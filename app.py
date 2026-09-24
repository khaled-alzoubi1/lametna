import os
import re
import random
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from io import BytesIO
from openpyxl import Workbook

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
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max upload

db = SQLAlchemy(app)

# ==================== نماذج قاعدة البيانات (Models) ====================


class SystemSettings(db.Model):
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    banner_text = db.Column(db.String(500), default='أهلاً بكم في المنصة الرسمية لفريق لمتنا بصمة')
    is_banner_active = db.Column(db.Boolean, default=False)

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
    gender = db.Column(db.String(10), nullable=True)
    skills = db.Column(db.String(200), nullable=True)
    experience = db.Column(db.Text, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    is_leader = db.Column(db.Boolean, default=False)
    position = db.Column(db.String(100), nullable=True)
    volunteer_hours = db.Column(db.Integer, default=0)
    attended_events_count = db.Column(db.Integer, default=0)
    photo_url = db.Column(db.String(500), nullable=True)
    leader_notes = db.Column(db.Text, nullable=True)
    badges = db.Column(db.Text, default='')  # تخزين الأوسمة مفصولة بفواصل
    badge_number = db.Column(db.String(50), unique=True, nullable=True)
    
    # Phase 3 Columns
    emergency_contact_name = db.Column(db.String(100), nullable=True)
    emergency_contact_phone = db.Column(db.String(20), nullable=True)
    is_suspended = db.Column(db.Boolean, default=False)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    admin_evaluation = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات التابعة
    duties = db.relationship('Duty', backref='volunteer', lazy=True, cascade="all, delete-orphan")
    excuses = db.relationship('Excuse', backref='volunteer', lazy=True, cascade="all, delete-orphan")
    registrations = db.relationship('EventRegistration', backref='volunteer', lazy=True, cascade="all, delete-orphan")

    @db.orm.reconstructor
    def enforce_admin_titles(self):
        if self.email:
            em = self.email.lower()
            if em == 'lanooshabdo7@gmail.com':
                self.position = 'رئيس الفريق'
                self.is_leader = True
            elif em == 'khaledsalzoubi1352006@gmail.com':
                self.position = 'نائب رئيس الفريق'
                self.is_leader = True

    @property
    def badges_list(self):
        if not self.badges:
            return []
        return [b.strip() for b in self.badges.split(',') if b.strip()]

    def auto_assign_badges(self):
        badges = self.badges_list
        changed = False

        # وسام النشاط الأول
        if (self.attended_events_count or 0) >= 1 and 'وسام أول بصمة' not in badges:
            badges.append('وسام أول بصمة')
            changed = True

        # عتبة 10 ساعات
        if (self.volunteer_hours or 0) >= 10 and 'وسام الالتزام الميداني' not in badges:
            badges.append('وسام الالتزام الميداني')
            changed = True

        # عتبة 25 ساعة
        if (self.volunteer_hours or 0) >= 25 and 'وسام بطل الميدان' not in badges:
            badges.append('وسام بطل الميدان')
            changed = True

        # عتبة 50 ساعة
        if (self.volunteer_hours or 0) >= 50 and 'وسام الانضباط الذهبي' not in badges:
            badges.append('وسام الانضباط الذهبي')
            changed = True

        if changed:
            self.badges = ','.join(badges)

    @property
    def wa_link(self):
        if not self.phone:
            return "#"
        raw_phone = re.sub(r'\D', '', self.phone)
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
    secret_code = db.Column(db.String(10), nullable=True)
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

    @property
    def is_completed(self):
        if not self.date:
            return False
        raw_date = str(self.date).strip()
        today = datetime.now().date()
        
        # فحص كافة صيغ التاريخ المحتملة
        event_date = None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y'):
            try:
                event_date = datetime.strptime(raw_date, fmt).date()
                break
            except (ValueError, TypeError):
                pass
        
        # دعم الإدخال المختصر مثل 11/9 أو 11-9
        if not event_date:
            try:
                parts = re.split(r'[/.-]', raw_date)
                if len(parts) >= 2:
                    d, m = int(parts[0]), int(parts[1])
                    y = int(parts[2]) if len(parts) > 2 else today.year
                    event_date = datetime(y, m, d).date()
            except Exception:
                return False

        if not event_date:
            return False

        # ينتهي التسجيل وتعتبر منجزة فقط بعد انتهاء يوم الفعالية بالكامل
        return event_date < today

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

class Album(db.Model):
    __tablename__ = 'albums'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='عام')
    cover_image_url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    media = db.relationship('AlbumMedia', backref='album', lazy=True, cascade="all, delete-orphan")

