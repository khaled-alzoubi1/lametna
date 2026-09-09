import os
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ==================== إعدادات الأمان وقاعدة البيانات ====================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'lametna-production-secure-key-2026-xyz')

database_url = os.environ.get('DATABASE_URL', 'sqlite:///lametna.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db = SQLAlchemy(app)

# ==================== نماذج قاعدة البيانات (Models) ====================

class SiteSetting(db.Model):
    __tablename__ = 'site_settings'
    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(150), default='فريق لمتنا بصمة | المنصة التطوعية الرسمية')
    brand_title_main = db.Column(db.String(50), default='فريق لمتنا')
    brand_title_sub = db.Column(db.String(50), default='بصمة')
    logo_url = db.Column(db.String(500), nullable=True)
    hero_title = db.Column(db.String(250), default='الشباب والمجتمع،<br><span>أثرٌ يتصل.</span>')
    hero_desc = db.Column(db.Text, default='مبادرة شبابية أردنية تأسست لنثبت أن التغيير الحقيقي يبدأ بجمع طاقتنا معاً. نؤمن أن العمل التطوعي ليس مجرد ساعات نقدّمها، بل أثر ملموس ومستدام نتركه في حياة الناس والمجتمع.')
    vision_text = db.Column(db.Text, default='الوصول إلى مجتمع شبابي ريادي يقود المبادرات المجتمعية بأعلى معايير التنظيم، وتوسيع مظلة الأثر التطوعي لتغطي كافة محافظات ومناطق المملكة الأردنية الهاشمية.')
    mission_text = db.Column(db.Text, default='تمكين الطاقات الشبابية وتوجيه شغفها لخدمة الفئات المستحقة، وترسيخ ثقافة التعاون الميداني من خلال بيئة تطوعية محفزة، منظمة، وآمنة تضمن استدامة البصمة الإيجابية.')
    contact_email = db.Column(db.String(120), default='info@lametnahbasmeh.org')
    
    # روابط المنصات الرسمية الحية
    whatsapp_url = db.Column(db.String(500), default='https://chat.whatsapp.com/DtNFEE9hSaDHQNIIPjHZJ8')
    instagram_url = db.Column(db.String(500), default='https://www.instagram.com/lametna_basmeh?stkn=ZGd5NHZiNmVteDFw')
    nahno_url = db.Column(db.String(500), default='https://www.nahno.org/ngo/%D9%81%D8%B1%D9%8A%D9%82-%D9%84%D9%85%D8%AA%D9%86%D8%A7-%D8%A8%D8%B5%D9%85%D8%A9-81843')
    
    # صور بطاقات خدمات المتطوعين الخمس
    card_img_duties = db.Column(db.String(500), default='https://images.unsplash.com/photo-1434030216411-0b793f4b4173?auto=format&fit=crop&w=600&q=80')
    card_img_hours = db.Column(db.String(500), default='https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=600&q=80')
    card_img_events = db.Column(db.String(500), default='https://images.unsplash.com/photo-1511632765486-a01980e01a18?auto=format&fit=crop&w=600&q=80')
    card_img_excuse = db.Column(db.String(500), default='https://images.unsplash.com/photo-1450133064473-71024230f91b?auto=format&fit=crop&w=600&q=80')
    card_img_transport = db.Column(db.String(500), default='https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=600&q=80')

    # أسماء وعناوين بطاقات الخدمات الخمس
    card_title_duties = db.Column(db.String(100), default='المهام والتكليفات')
    card_title_hours = db.Column(db.String(100), default='سجل الساعات والتقييم')
    card_title_events = db.Column(db.String(100), default='الفعاليات الميدانية')
    card_title_excuse = db.Column(db.String(100), default='تقديم اعتذار عن فعالية')
    card_title_transport = db.Column(db.String(100), default='نقاط التجمع والمواصلات')

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Volunteer(db.Model):
    __tablename__ = 'volunteers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(50), default='عمان')
    age = db.Column(db.Integer, nullable=True)
    team = db.Column(db.String(50), default='عمان')
    bio = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    is_leader = db.Column(db.Boolean, default=False)
    position = db.Column(db.String(100), nullable=True)
    volunteer_hours = db.Column(db.Integer, default=0)
    attended_events_count = db.Column(db.Integer, default=0)
    photo_url = db.Column(db.String(500), nullable=True)
    leader_notes = db.Column(db.Text, nullable=True)
    badges = db.Column(db.Text, default='')  # تخزين الأوسمة مفصولة بفواصل
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات التابعة
    duties = db.relationship('Duty', backref='volunteer', lazy=True, cascade="all, delete-orphan")
    excuses = db.relationship('Excuse', backref='volunteer', lazy=True, cascade="all, delete-orphan")
    registrations = db.relationship('EventRegistration', backref='volunteer', lazy=True, cascade="all, delete-orphan")

    @property
    def badges_list(self):
        if not self.badges:
            return []
        return [b.strip() for b in self.badges.split(',') if b.strip()]

    @property
    def wa_link(self):
        raw_phone = re.sub(r'\D', '', self.phone or '')
        if raw_phone.startswith('0'):
            return f"https://wa.me/962{raw_phone[1:]}"
        elif raw_phone.startswith('962'):
            return f"https://wa.me/{raw_phone}"
        return f"https://wa.me/{raw_phone}"

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    capacity = db.Column(db.Integer, default=10)  # المقاعد المطلوبة للميدان
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    registrations = db.relationship('EventRegistration', backref='event', lazy=True, cascade="all, delete-orphan")

    @property
    def registered_count(self):
        return len(self.registrations)

    @property
    def remaining_seats(self):
        rem = self.capacity - self.registered_count
        return rem if rem > 0 else 0

    @property
    def is_full(self):
        return self.registered_count >= self.capacity

