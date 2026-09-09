import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
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
    team = db.Column(db.String(50), default='الميداني')
    bio = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    is_leader = db.Column(db.Boolean, default=False)
    position = db.Column(db.String(100), nullable=True)
    volunteer_hours = db.Column(db.Integer, default=0)
    attended_events_count = db.Column(db.Integer, default=0)
    photo_url = db.Column(db.String(500), nullable=True)
    leader_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات المرتبطة
    duties = db.relationship('Duty', backref='volunteer', lazy=True, cascade="all, delete-orphan")
    excuses = db.relationship('Excuse', backref='volunteer', lazy=True, cascade="all, delete-orphan")

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(150), nullable=False)
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
    type = db.Column(db.String(20), nullable=False)  # 'photo' أو 'video'
    media_url = db.Column(db.String(500), nullable=False)
    thumbnail_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== دالة مساعدة لجلب الإعدادات ====================

def get_settings():
    setting = SiteSetting.query.first()
    if not setting:
        setting = SiteSetting()
        db.session.add(setting)
        db.session.commit()
    return setting

# ==================== المسارات العامة ====================

@app.route('/')
def index():
    settings = get_settings()
    leaders = Volunteer.query.filter_by(is_leader=True).all()
    events = Event.query.order_by(Event.id.desc()).limit(4).all()
    gallery_items = GalleryItem.query.order_by(GalleryItem.id.desc()).all()
    
    volunteers_count = Volunteer.query.filter_by(status='approved').count()
    hours_count = db.session.query(db.func.sum(Volunteer.volunteer_hours)).scalar() or 0
    events_count = Event.query.count()

    stats = {
        'volunteers_count': volunteers_count,
        'hours_count': hours_count,
        'events_count': events_count
    }
    
    return render_template(
        'index.html',
        settings=settings,
        leaders=leaders,
        events=events,
        gallery_items=gallery_items,
        stats=stats
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        if Volunteer.query.filter_by(email=email).first():
            flash('البريد الإلكتروني مسجل مسبقاً في المنصة.', 'danger')
            return redirect(url_for('index'))

        new_volunteer = Volunteer(
            name=request.form.get('name'),
            email=email,
            phone=request.form.get('phone'),
            password_hash=generate_password_hash(request.form.get('password')),
            city=request.form.get('city', 'عمان'),
            team=request.form.get('team', 'الميداني'),
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
        identifier = request.form.get('email')
        password = request.form.get('password')

        # التحقق من دخول مدير النظام (Admin)
        if identifier == 'admin' and password == 'lametna2026':
            session.clear()
            session['admin_logged_in'] = True
            flash('تم تسجيل الدخول بنجاح كمسؤول للنظام.', 'success')
            return redirect(url_for('admin_dashboard'))

        # التحقق من دخول المتطوع
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
    flash('شكراً لتواصلك معنا، تم استلام استفسارك بنجاح وسنقوم بالرد قريباً.', 'success')
    return redirect(url_for('index'))

# ==================== بوابة المتطوع ====================

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('يرجى تسجيل الدخول أولاً.', 'danger')
        return redirect(url_for('index'))

    user = Volunteer.query.get_or_404(session['user_id'])
    user_events = Event.query.order_by(Event.id.desc()).all()
    duties = Duty.query.filter_by(volunteer_id=user.id).order_by(Duty.due_date.asc()).all()
    
    return render_template('profile.html', user=user, user_events=user_events, duties=duties)

@app.route('/profile/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user = Volunteer.query.get_or_404(session['user_id'])
    user.age = request.form.get('age', type=int)
    user.city = request.form.get('city')
    user.phone = request.form.get('phone')
    user.bio = request.form.get('bio')
    
    db.session.commit()
    flash('تم تحديث ملفك الشخصي بنجاح.', 'success')
    return redirect(url_for('profile'))

@app.route('/profile/delete', methods=['POST'])
def delete_own_account():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user = Volunteer.query.get_or_404(session['user_id'])
    db.session.delete(user)
    db.session.commit()
    session.clear()
    flash('تم حذف حسابك وكافة سجلاتك نهائياً من المنصة.', 'info')
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
    volunteers = Volunteer.query.order_by(Volunteer.id.desc()).all()
    events = Event.query.order_by(Event.id.desc()).all()
    gallery_items = GalleryItem.query.order_by(GalleryItem.id.desc()).all()
    excuses = Excuse.query.order_by(Excuse.id.desc()).all()
    
    return render_template(
        'admin.html',
        settings=settings,
        volunteers=volunteers,
        events=events,
        gallery_items=gallery_items,
        excuses=excuses
    )

# --- إدارة المتطوعين والقيادات ---

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
        v.volunteer_hours += 2
    elif action == 'decrement' and v.volunteer_hours >= 2:
        v.volunteer_hours -= 2
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
    new_event = Event(
        title=request.form.get('title'),
        description=request.form.get('description'),
        date=request.form.get('date'),
        time=request.form.get('time'),
        location=request.form.get('location')
    )
    db.session.add(new_event)
    db.session.commit()
    flash('تمت إضافة الفعالية بنجاح.', 'success')
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

# --- إدارة محتوى ومظهر الموقع (Full CMS Update) ---

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

    db.session.commit()
    flash('تم حفظ وتحديث إعدادات ومحتوى الموقع بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

# ==================== التهيئة الأولية للجداول ====================

with app.app_context():
    db.create_all()
    # التأكد من وجود سطر الإعدادات
    if not SiteSetting.query.first():
        db.session.add(SiteSetting())
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)