class AlbumMedia(db.Model):
    __tablename__ = 'album_media'
    id = db.Column(db.Integer, primary_key=True)
    album_id = db.Column(db.Integer, db.ForeignKey('albums.id'), nullable=False)
    media_url = db.Column(db.String(500), nullable=False)
    media_type = db.Column(db.String(20), nullable=False) # 'image' or 'video'

class Inquiry(db.Model):
    __tablename__ = 'inquiries'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== دوال المساعدة ====================


@app.context_processor
def inject_sys_settings():
    try:
        sys_settings = SystemSettings.query.first()
        if not sys_settings:
            sys_settings = SystemSettings()
            db.session.add(sys_settings)
            db.session.commit()
    except Exception:
        db.session.rollback()
        sys_settings = None
    return dict(sys_settings=sys_settings)

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

@app.route('/robots.txt')
def robots_txt():
    return "User-agent: *\nAllow: /", 200, {'Content-Type': 'text/plain'}
@app.route('/')
def index():
    settings = get_settings()
    valid_positions = ['ليدر', 'رئيس لجان', 'هيئة إدارية', 'رئيس الفريق', 'نائب رئيس الفريق']
    admin_emails = ['lanooshabdo7@gmail.com', 'khaledsalzoubi1352006@gmail.com']

    leaders = Volunteer.query.filter(
        db.or_(
            db.and_(
                Volunteer.is_leader == True,
                Volunteer.position.in_(valid_positions)
            ),
            db.func.lower(Volunteer.email).in_(admin_emails)
        )
    ).all()
    events = Event.query.order_by(Event.id.desc()).limit(4).all()
    albums = Album.query.order_by(Album.id.desc()).all()
    
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
        albums=albums,
        top_volunteers=top_volunteers,
        stats=stats,
        user_registered_event_ids=user_registered_event_ids
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        if Volunteer.query.filter_by(email=email).first():
            flash('البريد الإلكتروني مسجل مسبقاً في المنصة.', 'danger')
            return redirect(url_for('index'))
        if phone and Volunteer.query.filter_by(phone=phone).first():
            flash('رقم الهاتف مسجل مسبقاً في المنصة.', 'danger')
            return redirect(url_for('index'))


        new_volunteer = Volunteer(
            name=request.form.get('name', '').strip(),
            email=email,
            phone=phone,
            password_hash=generate_password_hash(request.form.get('password', '').strip()),
            city=request.form.get('city', 'عمان'),
            team=request.form.get('team', 'عمان'),
            age=int(request.form.get('age')) if request.form.get('age') else None,
            gender=request.form.get('gender'),
            skills = ', '.join(request.form.getlist('skills')),
            experience=request.form.get('experience', '').strip(),
            emergency_contact_name=request.form.get('emergency_contact_name', '').strip(),
            emergency_contact_phone=request.form.get('emergency_contact_phone', '').strip(),
            status='pending'
        )
        
        db.session.add(new_volunteer)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
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
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')

            admin_user.last_active = datetime.utcnow()
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
            
            session.clear()
            session['admin_logged_in'] = True
            session['admin_email'] = identifier
            session['user_id'] = admin_user.id
            flash(f'أهلاً بكِ يا {admin_user.name} في لوحة التحكم الإدارية.' if 'lanoosh' in identifier else f'أهلاً بك يا {admin_user.name} في لوحة التحكم الإدارية.', 'success')
            return redirect(url_for('admin_dashboard'))

        volunteer = Volunteer.query.filter_by(email=identifier).first()
        if volunteer and check_password_hash(volunteer.password_hash, password):
            volunteer.last_active = datetime.utcnow()
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
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
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    message = request.form.get('message', '').strip()
    if first_name or last_name or message:
        inquiry = Inquiry(
            first_name=first_name or 'غير محدد',
            last_name=last_name or '',
            phone=phone,
            email=email,
            message=message or 'لا يوجد نص'
        )
        db.session.add(inquiry)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    flash('شكراً لتواصلك معنا، تم استلام استفسارك وسنقوم بالرد عليك في أقرب وقت.', 'success')
    return redirect(url_for('index'))