class EventRegistration(db.Model):
    __tablename__ = 'event_registrations'
    id = db.Column(db.Integer, primary_key=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    attended = db.Column(db.Boolean, default=False)  # حالة التحضير الميداني
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Duty(db.Model):
    __tablename__ = 'duties'
    id = db.Column(db.Integer, primary_key=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Excuse(db.Model):
    __tablename__ = 'excuses'
    id = db.Column(db.Integer, primary_key=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id'), nullable=False)
    event_id = db.Column(db.Integer, nullable=True)
    reason = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GalleryItem(db.Model):
    __tablename__ = 'gallery'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # photo أو video
    media_url = db.Column(db.String(500), nullable=False)
    thumbnail_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== دوال المساعدة ====================

def get_settings():
    try:
        setting = SiteSetting.query.first()
        if not setting:
            setting = SiteSetting()
            db.session.add(setting)
            db.session.commit()
        return setting
    except Exception:
        db.session.rollback()
        return SiteSetting()

# ==================== المسارات العامة ====================

@app.route('/')
def index():
    settings = get_settings()
    leaders = Volunteer.query.filter_by(is_leader=True).all()
    events = Event.query.order_by(Event.id.desc()).limit(4).all()
    gallery_items = GalleryItem.query.order_by(GalleryItem.id.desc()).all()
    
    top_volunteers = Volunteer.query.filter_by(status='approved')\
                                    .order_by(Volunteer.volunteer_hours.desc(), Volunteer.attended_events_count.desc())\
                                    .limit(5).all()

    volunteers_count = Volunteer.query.filter_by(status='approved').count()
    hours_count = db.session.query(db.func.sum(Volunteer.volunteer_hours)).scalar() or 0
    events_count = Event.query.count()

    stats = {
        'volunteers_count': volunteers_count,
        'hours_count': hours_count,
        'events_count': events_count
    }
    
    user_registered_event_ids = []
    if 'user_id' in session:
        user_registered_event_ids = [r.event_id for r in EventRegistration.query.filter_by(volunteer_id=session['user_id']).all()]

    return render_template(
        'index.html',
        settings=settings,
        leaders=leaders,
        events=events,
        gallery_items=gallery_items,
        top_volunteers=top_volunteers,
        stats=stats,
        user_registered_event_ids=user_registered_event_ids
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if Volunteer.query.filter_by(email=email).first():
            flash('البريد الإلكتروني مسجل مسبقاً في المنصة.', 'danger')
            return redirect(url_for('index'))

        new_volunteer = Volunteer(
            name=request.form.get('name', '').strip(),
            email=email,
            phone=request.form.get('phone', '').strip(),
            password_hash=generate_password_hash(request.form.get('password', '').strip()),
            city=request.form.get('city', 'عمان'),
            team=request.form.get('team', 'عمان'),
            age=int(request.form.get('age')) if request.form.get('age') else None,
            status='pending'
        )
        db.session.add(new_volunteer)
        db.session.commit()
        flash('تم استلام طلب انتسابك بنجاح! سيتم تدقيقه من قبل الهيئة الإدارية.', 'success')
        return redirect(url_for('index'))

    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        admin_credentials = {
            'khaledsalzoubi1352006@gmail.com': {
                'password': 'kh13s5alzoubi2006',
                'name': 'خالد سمير الزعبي',
                'position': 'نائب رئيس المبادرة'
            },
            'lanooshabdo7@gmail.com': {
                'password': 'lanooshabdo7',
                'name': 'لين عبده',
                'position': 'رئيسة المبادرة'
            }
        }

        if identifier in admin_credentials and admin_credentials[identifier]['password'] == password:
            admin_user = Volunteer.query.filter_by(email=identifier).first()
            if not admin_user:
                admin_user = Volunteer(
                    name=admin_credentials[identifier]['name'],
                    email=identifier,
                    phone='0793888086' if 'khaled' in identifier else '0796425003',
                    password_hash=generate_password_hash(password),
                    city='عمان',
                    team='عمان',
                    status='approved',
                    is_leader=True,
                    position=admin_credentials[identifier]['position']
                )
                db.session.add(admin_user)
                db.session.commit()

            session.clear()
            session['admin_logged_in'] = True
            session['admin_email'] = identifier
            session['user_id'] = admin_user.id
            flash(f'أهلاً بكِ يا {admin_user.name} في لوحة التحكم الإدارية.' if 'lanoosh' in identifier else f'أهلاً بك يا {admin_user.name} في لوحة التحكم الإدارية.', 'success')
            return redirect(url_for('admin_dashboard'))

        volunteer = Volunteer.query.filter_by(email=identifier).first()
        if volunteer and check_password_hash(volunteer.password_hash, password):
            session.clear()
            session['user_id'] = volunteer.id
            flash(f'أهلاً بك مجدداً يا {volunteer.name}', 'success')
            return redirect(url_for('profile'))

        flash('بيانات الدخول غير صحيحة، يرجى التحقق من البريد وكلمة المرور.', 'danger')
        return redirect(url_for('index'))

    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج بنجاح.', 'info')
    return redirect(url_for('index'))

@app.route('/contact', methods=['POST'])
def contact_submit():
    flash('شكراً لتواصلك معنا، تم استلام استفسارك وسنقوم بالرد عليك في أقرب وقت.', 'success')
    return redirect(url_for('index'))

# ==================== بوابة التحقق الميداني من الباجة عبر QR ====================

@app.route('/verify/<int:volunteer_id>')
def verify_badge(volunteer_id):
    volunteer = Volunteer.query.get_or_404(volunteer_id)
    settings = get_settings()
    return render_template('verify_badge.html', volunteer=volunteer, settings=settings)

# ==================== بوابة المتطوع والتسجيل وتعديل كلمة المرور ====================

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('يرجى تسجيل الدخول أولاً.', 'danger')
        return redirect(url_for('index'))

    settings = get_settings()
    user = Volunteer.query.get_or_404(session['user_id'])
    user_events = Event.query.order_by(Event.id.desc()).all()
    duties = Duty.query.filter_by(volunteer_id=user.id).order_by(Duty.due_date.asc()).all()
    user_registrations = EventRegistration.query.filter_by(volunteer_id=user.id).all()
    registered_event_ids = [r.event_id for r in user_registrations]
    
    return render_template(
        'profile.html',
        user=user,
        user_events=user_events,
        duties=duties,
        settings=settings,
        registered_event_ids=registered_event_ids
    )

@app.route('/profile/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user = Volunteer.query.get_or_404(session['user_id'])
    user.age = request.form.get('age', type=int)
    user.city = request.form.get('city')
    user.team = request.form.get('team', user.team)
    user.phone = request.form.get('phone')
    user.bio = request.form.get('bio')
    photo_url = request.form.get('photo_url')
    if photo_url:
        user.photo_url = photo_url
    
    new_password = request.form.get('new_password', '').strip()
    if new_password:
        user.password_hash = generate_password_hash(new_password)
    
    db.session.commit()
    flash('تم تحديث ملفك الشخصي بنجاح.', 'success')
    return redirect(url_for('profile'))

@app.route('/events/rsvp/<int:event_id>', methods=['POST'])
def rsvp_event(event_id):
    if 'user_id' not in session:
        flash('يرجى تسجيل الدخول أولاً.', 'danger')
        return redirect(url_for('index'))

    user = Volunteer.query.get_or_404(session['user_id'])
    if user.status != 'approved':
        flash('يجب أن يكون حسابك معتمداً من الإدارة لتأكيد المشاركة.', 'danger')
        return redirect(request.referrer or url_for('profile'))

    ev = Event.query.get_or_404(event_id)
    existing_reg = EventRegistration.query.filter_by(volunteer_id=user.id, event_id=ev.id).first()
    if existing_reg:
        flash('أنت مسجل مسبقاً في هذا النشاط الميداني.', 'info')
        return redirect(request.referrer or url_for('profile'))

    if ev.is_full:
        flash('اكتمل العدد المطلوب للميدان في هذه الفعالية.', 'danger')
        return redirect(request.referrer or url_for('profile'))

    new_reg = EventRegistration(volunteer_id=user.id, event_id=ev.id)
    db.session.add(new_reg)
    db.session.commit()

    flash(f'تم حجز مقعدك بنجاح في: {ev.title}.', 'success')
    return redirect(request.referrer or url_for('profile'))

@app.route('/events/cancel_rsvp/<int:event_id>', methods=['POST'])
def cancel_rsvp(event_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))

    reg = EventRegistration.query.filter_by(volunteer_id=session['user_id'], event_id=event_id).first()
    if reg:
        db.session.delete(reg)
        db.session.commit()
        flash('تم إلغاء حجزك في الفعالية وفتح المقعد لمتطوع آخر.', 'info')
    return redirect(request.referrer or url_for('profile'))

@app.route('/profile/delete', methods=['POST'])
def delete_own_account():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user = Volunteer.query.get_or_404(session['user_id'])
    db.session.delete(user)
    db.session.commit()
    session.clear()
    flash('تم حذف حسابك نهائياً من المنصة.', 'info')
    return redirect(url_for('index'))

@app.route('/submit_excuse', methods=['POST'])
def submit_excuse():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    excuse = Excuse(
        volunteer_id=session['user_id'],
        event_id=request.form.get('event_id', type=int),
        reason=request.form.get('reason')
    )
    db.session.add(excuse)
    db.session.commit()
    flash('تم رفع عذر عدم الحضور للإدارة بنجاح.', 'success')
    return redirect(url_for('profile'))

# ==================== لوحة تحكم الإدارة (Admin Dashboard & CMS) ====================

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('غير مصرح لك بدخول لوحة التحكم.', 'danger')
        return redirect(url_for('index'))

    settings = get_settings()
    admin_email = session.get('admin_email')
    current_admin = Volunteer.query.filter_by(email=admin_email).first()
    
    volunteers = Volunteer.query.order_by(Volunteer.id.desc()).all()
    events = Event.query.order_by(Event.id.desc()).all()
    gallery_items = GalleryItem.query.order_by(GalleryItem.id.desc()).all()
    excuses = Excuse.query.order_by(Excuse.id.desc()).all()
    
    return render_template(
        'admin.html',
        settings=settings,
        current_admin=current_admin,
        volunteers=volunteers,
        events=events,
        gallery_items=gallery_items,
        excuses=excuses
    )

@app.route('/admin/profile/update', methods=['POST'])
def update_admin_profile():
    if not session.get('admin_logged_in'):
        return redirect(url_for('index'))

    admin_email = session.get('admin_email')
    admin_user = Volunteer.query.filter_by(email=admin_email).first()
    if admin_user:
        admin_user.name = request.form.get('name', admin_user.name)
        admin_user.phone = request.form.get('phone', admin_user.phone)
        admin_user.team = request.form.get('team', admin_user.team)
        admin_user.bio = request.form.get('bio', admin_user.bio)
        photo_url = request.form.get('photo_url')
        if photo_url:
            admin_user.photo_url = photo_url
        db.session.commit()
        flash('تم حفظ ملفك الإداري وصورتك بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

# --- إدارة المتطوعين، القيادات، الأوسمة، والتحضير الميداني ---

@app.route('/admin/rsvp/checkin/<int:reg_id>', methods=['POST'])
def checkin_rsvp_volunteer(reg_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    reg = EventRegistration.query.get_or_404(reg_id)
    if not reg.attended:
        reg.attended = True
        hours_to_award = request.form.get('hours', type=int) or 3
        reg.volunteer.volunteer_hours += hours_to_award
        reg.volunteer.attended_events_count += 1
        db.session.commit()
        flash(f'تم تحضير المتطوع {reg.volunteer.name} ومنحه {hours_to_award} ساعات.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/rsvp/remove/<int:reg_id>', methods=['POST'])
def remove_rsvp_volunteer(reg_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    reg = EventRegistration.query.get_or_404(reg_id)
    v_name = reg.volunteer.name
    db.session.delete(reg)
    db.session.commit()
    flash(f'تم شطب المتطوع {v_name} من الفعالية وفتح المقعد تلقائياً.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve/<int:volunteer_id>', methods=['POST'])
def approve_volunteer(volunteer_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    v.status = 'approved'
    db.session.commit()
    flash(f'تم اعتماد المتطوع {v.name}.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject/<int:volunteer_id>', methods=['POST'])
def reject_volunteer(volunteer_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    v.status = 'rejected'
    db.session.commit()
    flash(f'تم رفض طلب {v.name}.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/assign_leader', methods=['POST'])
def assign_leader():
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    volunteer_id = request.form.get('volunteer_id', type=int)
    position = request.form.get('position')
    photo_url = request.form.get('photo_url')

    v = Volunteer.query.get_or_404(volunteer_id)
    v.is_leader = True
    v.position = position
    if photo_url:
        v.photo_url = photo_url
    db.session.commit()

    flash(f'تم تثبيت {v.name} في منصب: {position}.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/remove_leader/<int:volunteer_id>', methods=['POST'])
def remove_leader(volunteer_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    v.is_leader = False
    v.position = None
    db.session.commit()
    flash(f'تم إعفاء {v.name} من المنصب القيادي.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/badge/assign/<int:volunteer_id>', methods=['POST'])
def assign_badge(volunteer_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    badge_name = request.form.get('badge_name', '').strip()
    if badge_name:
        current_badges = v.badges_list
        if badge_name not in current_badges:
            current_badges.append(badge_name)
            v.badges = ','.join(current_badges)
            db.session.commit()
            flash(f'تم منح {v.name}: {badge_name}', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/badge/remove/<int:volunteer_id>', methods=['POST'])
def remove_badge(volunteer_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    badge_name = request.form.get('badge_name', '').strip()
    current_badges = v.badges_list
    if badge_name in current_badges:
        current_badges.remove(badge_name)
        v.badges = ','.join(current_badges)
        db.session.commit()
        flash(f'تم سحب وسام {badge_name} من المتطوع.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/adjust_events/<int:volunteer_id>/<action>', methods=['POST'])
def adjust_events(volunteer_id, action):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    if action == 'increment':
        v.attended_events_count += 1
    elif action == 'decrement' and v.attended_events_count > 0:
        v.attended_events_count -= 1
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/adjust_hours/<int:volunteer_id>/<action>', methods=['POST'])
def adjust_hours(volunteer_id, action):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    if action == 'increment':
        v.volunteer_hours += 1
    elif action == 'decrement' and v.volunteer_hours >= 1:
        v.volunteer_hours -= 1
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reset_password/<int:volunteer_id>', methods=['POST'])
def reset_volunteer_password(volunteer_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    v.password_hash = generate_password_hash('123456')
    db.session.commit()
    flash(f'تمت إعادة تعيين كلمة سر {v.name} إلى: 123456', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_volunteer/<int:volunteer_id>', methods=['POST'])
def delete_volunteer_admin(volunteer_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    db.session.delete(v)
    db.session.commit()
    flash('تم مسح حساب المتطوع وسجلاته نهائياً.', 'info')
    return redirect(url_for('admin_dashboard'))

# --- إدارة الفعاليات والمهام والمعرض ---

@app.route('/admin/event/add', methods=['POST'])
def add_event():
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    capacity = request.form.get('capacity', type=int) or 10
    new_event = Event(
        title=request.form.get('title'),
        description=request.form.get('description'),
        date=request.form.get('date'),
        time=request.form.get('time'),
        location=request.form.get('location'),
        capacity=capacity
    )
    db.session.add(new_event)
    db.session.commit()
    flash('تمت إضافة الفعالية الميدانية بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/event/delete/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    ev = Event.query.get_or_404(event_id)
    db.session.delete(ev)
    db.session.commit()
    flash('تم حذف الفعالية.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/duty/assign', methods=['POST'])
def assign_duty():
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    new_duty = Duty(
        volunteer_id=request.form.get('volunteer_id', type=int),
        title=request.form.get('title'),
        description=request.form.get('description'),
        due_date=request.form.get('due_date')
    )
    db.session.add(new_duty)
    db.session.commit()
    flash('تم إسناد التكليف الميداني بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/gallery/add', methods=['POST'])
def add_gallery_item():
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    new_item = GalleryItem(
        title=request.form.get('title'),
        type=request.form.get('type'),
        media_url=request.form.get('media_url'),
        thumbnail_url=request.form.get('thumbnail_url')
    )
    db.session.add(new_item)
    db.session.commit()
    flash('تمت إضافة المادة للمعرض بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/gallery/delete/<int:item_id>', methods=['POST'])
def delete_gallery_item(item_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    item = GalleryItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('تم حذف العنصر من المعرض.', 'info')
    return redirect(url_for('admin_dashboard'))

# --- إدارة محتوى ومظهر الموقع (CMS) ---

@app.route('/admin/settings/update', methods=['POST'])
def update_settings():
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    setting = get_settings()

    setting.site_name = request.form.get('site_name')
    setting.brand_title_main = request.form.get('brand_title_main')
    setting.brand_title_sub = request.form.get('brand_title_sub')
    setting.logo_url = request.form.get('logo_url')
    setting.hero_title = request.form.get('hero_title')
    setting.hero_desc = request.form.get('hero_desc')
    setting.vision_text = request.form.get('vision_text')
    setting.mission_text = request.form.get('mission_text')
    setting.contact_email = request.form.get('contact_email')
    
    setting.whatsapp_url = request.form.get('whatsapp_url')
    setting.instagram_url = request.form.get('instagram_url')
    setting.nahno_url = request.form.get('nahno_url')

    # صور بطاقات خدمات المتطوعين الخمس
    setting.card_img_duties = request.form.get('card_img_duties')
    setting.card_img_hours = request.form.get('card_img_hours')
    setting.card_img_events = request.form.get('card_img_events')
    setting.card_img_excuse = request.form.get('card_img_excuse')
    setting.card_img_transport = request.form.get('card_img_transport')

    # أسماء وعناوين بطاقات الخدمات الخمس
    setting.card_title_duties = request.form.get('card_title_duties', setting.card_title_duties)
    setting.card_title_hours = request.form.get('card_title_hours', setting.card_title_hours)
    setting.card_title_events = request.form.get('card_title_events', setting.card_title_events)
    setting.card_title_excuse = request.form.get('card_title_excuse', setting.card_title_excuse)
    setting.card_title_transport = request.form.get('card_title_transport', setting.card_title_transport)

    db.session.commit()
    flash('تم حفظ الإعدادات وعناوين وصور البطاقات بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

# ==================== التهيئة والترحيل التلقائي لقاعدة البيانات ====================

with app.app_context():
    db.create_all()
    
    migrations = [
        ("site_settings", "whatsapp_url", "VARCHAR(500)"),
        ("site_settings", "instagram_url", "VARCHAR(500)"),
        ("site_settings", "nahno_url", "VARCHAR(500)"),
        ("site_settings", "card_img_duties", "VARCHAR(500)"),
        ("site_settings", "card_img_hours", "VARCHAR(500)"),
        ("site_settings", "card_img_events", "VARCHAR(500)"),
        ("site_settings", "card_img_excuse", "VARCHAR(500)"),
        ("site_settings", "card_img_transport", "VARCHAR(500)"),
        ("site_settings", "card_title_duties", "VARCHAR(100) DEFAULT 'المهام والتكليفات'"),
        ("site_settings", "card_title_hours", "VARCHAR(100) DEFAULT 'سجل الساعات والتقييم'"),
        ("site_settings", "card_title_events", "VARCHAR(100) DEFAULT 'الفعاليات الميدانية'"),
        ("site_settings", "card_title_excuse", "VARCHAR(100) DEFAULT 'تقديم اعتذار عن فعالية'"),
        ("site_settings", "card_title_transport", "VARCHAR(100) DEFAULT 'نقاط التجمع والمواصلات'"),
        ("volunteers", "badges", "TEXT DEFAULT ''"),
        ("events", "capacity", "INTEGER DEFAULT 10"),
        ("event_registrations", "attended", "BOOLEAN DEFAULT FALSE")
    ]
    for tbl, col, col_type in migrations:
        try:
            db.session.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {col} {col_type};"))
            db.session.commit()
        except Exception:
            db.session.rollback()

    try:
        if not SiteSetting.query.first():
            db.session.add(SiteSetting())
            db.session.commit()
    except Exception:
        db.session.rollback()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)