@app.route('/org_chart')
def org_chart():
    settings = get_settings()
    return render_template('org_chart.html', settings=settings)

@app.route('/resources')
def resources():
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول أولاً للوصول لمركز الوثائق.', 'danger')
        return redirect(url_for('login'))
    user = Volunteer.query.get_or_404(session['user_id'])
    if user.status != 'approved':
        flash('مركز الوثائق متاح فقط للمتطوعين المعتمدين.', 'danger')
        return redirect(url_for('profile'))
    settings = get_settings()
    return render_template('resources.html', settings=settings, user=user)

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
    user.skills = request.form.get('skills', user.skills)
    user.experience = request.form.get('experience', user.experience)
    if 'emergency_contact_name' in request.form:
        user.emergency_contact_name = request.form.get('emergency_contact_name', '').strip()
    if 'emergency_contact_phone' in request.form:
        user.emergency_contact_phone = request.form.get('emergency_contact_phone', '').strip()

    # Handle physical file upload
    uploaded_file = request.files.get('profile_image')
    if uploaded_file and uploaded_file.filename:
        allowed_ext = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        ext = uploaded_file.filename.rsplit('.', 1)[-1].lower() if '.' in uploaded_file.filename else ''
        if ext in allowed_ext:
            safe_name = secure_filename(f"vol_{user.id}_{uploaded_file.filename}")
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
            uploaded_file.save(save_path)
            user.photo_url = url_for('static', filename=f'uploads/{safe_name}')
        else:
            flash('صيغة الصورة غير مدعومة. استخدم PNG, JPG, GIF, أو WEBP.', 'danger')
    else:
        # Fallback to URL if no file uploaded
        photo_url = request.form.get('photo_url')
        if photo_url:
            user.photo_url = photo_url
    
    new_password = request.form.get('new_password', '').strip()
    if new_password:
        user.password_hash = generate_password_hash(new_password)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
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
    if ev.is_completed:
        flash('عذراً، هذه الفعالية انتهت ومغلقة أمام التسجيل الميداني.', 'danger')
        return redirect(request.referrer or url_for('profile'))
    existing_reg = EventRegistration.query.filter_by(volunteer_id=user.id, event_id=ev.id).first()
    if existing_reg:
        flash('أنت مسجل مسبقاً في هذا النشاط الميداني.', 'info')
        return redirect(request.referrer or url_for('profile'))

    if ev.is_full:
        flash('اكتمل العدد المطلوب للميدان في هذه الفعالية.', 'danger')
        return redirect(request.referrer or url_for('profile'))

    new_reg = EventRegistration(volunteer_id=user.id, event_id=ev.id)
    db.session.add(new_reg)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')

    flash(f'تم حجز مقعدك بنجاح في: {ev.title}.', 'success')
    return redirect(request.referrer or url_for('profile'))

@app.route('/events/cancel_rsvp/<int:event_id>', methods=['POST'])
def cancel_rsvp(event_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))

    reg = EventRegistration.query.filter_by(volunteer_id=session['user_id'], event_id=event_id).first()
    if reg:
        db.session.delete(reg)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
        flash('تم إلغاء حجزك في الفعالية وفتح المقعد لمتطوع آخر.', 'info')
    return redirect(request.referrer or url_for('profile'))

@app.route('/events/self_checkin', methods=['POST'])
def self_checkin():
    if 'user_id' not in session:
        flash('يرجى تسجيل الدخول أولاً.', 'danger')
        return redirect(url_for('index'))

    event_id = request.form.get('event_id', type=int)
    entered_code = request.form.get('secret_code', '').strip()

    ev = Event.query.get_or_404(event_id)
    user = Volunteer.query.get_or_404(session['user_id'])

    reg = EventRegistration.query.filter_by(volunteer_id=user.id, event_id=ev.id).first()
    if not reg:
        flash('يجب أن تكون مسجلاً بالفعالية لتأكيد حضورك.', 'danger')
        return redirect(request.referrer or url_for('profile'))

    if reg.attended:
        flash('تم تسجيل حضورك مسبقاً في هذه الفعالية.', 'info')
        return redirect(request.referrer or url_for('profile'))

    # مطابقة الكود السري
    if ev.secret_code and entered_code == str(ev.secret_code).strip():
        reg.attended = True
        hours_to_award = 3  # الساعات الافتراضية للنشاط
        user.volunteer_hours = (user.volunteer_hours or 0) + hours_to_award
        user.attended_events_count = (user.attended_events_count or 0) + 1
        user.auto_assign_badges()
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
        flash(f'أحسنت! تم تأكيد حضورك بنجاح في "{ev.title}" وإضافة {hours_to_award} ساعات لرصيدك.', 'success')
    else:
        flash('كود التحضير غير صحيح! يرجى مراجعة مسؤول الميدان.', 'danger')

    return redirect(request.referrer or url_for('profile'))

@app.route('/profile/delete', methods=['POST'])
def delete_own_account():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user = Volunteer.query.get_or_404(session['user_id'])
    db.session.delete(user)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    session.clear()
    flash('تم حذف حسابك نهائياً من المنصة.', 'info')
    return redirect(url_for('index'))

@app.route('/submit_excuse', methods=['POST'])
def submit_excuse():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    event_id = request.form.get('event_id', type=int)
    excuse = Excuse(
        volunteer_id=session['user_id'],
        event_id=event_id,
        reason=request.form.get('reason')
    )
    db.session.add(excuse)

    # تفريغ المقعد تلقائياً بإلغاء تسجيل المتطوع في الفعالية
    if event_id and event_id > 0:
        reg = EventRegistration.query.filter_by(volunteer_id=session['user_id'], event_id=event_id).first()
        if reg:
            db.session.delete(reg)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    flash('تم رفع عذر عدم الحضور للإدارة وإلغاء حجز المقعد بنجاح.', 'success')
    return redirect(url_for('profile'))
# ==================== لوحة تحكم الإدارة (Admin Dashboard & CMS) ====================

import json
from collections import Counter

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('غير مصرح لك بدخول لوحة التحكم.', 'danger')
        return redirect(url_for('index'))

    settings = get_settings()
    admin_email = session.get('admin_email')
    current_admin = Volunteer.query.filter_by(email=admin_email).first()
    
    # --- Task 6: Search & Filter ---
    search_name = request.args.get('search_name', '').strip()
    filter_city = request.args.get('filter_city', '').strip()
    filter_skill = request.args.get('filter_skill', '').strip()
    filter_gender = request.args.get('filter_gender', '').strip()

    vol_query = Volunteer.query
    if search_name:
        vol_query = vol_query.filter(
            db.or_(
                Volunteer.name.ilike(f'%{search_name}%'),
                Volunteer.phone.ilike(f'%{search_name}%')
            )
        )
    if filter_city:
        vol_query = vol_query.filter(Volunteer.city.ilike(f'%{filter_city}%'))
    if filter_skill:
        vol_query = vol_query.filter(Volunteer.skills.ilike(f'%{filter_skill}%'))
    if filter_gender:
        vol_query = vol_query.filter(Volunteer.gender == filter_gender)

    volunteers = vol_query.order_by(Volunteer.id.desc()).all()
    inquiries = Inquiry.query.order_by(Inquiry.id.desc()).all()

    events = Event.query.order_by(Event.id.desc()).all()
    albums = Album.query.order_by(Album.id.desc()).all()
    excuses = Excuse.query.order_by(Excuse.id.desc()).all()

    # --- PHASE 2: Data Aggregation for Chart.js Command Center ---
    all_volunteers = Volunteer.query.all()
    city_counts = dict(Counter(v.city for v in all_volunteers if v.city))
    if not city_counts:
        city_counts = {"عمان": 120, "الزرقاء": 85, "إربد": 60, "البلقاء": 40, "أخرى": 15}

    growth_labels = ['أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر']
    growth_data = [max(1, len(all_volunteers)*2), max(1, len(events)*3), max(1, len(albums)*2), max(1, len(excuses)), max(1, len(all_volunteers)*3), max(1, len(events)*4)]

    activity_labels = ['وقف ثريد', 'مسنين', 'بنك ملابس', 'أطفال', 'بيئي']
    activity_data = [
        EventRegistration.query.join(Event).filter(Event.title.ilike('%ثريد%')).count() or 0,
        EventRegistration.query.join(Event).filter(Event.title.ilike('%مسن%')).count() or 0,
        EventRegistration.query.join(Event).filter(Event.title.ilike('%ملابس%')).count() or 0,
        EventRegistration.query.join(Event).filter(Event.title.ilike('%أطفال%')).count() or 0,
        EventRegistration.query.join(Event).filter(Event.title.ilike('%بيئ%')).count() or 0,
    ]
    total_activities = len(events)

    chart_data = {
        'city_labels': list(city_counts.keys()),
        'city_data': list(city_counts.values()),
        'growth_labels': growth_labels,
        'growth_data': growth_data,
        'activity_labels': activity_labels,
        'activity_data': activity_data,
        'total_activities': total_activities
    }

    return render_template(
        'admin.html',
        settings=settings,
        current_admin=current_admin,
        volunteers=volunteers,
        events=events,
        albums=albums,
        excuses=excuses,
        inquiries=inquiries,
        chart_data=chart_data,
        search_name=search_name,
        filter_city=filter_city,
        filter_skill=filter_skill,
        filter_gender=filter_gender
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
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
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
        reg.volunteer.volunteer_hours = (reg.volunteer.volunteer_hours or 0) + hours_to_award
        reg.volunteer.attended_events_count = (reg.volunteer.attended_events_count or 0) + 1
        reg.volunteer.auto_assign_badges()
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
        flash(f'تم تحضير المتطوع {reg.volunteer.name} ومنحه {hours_to_award} ساعات.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/rsvp/remove/<int:reg_id>', methods=['POST'])
def remove_rsvp_volunteer(reg_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    reg = EventRegistration.query.get_or_404(reg_id)
    v_name = reg.volunteer.name
    db.session.delete(reg)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    flash(f'تم شطب المتطوع {v_name} من الفعالية وفتح المقعد تلقائياً.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve/<int:volunteer_id>', methods=['POST'])
def approve_volunteer(volunteer_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    
    # Intercept incoming badge_number
    submitted_number = request.form.get('badge_number')
    if submitted_number:
        submitted_number = submitted_number.strip()
        existing = Volunteer.query.filter_by(badge_number=submitted_number).first()
        if existing and existing.id != v.id:
            flash('الرقم الميداني مسجل مسبقاً لمتطوع آخر. يرجى اختيار رقم مختلف.', 'danger')
            return redirect(url_for('admin_dashboard'))
        v.badge_number = submitted_number

    v.status = 'approved'
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    flash(f'تم اعتماد المتطوع {v.name}.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject/<int:volunteer_id>', methods=['POST'])
def reject_volunteer(volunteer_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    v.status = 'rejected'
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    flash(f'تم رفض طلب {v.name}.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/assign_leader', methods=['POST'])
def assign_leader():
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    volunteer_id = request.form.get('volunteer_id', type=int)
    position = request.form.get('position')
    photo_url = request.form.get('photo_url')

    v = Volunteer.query.get_or_404(volunteer_id)
    
    # Intercept incoming badge_number
    submitted_number = request.form.get('badge_number')
    if submitted_number:
        submitted_number = submitted_number.strip()
        existing = Volunteer.query.filter_by(badge_number=submitted_number).first()
        if existing and existing.id != v.id:
            flash('الرقم الميداني مسجل مسبقاً لمتطوع آخر. يرجى اختيار رقم مختلف.', 'danger')
            return redirect(url_for('admin_dashboard'))
        v.badge_number = submitted_number

    v.is_leader = True
    v.position = position
    if photo_url:
        v.photo_url = photo_url
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')

    flash(f'تم تحديث بيانات {v.name} وتثبيته في المنصب.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_suspend/<int:vol_id>', methods=['POST'])
def toggle_suspend(vol_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(vol_id)
    v.is_suspended = not v.is_suspended
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    status_text = 'تجميد' if v.is_suspended else 'فك تجميد'
    flash(f'تم {status_text} حساب {v.name} بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_evaluation/<int:vol_id>', methods=['POST'])
def update_evaluation(vol_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(vol_id)
    v.admin_evaluation = request.form.get('admin_evaluation')
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    flash(f'تم تحديث التقييم الإداري للمتطوع {v.name}.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/remove_leader/<int:volunteer_id>', methods=['POST'])
def remove_leader(volunteer_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    v.is_leader = False
    v.position = None
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
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
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
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
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
        flash(f'تم سحب وسام {badge_name} من المتطوع.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/adjust_events/<int:volunteer_id>/<action>', methods=['POST'])
def adjust_events(volunteer_id, action):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    if action == 'increment':
        v.attended_events_count = (v.attended_events_count or 0) + 1
        v.auto_assign_badges()
    elif action == 'decrement' and (v.attended_events_count or 0) > 0:
        v.attended_events_count = (v.attended_events_count or 0) - 1
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/adjust_hours/<int:volunteer_id>/<action>', methods=['POST'])
def adjust_hours(volunteer_id, action):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    if action == 'increment':
        v.volunteer_hours = (v.volunteer_hours or 0) + 1
        v.auto_assign_badges()
    elif action == 'decrement' and (v.volunteer_hours or 0) >= 1:
        v.volunteer_hours = (v.volunteer_hours or 0) - 1
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reset_password/<int:volunteer_id>', methods=['POST'])
def reset_volunteer_password(volunteer_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    v.password_hash = generate_password_hash('123456')
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    flash(f'تمت إعادة تعيين كلمة سر {v.name} إلى: 123456', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_volunteer/<int:volunteer_id>', methods=['POST'])
def delete_volunteer_admin(volunteer_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    v = Volunteer.query.get_or_404(volunteer_id)
    EventRegistration.query.filter_by(volunteer_id=v.id).delete()
    db.session.delete(v)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    flash('تم حذف المتطوع وسجلاته بنجاح.', 'info')
    return redirect(url_for('admin_dashboard'))
# --- إدارة الفعاليات والمهام والمعرض ---

@app.route('/admin/event/add', methods=['POST'])
def add_event():
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    capacity = request.form.get('capacity', type=int) or 10
    code = str(random.randint(1000, 9999))
    new_event = Event(
        title=request.form.get('title'),
        description=request.form.get('description'),
        date=request.form.get('date'),
        time=request.form.get('time'),
        location=request.form.get('location'),
        capacity=capacity,
        secret_code=code
    )
    db.session.add(new_event)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    flash(f'تمت إضافة الفعالية بنجاح. كود التحضير السري هو: {code}', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/event/<int:event_id>/export')
def export_event_roster(event_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('index'))

    wb = Workbook()
    ws = wb.active
    ws.sheet_view.rightToLeft = True

    if event_id == 0:
        # Export all volunteers
        ws.title = 'كشف المتطوعين'
        ws.append(['#', 'الاسم', 'الجنس', 'العمر', 'المحافظة', 'الفريق', 'الهاتف', 'البريد الإلكتروني', 'المهارات', 'الخبرة', 'الحالة', 'الساعات', 'الفعاليات'])
        volunteers_all = Volunteer.query.order_by(Volunteer.id.asc()).all()
        for i, v in enumerate(volunteers_all, start=1):
            ws.append([
                i, v.name, v.gender or 'غير محدد', v.age or 'غير محدد',
                v.city, v.team, v.phone, v.email,
                v.skills or 'لا يوجد', v.experience or 'لا يوجد',
                v.status, v.volunteer_hours or 0, v.attended_events_count or 0
            ])
        filename = 'all_volunteers.xlsx'
    else:
        ev = Event.query.get_or_404(event_id)
        regs = EventRegistration.query.filter_by(event_id=event_id).all()
        ws.title = 'المشاركون'
        ws.append(['#', 'الاسم', 'الجنس', 'العمر', 'الهاتف', 'البريد الإلكتروني', 'الفريق', 'المهارات', 'الخبرة السابقة', 'حالة الحضور'])
        for i, reg in enumerate(regs, start=1):
            attendance_status = 'تم التحضير' if reg.attended else 'مسجل (لم يحضر بعد)'
            ws.append([
                i, reg.volunteer.name, reg.volunteer.gender or 'غير محدد',
                reg.volunteer.age or 'غير محدد', reg.volunteer.phone,
                reg.volunteer.email, reg.volunteer.team,
                reg.volunteer.skills or 'لا يوجد',
                reg.volunteer.experience or 'لا يوجد',
                attendance_status
            ])
        filename = f'roster_event_{ev.id}.xlsx'

    for col in ws.columns:
        values = [str(c.value) for c in col if c.value is not None]
        width = max((len(v) for v in values), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(width + 4, 40)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer, as_attachment=True, download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@app.route('/admin/event/delete/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    ev = Event.query.get_or_404(event_id)
    db.session.delete(ev)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
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
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    flash('تم إسناد التكليف الميداني بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/gallery/add', methods=['POST'])
def add_gallery_item():
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    
    # 1. Create the Album
    new_album = Album(
        title=request.form.get('title'),
        category=request.form.get('category', 'عام')
    )
    
    # Handle Cover Image Upload
    cover_file = request.files.get('cover_image')
    if cover_file and cover_file.filename:
        safe_name = secure_filename(f"cover_{datetime.now().strftime('%Y%m%d%H%M%S')}_{cover_file.filename}")
        os.makedirs(app.config.get('UPLOAD_FOLDER', 'static/uploads'), exist_ok=True)
        cover_file.save(os.path.join(app.config.get('UPLOAD_FOLDER', 'static/uploads'), safe_name))
        new_album.cover_image_url = url_for('static', filename=f'uploads/{safe_name}')
    else:
        new_album.cover_image_url = request.form.get('cover_image_url', '') # Fallback to URL if provided

    db.session.add(new_album)
    try:
        db.session.commit() # Commit to get the album ID
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    
    # 2. Handle Multi-Media Upload
    uploaded_files = request.files.getlist('album_media')
    for file in uploaded_files:
        if file and file.filename:
            safe_name = secure_filename(f"media_{new_album.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            os.makedirs(app.config.get('UPLOAD_FOLDER', 'static/uploads'), exist_ok=True)
            file.save(os.path.join(app.config.get('UPLOAD_FOLDER', 'static/uploads'), safe_name))
            
            ext = safe_name.rsplit('.', 1)[-1].lower()
            media_type = 'video' if ext in ['mp4', 'webm', 'ogg', 'mov'] else 'image'
            
            new_media = AlbumMedia(
                album_id=new_album.id,
                media_url=url_for('static', filename=f'uploads/{safe_name}'),
                media_type=media_type
            )
            db.session.add(new_media)
            
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    flash('تمت إضافة الألبوم بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/gallery/delete/<int:item_id>', methods=['POST'])
def delete_gallery_item(item_id):
    if not session.get('admin_logged_in'): return redirect(url_for('index'))
    album = Album.query.get_or_404(item_id)
    db.session.delete(album)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    flash('تم حذف الألبوم.', 'info')
    return redirect(url_for('admin_dashboard'))

# --- إدارة محتوى ومظهر الموقع (CMS) ---


@app.route('/admin/settings/banner', methods=['POST'])
def update_banner():
    if not session.get('admin_logged_in'): return jsonify({'error': 'Unauthorized'}), 403
    sys_settings = SystemSettings.query.first()
    if not sys_settings:
        sys_settings = SystemSettings()
        db.session.add(sys_settings)
    sys_settings.banner_text = request.form.get('banner_text', '')
    sys_settings.is_banner_active = request.form.get('is_banner_active') == 'on'
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    flash('تم تحديث لوحة الإعلانات بنجاح', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/ajax/update_stat', methods=['POST'])
def ajax_update_stat():
    if not session.get('admin_logged_in'): return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    vol_id = data.get('vol_id')
    stat_type = data.get('type')
    action = data.get('action')
    v = Volunteer.query.get(vol_id)
    if not v: return jsonify({'error': 'Not found'}), 404
    
    if stat_type == 'hours':
        if action == 'increment': v.volunteer_hours = (v.volunteer_hours or 0) + 1
        elif action == 'decrement' and (v.volunteer_hours or 0) >= 1: v.volunteer_hours = (v.volunteer_hours or 0) - 1
    elif stat_type == 'events':
        if action == 'increment': v.attended_events_count = (v.attended_events_count or 0) + 1
        elif action == 'decrement' and (v.attended_events_count or 0) > 0: v.attended_events_count = (v.attended_events_count or 0) - 1
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'hours': v.volunteer_hours, 'events': v.attended_events_count})
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'DB Error'}), 500

@app.route('/admin/bulk_approve', methods=['POST'])
def bulk_approve():
    if not session.get('admin_logged_in'): return jsonify({'error': 'Unauthorized'}), 403
    vol_ids = request.form.getlist('vol_ids')
    for vid in vol_ids:
        v = Volunteer.query.get(vid)
        if v:
            v.status = 'approved'
            v.badge_number = None # Or assign next available if logic needed
    try:
        db.session.commit()
        flash('تم اعتماد المتطوعين المحددين بنجاح', 'success')
    except Exception:
        db.session.rollback()
        flash('حدث خطأ', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/bulk_add_hours', methods=['POST'])
def bulk_add_hours():
    if not session.get('admin_logged_in'): return jsonify({'error': 'Unauthorized'}), 403
    vol_ids = request.form.getlist('vol_ids')
    hours = int(request.form.get('hours', 0))
    for vid in vol_ids:
        v = Volunteer.query.get(vid)
        if v: v.volunteer_hours = (v.volunteer_hours or 0) + hours
    try:
        db.session.commit()
        flash('تمت إضافة الساعات للمتطوعين المحددين', 'success')
    except Exception:
        db.session.rollback()
        flash('حدث خطأ', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/bulk_add_events', methods=['POST'])
def bulk_add_events():
    if not session.get('admin_logged_in'): return jsonify({'error': 'Unauthorized'}), 403
    vol_ids = request.form.getlist('vol_ids')
    events = int(request.form.get('events', 0))
    for vid in vol_ids:
        v = Volunteer.query.get(vid)
        if v: v.attended_events_count = (v.attended_events_count or 0) + events
    try:
        db.session.commit()
        flash('تمت إضافة الفعاليات للمتطوعين المحددين', 'success')
    except Exception:
        db.session.rollback()
        flash('حدث خطأ', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/bulk_evaluation', methods=['POST'])
def bulk_evaluation():
    if not session.get('admin_logged_in'): return jsonify({'error': 'Unauthorized'}), 403
    vol_ids = request.form.getlist('vol_ids')
    note = request.form.get('evaluation', '')
    for vid in vol_ids:
        v = Volunteer.query.get(vid)
        if v:
            v.admin_evaluation = (v.admin_evaluation + '\n' + note) if v.admin_evaluation else note
    try:
        db.session.commit()
        flash('تم إضافة الملاحظة للمتطوعين المحددين', 'success')
    except Exception:
        db.session.rollback()
        flash('حدث خطأ', 'error')
    return redirect(url_for('admin_dashboard'))

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

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    flash('تم حفظ الإعدادات وعناوين وصور البطاقات بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

# ==================== التهيئة والترحيل التلقائي لقاعدة البيانات ====================

with app.app_context():
    db.create_all()
    
    migrations = [
        ("system_settings", "banner_text", "VARCHAR(500)"),
        ("system_settings", "is_banner_active", "BOOLEAN DEFAULT FALSE"),

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
        ("volunteers", "badge_number", "VARCHAR(50)"),
        ("volunteers", "gender", "VARCHAR(10)"),
        ("volunteers", "skills", "VARCHAR(200)"),
        ("volunteers", "experience", "TEXT"),
        ("events", "capacity", "INTEGER DEFAULT 10"),
        ("event_registrations", "attended", "BOOLEAN DEFAULT FALSE"),
        ("events", "secret_code", "VARCHAR(10)"),
        ("volunteers", "emergency_contact_name", "VARCHAR(100)"),
        ("volunteers", "emergency_contact_phone", "VARCHAR(20)"),
        ("volunteers", "is_suspended", "BOOLEAN DEFAULT FALSE"),
        ("volunteers", "last_active", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
        ("volunteers", "admin_evaluation", "TEXT")
    ]
    for tbl, col, col_type in migrations:
        try:
            if "sqlite" in app.config['SQLALCHEMY_DATABASE_URI']:
                db.session.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_type};"))
            else:
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