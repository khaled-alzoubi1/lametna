import os
import re
import random
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify, render_template_string
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
# [DEV] Flask-Talisman disabled — port 5000 HSTS cache poisoned; running on clean port 5001.
# from flask_talisman import Talisman
from sqlalchemy.exc import IntegrityError
import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from flask_wtf import CSRFProtect

from flask_wtf import CSRFProtect

from storage import upload_file, is_cloudinary_configured, UploadError, ALLOWED_IMAGE_EXTENSIONS, ALLOWED_MEDIA_EXTENSIONS

load_dotenv()

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True
)
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from io import BytesIO
from openpyxl import Workbook

app = Flask(__name__)

import os
import cloudinary
import cloudinary.uploader

cloudinary.config(
  cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
  api_key=os.environ.get('CLOUDINARY_API_KEY'),
  api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
  secure=True
)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]
)

# [DEV] Talisman fully disabled. Uncomment block below for production.
# csp = {
#     'default-src': [
#         '\'self\'',
#         '\'unsafe-inline\'',
#         '\'unsafe-eval\'',
#         'https://cdn.jsdelivr.net',
#         'https://cdnjs.cloudflare.com',
#         'https://fonts.googleapis.com',
#         'https://fonts.gstatic.com',
#         'https://ka-f.fontawesome.com'
#     ],
#     'img-src': ['*', 'data:'],
#     'font-src': ['*', 'data:']
# }
# DEV: force_https disabled locally to prevent ERR_SSL_PROTOCOL_ERROR / WRONG_VERSION_NUMBER.
# Re-enable (remove force_https=False) before deploying to production.
# Talisman(app, content_security_policy=csp, force_https=False)

# ── Environment detection ──────────────────────────────────────────────────
_is_dev = os.environ.get('FLASK_ENV', 'production').lower() == 'development'
_is_prod = not _is_dev

# ==================== CONFIGURATION VALIDATION ====================

# 1. SECRET_KEY
_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    if _is_dev:
        import secrets
        _secret_key = secrets.token_hex(32)
    else:
        raise RuntimeError("FATAL: SECRET_KEY environment variable is missing. This is a critical security requirement for production.")
app.config['SECRET_KEY'] = _secret_key

# 2. DATABASE_URL
_db_url = os.environ.get('DATABASE_URL')
if not _db_url:
    if _is_dev:
        _db_url = 'sqlite:///local.db'
    else:
        raise RuntimeError("FATAL: DATABASE_URL environment variable is missing. Production requires a valid database connection string (e.g., PostgreSQL).")
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 3. PUBLIC URL SAFETY (ProxyFix)
# Ensures url_for(_external=True) generates correct HTTPS URLs in production (e.g., behind Render proxy)
if _is_prod or os.environ.get('RENDER', '').lower() == 'true':
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)


# ── Session security ────────────────────────────────────────────────────────
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# Secure flag is enabled in production; disabled in dev where HTTPS is not available
app.config['SESSION_COOKIE_SECURE'] = not _is_dev
# Sessions expire after 8 hours — forces re-authentication after long idle periods
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max upload (covers video)

db = SQLAlchemy(app)

from sqlalchemy.engine import Engine
from sqlalchemy import event

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in type(dbapi_connection).__module__:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ── CSRF protection (covers all state-changing browser form POSTs) ─────────
csrf = CSRFProtect(app)

# ── Cloudinary configuration check ──────────────────────────────────────────
import logging as _logging
_startup_logger = _logging.getLogger('storage')
if not _is_dev and not all([
    os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip(),
    os.environ.get('CLOUDINARY_API_KEY', '').strip(),
    os.environ.get('CLOUDINARY_API_SECRET', '').strip(),
]):
    _startup_logger.warning(
        'PRODUCTION MEDIA WARNING: Cloudinary environment variables are not set. '
        'File uploads will fail in production. Set CLOUDINARY_CLOUD_NAME, '
        'CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET.'
    )


# ==================== Blueprint Registration (Strangler Fig) ====================
from controllers.certificates import certificates_bp
app.register_blueprint(certificates_bp)

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

    # Featured Story fields
    featured_story_title = db.Column(db.String(250), nullable=True)
    featured_story_desc = db.Column(db.Text, nullable=True)
    featured_story_image_url = db.Column(db.String(500), nullable=True)
    featured_story_cta_text = db.Column(db.String(100), nullable=True)
    featured_story_cta_link = db.Column(db.String(500), nullable=True)

    # Impact fields
    impact_section_title = db.Column(db.String(250), nullable=True)
    impact_section_desc = db.Column(db.Text, nullable=True)
    impact_image_url = db.Column(db.String(500), nullable=True)
    impact_cta_text = db.Column(db.String(100), nullable=True)
    impact_cta_link = db.Column(db.String(500), nullable=True)

    # Closing CTA fields
    closing_cta_title = db.Column(db.String(250), nullable=True)
    closing_cta_desc = db.Column(db.Text, nullable=True)

    stat_label_hours = db.Column(db.String(100), nullable=True)
    stat_label_volunteers = db.Column(db.String(100), nullable=True)
    stat_label_events = db.Column(db.String(100), nullable=True)

    activities_section_title = db.Column(db.String(250), nullable=True)
    activities_section_desc = db.Column(db.Text, nullable=True)

    gallery_section_title = db.Column(db.String(250), nullable=True)
    gallery_section_desc = db.Column(db.Text, nullable=True)

    footer_about_text = db.Column(db.Text, nullable=True)
    contact_phone1 = db.Column(db.String(50), nullable=True)
    contact_phone2 = db.Column(db.String(50), nullable=True)


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

class Interest(db.Model):
    __tablename__ = 'interests'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Skill(db.Model):
    __tablename__ = 'skills'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

volunteer_interests = db.Table('volunteer_interests',
    db.Column('volunteer_id', db.Integer, db.ForeignKey('volunteers.id', ondelete='CASCADE'), primary_key=True),
    db.Column('interest_id', db.Integer, db.ForeignKey('interests.id', ondelete='CASCADE'), primary_key=True)
)

volunteer_skills = db.Table('volunteer_skills',
    db.Column('volunteer_id', db.Integer, db.ForeignKey('volunteers.id', ondelete='CASCADE'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skills.id', ondelete='CASCADE'), primary_key=True)
)

event_interests = db.Table('event_interests',
    db.Column('event_id', db.Integer, db.ForeignKey('events.id', ondelete='CASCADE'), primary_key=True),
    db.Column('interest_id', db.Integer, db.ForeignKey('interests.id', ondelete='CASCADE'), primary_key=True)
)

event_skills = db.Table('event_skills',
    db.Column('event_id', db.Integer, db.ForeignKey('events.id', ondelete='CASCADE'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skills.id', ondelete='CASCADE'), primary_key=True)
)

class Volunteer(db.Model):
    __tablename__ = 'volunteers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
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

    # Structured Personalization Signals
    interests_rel = db.relationship('Interest', secondary=volunteer_interests, lazy='subquery',
        backref=db.backref('volunteers', lazy=True))
    structured_skills = db.relationship('Skill', secondary=volunteer_skills, lazy='subquery',
        backref=db.backref('volunteers', lazy=True))
    emergency_contact_phone = db.Column(db.String(20), nullable=True)
    is_suspended = db.Column(db.Boolean, default=False)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    admin_evaluation = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # العلاقات التابعة
    duties = db.relationship('Duty', backref='volunteer', lazy=True, cascade="all, delete-orphan")
    excuses = db.relationship('Excuse', backref='volunteer', lazy=True, cascade="all, delete-orphan")
    registrations = db.relationship('EventRegistration', backref='volunteer', lazy=True, cascade="all, delete-orphan")
    training_progress = db.relationship('TrainingProgress', backref='volunteer_rel', lazy=True, cascade='all, delete-orphan')

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


class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TeamMembership(db.Model):
    __tablename__ = 'team_memberships'
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id', ondelete='CASCADE'), primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id', ondelete='CASCADE'), primary_key=True)
    role = db.Column(db.String(20), default='MEMBER')  # MEMBER, LEADER
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    volunteer = db.relationship('Volunteer', backref=db.backref('team_memberships', lazy='dynamic', cascade='all, delete-orphan'))
    team = db.relationship('Team', backref=db.backref('memberships', lazy='dynamic', cascade='all, delete-orphan'))

class Goal(db.Model):
    __tablename__ = 'goals'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    target_value = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='ACTIVE') # ACTIVE, ACHIEVED, ARCHIVED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    team = db.relationship('Team', backref=db.backref('goals', lazy='dynamic', cascade='all, delete-orphan'))


class TrainingCourse(db.Model):
    __tablename__ = 'training_courses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    cover_image_url = db.Column(db.String(500), nullable=True)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    modules = db.relationship('TrainingModule', backref='course', lazy=True, cascade='all, delete-orphan')

class TrainingModule(db.Model):
    __tablename__ = 'training_modules'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('training_courses.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    content_type = db.Column(db.String(50), nullable=True)
    content_url = db.Column(db.String(500), nullable=True)
    position = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    progress_records = db.relationship('TrainingProgress', backref='module', lazy=True, cascade='all, delete-orphan')

class TrainingProgress(db.Model):
    __tablename__ = 'training_progress'
    id = db.Column(db.Integer, primary_key=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id', ondelete='CASCADE'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('training_modules.id', ondelete='CASCADE'), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('volunteer_id', 'module_id', name='uq_volunteer_module_progress'),
    )


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    # Safe path toward structured datetimes (nullable for now, no destructive migration)
    starts_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)
    location = db.Column(db.String(150), nullable=False)
    capacity = db.Column(db.Integer, default=10)
    event_hours = db.Column(db.Integer, default=3)  # المقاعد المطلوبة للميدان
    secret_code = db.Column(db.String(10), nullable=True)
    status = db.Column(db.String(50), nullable=True) # Explicit lifecycle state
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    team_id = db.Column(db.Integer, db.ForeignKey('teams.id', ondelete='SET NULL'), nullable=True)
    team = db.relationship('Team', backref=db.backref('events', lazy='dynamic'))

    registrations = db.relationship('EventRegistration', backref='event', lazy=True, cascade="all, delete-orphan")

    interests_rel = db.relationship('Interest', secondary=event_interests, lazy='subquery',
        backref=db.backref('events_rel', lazy=True))
    structured_skills = db.relationship('Skill', secondary=event_skills, lazy='subquery',
        backref=db.backref('events_rel', lazy=True))

    @property
    def registered_count(self):
        return sum(1 for r in self.registrations if r.is_active)

    @property
    def remaining_seats(self):
        rem = self.capacity - self.registered_count
        return rem if rem > 0 else 0

    @property
    def is_full(self):
        return self.registered_count >= self.capacity

    @property
    def is_completed(self):
        if self.status:
            return self.status == 'COMPLETED'

        # Fallback to legacy date-based logic for unmigrated data
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

    @property
    def is_cancelled(self):
        return self.status == 'CANCELLED'

    @property
    def is_today(self):
        if not self.date:
            return False
        raw_date = str(self.date).strip()
        today = datetime.now().date()

        event_date = None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y'):
            try:
                event_date = datetime.strptime(raw_date, fmt).date()
                break
            except (ValueError, TypeError):
                pass

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

        return event_date == today

    @property
    def is_cancelled(self):
        return self.status == 'CANCELLED'

    @property
    def is_today(self):
        if not self.date:
            return False
        raw_date = str(self.date).strip()
        today = datetime.now().date()

        event_date = None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y'):
            try:
                event_date = datetime.strptime(raw_date, fmt).date()
                break
            except (ValueError, TypeError):
                pass

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

        return event_date == today

class EventRegistration(db.Model):
    __tablename__ = 'event_registrations'
    __table_args__ = (
        db.UniqueConstraint('volunteer_id', 'event_id', name='uix_volunteer_event'),
    )
    id = db.Column(db.Integer, primary_key=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    attended = db.Column(db.Boolean, default=False)  # حالة التحضير الميداني
    status = db.Column(db.String(50), nullable=True) # Explicit registration state
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_active(self):
        """True if the registration consumes capacity."""
        # None is allowed for legacy compatibility before migration
        return self.status in [None, 'REGISTERED', 'ATTENDED']

class HourLedger(db.Model):
    """
    Foundation for the future source of truth for volunteer hours.
    Tracks every discrete mutation of hours (addition or subtraction).
    """
    __tablename__ = 'hour_ledger'
    id = db.Column(db.Integer, primary_key=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id'), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True, index=True)
    hours = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    idempotency_key = db.Column(db.String(100), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    """
    P1: Reflects state changes to volunteers as in-app notifications.
    Notifications NEVER create or mutate state; they reflect it.
    Idempotency is enforced via (volunteer_id, reference_id) unique index when reference_id is not None.
    """
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id', ondelete='CASCADE'), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False)      # e.g. 'REGISTRATION', 'ATTENDANCE', 'SYSTEM'
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    reference_id = db.Column(db.String(150), nullable=True)  # idempotency key / context
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    volunteer = db.relationship('Volunteer', backref=db.backref('notifications', lazy='dynamic', cascade='all, delete-orphan'))

class EventFeedback(db.Model):
    """
    P1: Volunteer feedback for a completed event.
    One feedback record per volunteer per event (enforced by unique index).
    Only ATTENDED volunteers may submit feedback.
    """
    __tablename__ = 'event_feedback'
    __table_args__ = (
        db.UniqueConstraint('volunteer_id', 'event_id', name='uix_feedback_volunteer_event'),
    )
    id = db.Column(db.Integer, primary_key=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id', ondelete='CASCADE'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)       # 1-5
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    volunteer = db.relationship('Volunteer', backref=db.backref('feedbacks', lazy='dynamic'))
    event = db.relationship('Event', backref=db.backref('feedbacks', lazy='dynamic'))

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

# ==================== Lifecycle Logic Helpers ====================

def can_register(event: Event) -> bool:
    """True if volunteer can theoretically register (does not check capacity)."""
    if event.is_cancelled or event.is_completed:
        return False
    # If no status or REGISTRATION_OPEN, allow registration
    return event.status in [None, 'REGISTRATION_OPEN', 'IN_PROGRESS']

def can_edit(event: Event) -> bool:
    """True if admin can edit the event."""
    # To be safe, don't allow deep edits of cancelled/completed events unless an admin overrides
    return not event.is_completed and not event.is_cancelled

def can_cancel(event: Event) -> bool:
    """True if admin can cancel the event."""
    return not event.is_completed and not event.is_cancelled

def can_complete(event: Event) -> bool:
    """True if admin can explicitly mark event as completed."""
    return not event.is_cancelled and not event.is_completed

def change_registration_status(registration: EventRegistration, new_status: str) -> bool:
    """Centralized safety for registration state transitions."""
    # Legacy compatibility treat None as REGISTERED conceptually for transitions
    old_status = registration.status or 'REGISTERED'

    if old_status == new_status:
        registration.status = new_status # Ensure None becomes explicit
        return True

    if old_status == 'ATTENDED' and new_status == 'CANCELLED':
        return False

    if old_status == 'CANCELLED' and new_status == 'ATTENDED':
        return False

    if old_status == 'WAITLISTED' and new_status == 'ATTENDED':
        return False

    registration.status = new_status
    return True

def migrate_event_lifecycle():
    """
    Deterministic mapping of legacy date-based implicit states to the new explicit lifecycle.
    DO NOT CALL ON STARTUP automatically. Run manually during cutover.
    """
    events = Event.query.all()
    for ev in events:
        if ev.status is not None:
            continue

        # If the date-based logic says it's completed, it's completed
        if ev.is_completed:
            ev.status = 'COMPLETED'
        else:
            # Otherwise it was active/open
            ev.status = 'REGISTRATION_OPEN'
    db.session.commit()

def migrate_registration_state():
    """
    Deterministic mapping of legacy boolean attendance to explicit registration states.
    DO NOT CALL ON STARTUP automatically. Run manually during cutover.
    """
    regs = EventRegistration.query.all()
    for reg in regs:
        if reg.status is not None:
            continue

        if reg.attended:
            reg.status = 'ATTENDED'
        else:
            # If not attended, it was active (CONFIRMED/REGISTERED).
            # We map legacy active to REGISTERED as a safe baseline.
            reg.status = 'REGISTERED'
    db.session.commit()

# ==================== Business Logic Helpers ====================

def record_hours(volunteer, hours_delta: float, reason: str, event_id: int = None, idempotency_key: str = None) -> bool:
    """
    Central Hour Service: Validates, creates ledger entry, and updates compatibility cache.
    Returns True if hours were applied, False if skipped (due to idempotency or 0 delta).
    Does NOT commit to the database.
    """
    if hours_delta == 0:
        return False

    if idempotency_key:
        existing = HourLedger.query.filter_by(idempotency_key=idempotency_key).first()
        if existing:
            return False

    ledger = HourLedger(
        volunteer_id=volunteer.id,
        event_id=event_id,
        hours=hours_delta,
        reason=reason,
        idempotency_key=idempotency_key
    )
    db.session.add(ledger)

    # Lock the row and refresh the object state to prevent concurrent cache clobbering
    locked_v = db.session.query(Volunteer).with_for_update().populate_existing().get(volunteer.id)
    if locked_v:
        locked_v.volunteer_hours = (locked_v.volunteer_hours or 0) + hours_delta
        locked_v.auto_assign_badges()

    return True

def mark_attendance_and_grant_hours(registration) -> int:
    """
    Business Logic: Awards hours and marks attendance via the Hour Service.
    Does NOT commit to the database; caller must wrap in a transaction.
    Returns the number of hours awarded.

    Concurrency Safety:
    On PostgreSQL: acquires a row-level lock on the parent Event BEFORE creating
    a HourLedger entry. This ensures serialization with EventTeamAssignmentService.assign_team,
    which also locks the Event row. Whichever path acquires the lock first wins;
    the loser sees the updated state after waiting.

    Lock order: Event (first) → Volunteer (second). Must never be reversed.

    On SQLite (tests): FOR UPDATE is not supported. The HourLedger idempotency_key
    unique constraint acts as the final defense against double-credit.
    """
    if registration.attended or registration.status == 'ATTENDED':
        return 0

    if not change_registration_status(registration, 'ATTENDED'):
        # Transition blocked (e.g. they were CANCELLED or WAITLISTED)
        return 0

    ev = registration.event
    vol = registration.volunteer
    hours_to_award = ev.event_hours if (ev and ev.event_hours) else 3

    # Acquire Event row lock BEFORE creating the HourLedger entry (PostgreSQL only).
    # This serializes with assign_team which also acquires the Event lock.
    if ev and ev.id:
        is_sqlite = 'sqlite' in app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if not is_sqlite:
            # Re-fetch and lock the event row. If assign_team is mid-transaction,
            # this will block until that transaction commits or rolls back.
            locked_ev = db.session.query(Event).with_for_update().populate_existing().get(ev.id)
        # On SQLite, skip the lock — rely on idempotency key.

    # Use attendance as the authoritative reason and idempotency context
    applied = record_hours(
        volunteer=vol,
        hours_delta=hours_to_award,
        reason=f"حضور الفعالية الميدانية: {ev.title if ev else 'غير محدد'}",
        event_id=ev.id if ev else None,
        idempotency_key=f"attendance:reg:{registration.id}" if registration.id else None
    )

    registration.attended = True
    if applied:
        vol.attended_events_count = (vol.attended_events_count or 0) + 1
        vol.auto_assign_badges()

        # Restore P1 notification
        notify_volunteer(
            volunteer_id=vol.id,
            notif_type='ATTENDANCE',
            title='تم تسجيل حضورك',
            message=f'شكراً لحضورك فعالية "{ev.title if ev else "الفعالية"}". تمت إضافة {hours_to_award} ساعات لرصيدك!',
            reference_id=f"attendance:reg:{registration.id}:confirmed" if registration.id else None
        )

    return hours_to_award

def notify_volunteer(volunteer_id: int, notif_type: str, title: str, message: str, reference_id: str = None) -> 'Notification':
    """
    P1 Notification Service: Reflects a state change to a volunteer as an in-app notification.

    NEVER call this before the state mutation has occurred.
    Notifications REFLECT state; they do not CREATE state.

    Idempotency: If reference_id is provided and a notification with the same
    (volunteer_id, reference_id) already exists, returns the existing notification
    without creating a duplicate. If reference_id is None, allows duplicates.

    Does NOT commit — caller must commit the enclosing transaction.
    Returns the Notification instance (existing or newly created).
    """
    if reference_id:
        existing = Notification.query.filter_by(
            volunteer_id=volunteer_id,
            reference_id=reference_id
        ).first()
        if existing:
            return existing

    n = Notification(
        volunteer_id=volunteer_id,
        type=notif_type,
        title=title[:200],
        message=message,
        reference_id=reference_id,
        is_read=False,
    )
    db.session.add(n)
    return n

def backfill_legacy_hours():
    """
    Idempotent migration function to backfill existing volunteer_hours
    into the HourLedger as a 'legacy baseline' entry.
    """
    # Fetch all IDs first to avoid long-running queries locking the whole table
    volunteer_ids = [v.id for v in Volunteer.query.all()]

    for vid in volunteer_ids:
        try:
            # Lock the volunteer row to prevent concurrent hours updates during backfill
            v = db.session.query(Volunteer).with_for_update().get(vid)
            if not v:
                continue

            current_hours = v.volunteer_hours or 0
            if current_hours <= 0:
                db.session.commit()
                continue

            baseline_key = f"baseline_migration:{v.id}"
            existing = HourLedger.query.filter_by(idempotency_key=baseline_key).first()
            if existing:
                db.session.commit()
                continue

            existing_ledger_sum = db.session.query(db.func.sum(HourLedger.hours)).filter(HourLedger.volunteer_id == v.id).scalar() or 0
            baseline_delta = current_hours - existing_ledger_sum

            if baseline_delta < 0:
                app.logger.error(f"INCONSISTENT HOURS FOR VOLUNTEER {v.id}: Ledger sum ({existing_ledger_sum}) > Cache ({current_hours}). Cannot safely reconcile. Skipping.")
                db.session.rollback()
                continue
            elif baseline_delta > 0:
                ledger = HourLedger(
                    volunteer_id=v.id,
                    event_id=None,
                    hours=baseline_delta,
                    reason="رصيد الساعات السابق (Legacy Baseline)",
                    idempotency_key=baseline_key
                )
                db.session.add(ledger)

            db.session.commit()
        except Exception as e:
            app.logger.error(f"Error backfilling volunteer {vid}: {e}")
            db.session.rollback()

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

# ==================== Security: Admin Authorization Guard ====================
# The two admin accounts are identified solely by their email addresses.
# These must also be set in ADMIN_EMAILS env var for production.
# They are kept here as the authoritative source-of-truth for the server-side check.
_ADMIN_EMAILS = frozenset({
    'lanooshabdo7@gmail.com',
    'khaledsalzoubi1352006@gmail.com',
})

def is_admin_session() -> bool:
    """Return True only when the current session belongs to one of the two designated admins.
    This is the single authoritative check used on every admin-only route.
    `admin_logged_in` flag alone is insufficient — we always verify the email too.
    """
    return bool(
        session.get('admin_logged_in') and
        session.get('admin_email', '').lower() in _ADMIN_EMAILS
    )


def _require_admin():
    """Call at the top of any admin route. Returns a redirect response if unauthorized,
    or None when the caller may proceed."""
    if not is_admin_session():
        flash('غير مصرح لك بدخول لوحة التحكم.', 'danger')
        return redirect(url_for('index'))
    return None


# ==================== المسارات العامة ====================


@app.route('/')
def index():
    settings = get_settings()
    valid_positions = ['ليدر', 'رئيس لجان', 'هيئة إدارية', 'رئيس الفريق', 'نائب رئيس الفريق', 'مدرب معتمد']
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
    # --- Public homepage: only show upcoming/active events (exclude past dates and cancelled) ---
    all_public_events = Event.query.order_by(Event.id.desc()).all()
    upcoming_events = [ev for ev in all_public_events if not ev.is_completed and not ev.is_cancelled]

    # Homepage event cards (max 4, upcoming only)
    events = upcoming_events[:4]

    albums = Album.query.order_by(Album.id.desc()).all()

    top_volunteers = Volunteer.query.filter_by(status='approved')\
                                    .order_by(Volunteer.volunteer_hours.desc(), Volunteer.attended_events_count.desc())\
                                    .limit(5).all()

    volunteers_count = Volunteer.query.filter_by(status='approved').count()
    hours_count = db.session.query(db.func.sum(Volunteer.volunteer_hours)).scalar() or 0
    events_count = Event.query.filter_by(status='COMPLETED').count()

    stats = {
        'volunteers_count': volunteers_count,
        'hours_count': hours_count,
        'events_count': events_count
    }

    user_registered_event_ids = []
    user_attended_event_ids = []
    if 'user_id' in session:
        regs = EventRegistration.query.filter_by(volunteer_id=session['user_id']).all()
        user_registered_event_ids = [r.event_id for r in regs]
        user_attended_event_ids = [r.event_id for r in regs if r.attended]

    # Volunteer profile event list: upcoming only (max 15) so they can still register
    recent_events = upcoming_events[:15]

    return render_template(
        'index.html',
        settings=settings,
        leaders=leaders,
        events=events,
        recent_events=recent_events,
        albums=albums,
        top_volunteers=top_volunteers,
        stats=stats,
        user_registered_event_ids=user_registered_event_ids,
        user_attended_event_ids=user_attended_event_ids
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        gender = request.form.get('gender', '').strip()

        import re as regex
        if not regex.match(r'^[\u0600-\u06FF\s]+$', name):
            db.session.rollback()
            flash('يرجى إدخال الاسم باللغة العربية فقط', 'danger')
            return redirect(url_for('index'))

        if gender not in ['ذكر', 'أنثى']:
            db.session.rollback()
            flash('يرجى تحديد الجنس بشكل صحيح', 'danger')
            return redirect(url_for('index'))

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
            flash('تم تسجيلك بنجاح! طلبك الآن قيد المراجعة.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('رقم الهاتف أو البريد الإلكتروني مسجل مسبقاً', 'danger')
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ أثناء التسجيل، يرجى المحاولة لاحقاً', 'danger')

        return redirect(url_for('index'))

    return render_template('register.html')

# ── Admin credential bootstrap ─────────────────────────────────────────────
# Passwords are NOT stored in source code. They live exclusively in the database
# (as bcrypt hashes). The env vars below are used ONLY on first boot to create
# the admin DB record when it does not yet exist.
#
# Required production env vars (set in Render):
#   ADMIN1_EMAIL     e.g. lanooshabdo7@gmail.com
#   ADMIN1_PASSWORD  (plain text — used once to seed the DB hash, then discarded)
#   ADMIN1_NAME
#   ADMIN1_PHONE
#   ADMIN1_POSITION
#   ADMIN2_EMAIL     e.g. khaledsalzoubi1352006@gmail.com
#   ADMIN2_PASSWORD
#   ADMIN2_NAME
#   ADMIN2_PHONE
#   ADMIN2_POSITION
#
# At runtime, authentication is ALWAYS checked against check_password_hash(db_hash, password).
# If env vars are absent after first boot, existing DB hashes continue to work.

def _bootstrap_admin(email, password, name, phone, position):
    """Create admin volunteer DB record on first boot if it does not exist.
    The password is immediately hashed; the plain-text value is never retained."""
    if not email or not password:
        return
    existing = Volunteer.query.filter_by(email=email).first()
    if existing:
        return  # Already seeded — do not overwrite
    admin_vol = Volunteer(
        name=name or email,
        email=email,
        phone=phone or '0000000000',
        password_hash=generate_password_hash(password),
        city='عمان',
        team='عمان',
        status='approved',
        is_leader=True,
        position=position or 'إدارة',
    )
    db.session.add(admin_vol)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


@app.route('/login', methods=['GET', 'POST'])
# Rate limit: per submitted email address, not per IP.
# This prevents shared venue Wi-Fi from locking out all volunteers
# (many different emails behind one IP) while still blocking per-account brute-force.
@limiter.limit(
    "10 per 15 minutes",
    key_func=lambda: request.form.get('email', '').strip().lower() or get_remote_address(),
    exempt_when=lambda: request.method != 'POST',
)
def login():
    if request.method == 'POST':
        identifier = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        # ── Admin path: email must be in the _ADMIN_EMAILS whitelist ──────────
        if identifier in _ADMIN_EMAILS:
            admin_user = Volunteer.query.filter_by(email=identifier).first()
            if admin_user and check_password_hash(admin_user.password_hash, password):
                admin_user.last_active = datetime.utcnow()
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()

                session.clear()
                session.permanent = True          # respect PERMANENT_SESSION_LIFETIME
                session['admin_logged_in'] = True
                session['admin_email'] = identifier
                session['user_id'] = admin_user.id
                greeting = 'أهلاً بكِ يا' if admin_user.gender == 'أنثى' else 'أهلاً بك يا'
                flash(f'{greeting} {admin_user.name} في لوحة التحكم الإدارية.', 'success')
                return redirect(url_for('admin_dashboard'))

            # Do not reveal whether the email exists
            flash('بيانات الدخول غير صحيحة، يرجى التحقق من البريد وكلمة المرور.', 'danger')
            return redirect(url_for('index'))

        # ── Volunteer path ────────────────────────────────────────────────────
        volunteer = Volunteer.query.filter_by(email=identifier).first()
        if volunteer and check_password_hash(volunteer.password_hash, password):
            if volunteer.is_suspended:
                flash('تم تعليق حسابك. تواصل مع الإدارة للاستفسار.', 'danger')
                return redirect(url_for('index'))
            volunteer.last_active = datetime.utcnow()
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
            session.clear()
            session.permanent = True              # respect PERMANENT_SESSION_LIFETIME
            session['user_id'] = volunteer.id
            flash(f'أهلاً بك مجدداً يا {volunteer.name}', 'success')
            return redirect(url_for('profile'))

        flash('بيانات الدخول غير صحيحة، يرجى التحقق من البريد وكلمة المرور.', 'danger')
        return redirect(url_for('index'))

    return render_template('login.html')


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

@app.route('/delete_inquiry/<int:id>', methods=['POST'])
def delete_inquiry(id):
    if not is_admin_session():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    inquiry = Inquiry.query.get_or_404(id)
    db.session.delete(inquiry)
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

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

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        volunteers = Volunteer.query.filter_by(status='approved').all()
        return render_template('partials/volunteers.html', volunteers=volunteers, settings=settings)

    duties = Duty.query.filter_by(volunteer_id=user.id).order_by(Duty.due_date.asc()).all()
    user_registrations = EventRegistration.query.filter_by(volunteer_id=user.id).all()
    registered_event_ids = [r.event_id for r in user_registrations]
    attended_map = {r.event_id: r.attended for r in user_registrations}

    user_events = Event.query.filter(Event.id.in_(registered_event_ids)).order_by(Event.id.desc()).all() if registered_event_ids else []

    past_attended_events = [ev for ev in user_events if attended_map.get(ev.id) and ev.is_completed]

    now = datetime.now()
    
    from services.training import TrainingVolunteerService
    training_courses_progress = TrainingVolunteerService.get_all_courses_progress(user.id)

    return render_template(
        'profile.html',
        user=user,
        user_events=user_events,
        duties=duties,
        settings=settings,
        registered_event_ids=registered_event_ids,
        attended_map=attended_map,
        now=now,
        past_attended_events=past_attended_events,
        training_courses_progress=training_courses_progress
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

    # Handle profile photo upload via storage adapter (Cloudinary / local-dev fallback)
    uploaded_file = request.files.get('profile_image')
    if uploaded_file and uploaded_file.filename:
        try:
            photo_url = upload_file(uploaded_file, folder='profile_photos',
                                    allowed_extensions=ALLOWED_IMAGE_EXTENSIONS)
            user.photo_url = photo_url
        except UploadError as e:
            flash(str(e), 'danger')
            return redirect(url_for('profile'))
    else:
        # Fallback to URL if no file uploaded
        photo_url_field = request.form.get('photo_url')
        if photo_url_field:
            user.photo_url = photo_url_field

    new_password = request.form.get('new_password', '').strip()
    if new_password:
        user.password_hash = generate_password_hash(new_password)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
        return redirect(url_for('profile'))
    flash('تم تحديث ملفك الشخصي بنجاح.', 'success')
    return redirect(url_for('profile'))

@app.route('/events')
def events_list():
    settings = get_settings()
    all_events = Event.query.order_by(Event.date.desc(), Event.time.desc()).all()

    user_registered_event_ids = []
    user_waitlisted_event_ids = []
    user_attended_event_ids = []

    if session.get('user_id'):
        user_regs = EventRegistration.query.filter_by(volunteer_id=session['user_id']).all()
        user_registered_event_ids = [r.event_id for r in user_regs if r.status == 'REGISTERED']
        user_waitlisted_event_ids = [r.event_id for r in user_regs if r.status == 'WAITLISTED']
        user_attended_event_ids = [r.event_id for r in user_regs if r.attended]

    return render_template('events.html',
                           events=all_events,
                           settings=settings,
                           user_registered_event_ids=user_registered_event_ids,
                           user_waitlisted_event_ids=user_waitlisted_event_ids,
                           user_attended_event_ids=user_attended_event_ids)

@app.route('/events/<int:event_id>')
def event_detail(event_id):
    settings = get_settings()
    event = Event.query.get_or_404(event_id)

    is_registered = False
    is_waitlisted = False
    is_attended = False
    has_feedback = False

    if session.get('user_id'):
        reg = EventRegistration.query.filter_by(volunteer_id=session['user_id'], event_id=event_id).first()
        if reg:
            is_registered = (reg.status == 'REGISTERED')
            is_waitlisted = (reg.status == 'WAITLISTED')
            is_attended = reg.attended

        fb = EventFeedback.query.filter_by(volunteer_id=session['user_id'], event_id=event_id).first()
        if fb:
            has_feedback = True

    return render_template('event_detail.html',
                           event=event,
                           settings=settings,
                           is_registered=is_registered,
                           is_waitlisted=is_waitlisted,
                           is_attended=is_attended,
                           has_feedback=has_feedback)

@app.route('/events/rsvp/<int:event_id>', methods=['POST'])
def rsvp_event(event_id):
    if 'user_id' not in session:
        flash('يرجى تسجيل الدخول أولاً.', 'danger')
        return redirect(url_for('index'))

    user = Volunteer.query.get_or_404(session['user_id'])
    if user.status != 'approved':
        flash('يجب أن يكون حسابك معتمداً من الإدارة لتأكيد المشاركة.', 'danger')
        return redirect(request.referrer or url_for('profile'))

    # On PostgreSQL: lock the event row first so that concurrent requests serialize here.
    # The duplicate check and capacity check must both happen inside the same transaction
    # as the INSERT so no window exists between check and write.
    # On SQLite: no row-level locking is available; the UNIQUE INDEX is the final defense.
    is_sqlite = 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']
    if is_sqlite:
        ev = Event.query.get_or_404(event_id)
    else:
        ev = Event.query.filter_by(id=event_id).with_for_update().first_or_404()

    if not can_register(ev):
        flash('انتهت هذه الفعالية أو تم إلغاؤها ولا يمكن التسجيل بها', 'danger')
        return redirect(request.referrer or url_for('profile'))

    # Both checks use a fresh DB count to avoid ORM session cache stale reads.
    # These queries run INSIDE the FOR UPDATE transaction on Postgres.
    existing_reg = EventRegistration.query.filter_by(volunteer_id=user.id, event_id=ev.id).first()
    if existing_reg and existing_reg.is_active:
        flash('أنت مسجل مسبقاً في هذا النشاط الميداني.', 'info')
        return redirect(request.referrer or url_for('profile'))

    # Only count ACTIVE registrations towards capacity
    current_count = EventRegistration.query.filter(
        EventRegistration.event_id == ev.id,
        db.or_(EventRegistration.status.is_(None), EventRegistration.status.notin_(['CANCELLED', 'WAITLISTED']))
    ).count()

    if current_count >= ev.capacity:
        flash('اكتمل العدد المطلوب للميدان في هذه الفعالية.', 'danger')
        return redirect(request.referrer or url_for('profile'))

    if existing_reg:
        if not change_registration_status(existing_reg, 'REGISTERED'):
            flash('لا يمكن إعادة التسجيل في هذه الفعالية.', 'danger')
            return redirect(request.referrer or url_for('profile'))
    else:
        new_reg = EventRegistration(volunteer_id=user.id, event_id=ev.id, status='REGISTERED')
        db.session.add(new_reg)
    try:
        db.session.commit()
        flash(f'تم حجز مقعدك بنجاح في: {ev.title}.', 'success')
    except IntegrityError:
        # Final defense: the UNIQUE INDEX catches any race that bypassed the app-level check.
        db.session.rollback()
        flash('أنت مسجل مسبقاً في هذا النشاط الميداني.', 'info')
    except Exception:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')

    return redirect(request.referrer or url_for('profile'))

@app.route('/events/cancel_rsvp/<int:event_id>', methods=['POST'])
def cancel_rsvp(event_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))

    reg = EventRegistration.query.filter_by(volunteer_id=session['user_id'], event_id=event_id).first()
    if reg:
        if not change_registration_status(reg, 'CANCELLED'):
            flash('لا يمكن إلغاء التسجيل لأنك حضرت الفعالية بالفعل.', 'danger')
            return redirect(request.referrer or url_for('profile'))

        try:
            notify_volunteer(reg.volunteer_id, 'REGISTRATION', 'إلغاء التسجيل', 'تم إلغاء تسجيلك في فعالية ' + reg.event.title, f'registration:{reg.id}:cancelled')
            db.session.commit()
            flash('تم إلغاء حجزك في الفعالية وفتح المقعد لمتطوع آخر.', 'info')
        except Exception:
            db.session.rollback()
            flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
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

    if not reg.is_active:
        flash('لا يمكنك تأكيد الحضور لأن حجزك ملغى أو غير فعال.', 'danger')
        return redirect(request.referrer or url_for('profile'))

    if reg.attended or reg.status == 'ATTENDED':
        flash('تم تسجيل حضورك مسبقاً في هذه الفعالية.', 'info')
        return redirect(request.referrer or url_for('profile'))

    # مطابقة الكود السري
    if ev.secret_code and entered_code == str(ev.secret_code).strip():
        hours_to_award = mark_attendance_and_grant_hours(reg)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
            return redirect(request.referrer or url_for('profile'))
        flash(f'تم حجز مقعدك بنجاح في: {ev.title}.', 'success')
    else:
        flash('كود التحضير غير صحيح! يرجى مراجعة مسؤول الميدان.', 'danger')

    return redirect(request.referrer or url_for('profile'))

@app.route('/verify_attendance_code/<int:event_id>', methods=['GET', 'POST'])
@limiter.limit("5 per 5 minutes", key_func=lambda: session.get('user_id', get_remote_address()), exempt_when=lambda: request.method != 'POST')
def verify_attendance_code(event_id):
    if 'user_id' not in session:
        flash('يرجى تسجيل الدخول أولاً لتأكيد الحضور.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        entered_code = request.form.get('secret_code', '').strip()
    else:
        entered_code = request.args.get('token', '').strip()

    ev = Event.query.get_or_404(event_id)
    user = Volunteer.query.get_or_404(session['user_id'])

    if ev.is_cancelled or ev.is_completed:
        flash('لا يمكن تسجيل الحضور لأن الفعالية منتهية أو ملغاة.', 'danger')
        return redirect(request.referrer or url_for('profile'))

    reg = EventRegistration.query.filter_by(volunteer_id=user.id, event_id=ev.id).first()
    if not reg:
        flash('أنت غير مسجل بهذه الفعالية.', 'danger')
        return redirect(request.referrer or url_for('profile'))

    if not reg.is_active:
        flash('تسجيلك غير فعال ولا يمكنك تسجيل الحضور.', 'danger')
        return redirect(request.referrer or url_for('profile'))

    if reg.attended or reg.status == 'ATTENDED':
        flash('لقد قمت بتسجيل الحضور مسبقاً في هذه الفعالية.', 'info')
        return redirect(request.referrer or url_for('profile'))

    if ev.secret_code and entered_code == str(ev.secret_code).strip():
        # Using the centralized idempotent helper
        hours_to_award = mark_attendance_and_grant_hours(reg)
        if hours_to_award == 0 and not reg.attended:
            # It was blocked by change_registration_status
            flash('تعذر تسجيل الحضور بسبب حالة التسجيل الحالية.', 'danger')
            return redirect(request.referrer or url_for('profile'))

        try:
            db.session.commit()
            flash(f'تم تسجيل الحضور بنجاح ومنح {hours_to_award} ساعة.', 'success')
        except Exception:
            db.session.rollback()
            flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    else:
        flash('كود التحضير غير صحيح! يرجى المحاولة مرة أخرى.', 'danger')

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

# ==================== P1: Notification Routes ====================

@app.route('/notifications')
def get_notifications():
    """Return JSON list of notifications for the authenticated volunteer. Ordered newest first."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    notifications = Notification.query.filter_by(
        volunteer_id=session['user_id']
    ).order_by(Notification.created_at.desc()).limit(50).all()

    return jsonify({
        'notifications': [
            {
                'id': n.id,
                'type': n.type,
                'title': n.title,
                'message': n.message,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ]
    })


@app.route('/notifications/read/<int:notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    """Mark a notification as read. Returns 404 if the notification does not belong to the user."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    n = Notification.query.filter_by(
        id=notification_id,
        volunteer_id=session['user_id']
    ).first()

    if not n:
        return jsonify({'error': 'Not found'}), 404

    n.is_read = True
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Database error'}), 500

    return jsonify({'success': True})


# ==================== P1: Event Feedback Route ====================

@app.route('/events/<int:event_id>/feedback', methods=['POST'])
def submit_event_feedback(event_id):
    """
    Submit feedback for a completed event.
    Rules:
    - Volunteer must be logged in.
    - Event must exist and be completed/ended.
    - Volunteer must have attended (registration.attended == True, status == 'ATTENDED').
    - Rating must be 1–5.
    - One feedback per volunteer per event (UPSERT behaviour).
    """
    if 'user_id' not in session:
        flash('يرجى تسجيل الدخول أولاً.', 'danger')
        return redirect(url_for('index'))

    ev = Event.query.get_or_404(event_id)

    if not ev.is_completed:
        flash('لا يمكن تقديم التقييم إلا بعد انتهاء الفعالية.', 'danger')
        return redirect(request.referrer or url_for('profile'))

    reg = EventRegistration.query.filter_by(
        volunteer_id=session['user_id'], event_id=event_id
    ).first()

    if not reg or not reg.attended or reg.status == 'WAITLISTED':
        flash('يجب أن تكون قد حضرت الفعالية لتقديم التقييم.', 'danger')
        return redirect(request.referrer or url_for('profile'))

    rating_raw = request.form.get('rating', '').strip()
    try:
        rating = int(rating_raw)
        if not (1 <= rating <= 5):
            raise ValueError
    except ValueError:
        flash('التقييم يجب أن يكون بين 1 و 5.', 'danger')
        return redirect(request.referrer or url_for('profile'))

    comment = request.form.get('comment', '').strip() or None

    # UPSERT behaviour
    fb = EventFeedback.query.filter_by(
        volunteer_id=session['user_id'], event_id=event_id
    ).first()
    if fb:
        fb.rating = rating
        fb.comment = comment
    else:
        fb = EventFeedback(
            volunteer_id=session['user_id'],
            event_id=event_id,
            rating=rating,
            comment=comment,
        )
        db.session.add(fb)

    try:
        db.session.commit()
        flash('تم إرسال تقييمك بنجاح. شكراً لمشاركتك!', 'success')
    except Exception:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')

    return redirect(request.referrer or url_for('profile'))


# ==================== لوحة تحكم الإدارة (Admin Dashboard & CMS) ====================

import json
from collections import Counter

@app.route('/admin')
def admin_dashboard():
    denied = _require_admin()
    if denied:
        return denied

    settings = get_settings()
    admin_email = session.get('admin_email')
    current_admin = Volunteer.query.filter_by(email=admin_email).first()

    # --- Task 6: Search & Filter ---
    search_name = request.args.get('search_name', '').strip()
    filter_city = request.args.get('filter_city', '').strip()
    filter_skill = request.args.get('filter_skill', '').strip()
    filter_gender = request.args.get('filter_gender', '').strip()
    filter_event_id = request.args.get('event_id', '').strip()

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
    if filter_event_id and filter_event_id.isdigit():
        vol_query = vol_query.join(EventRegistration).filter(
            EventRegistration.event_id == int(filter_event_id),
            EventRegistration.attended == True
        )

    volunteers = vol_query.order_by(Volunteer.id.desc()).all()
    inquiries = Inquiry.query.order_by(Inquiry.id.desc()).all()


    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('partials/volunteers.html', volunteers=volunteers, settings=settings)

    from sqlalchemy.orm import joinedload
    events = Event.query.options(joinedload(Event.registrations).joinedload(EventRegistration.volunteer)).order_by(Event.id.desc()).all()
    recent_events = Event.query.order_by(Event.id.desc()).limit(15).all()
    albums = Album.query.order_by(Album.id.desc()).all()
    excuses = Excuse.query.order_by(Excuse.id.desc()).all()

    # --- PHASE 2: Data Aggregation for Chart.js Command Center ---
    all_volunteers = Volunteer.query.all()
    city_counts = dict(Counter(v.city for v in all_volunteers if v.city))
    if not city_counts:
        city_counts = {"عمان": 120, "الزرقاء": 85, "إربد": 60, "البلقاء": 40, "أخرى": 15}


    # Real Chart Data
    import collections

    # 1. Hours Growth Curve (by month of creation)
    hours_dict = collections.defaultdict(int)
    for v in Volunteer.query.all():
        if v.created_at:
            m = v.created_at.strftime('%Y-%m')
            hours_dict[m] += (v.volunteer_hours or 0)
    sorted_months = sorted(hours_dict.keys())[-6:] # last 6 months
    growth_labels = sorted_months
    growth_data = [hours_dict[m] for m in sorted_months]
    if not growth_labels:
        growth_labels = ['لا يوجد بيانات']
        growth_data = [0]

    # 2. Activity Stats (Events by Title Category)
    keywords = ["تنظيمي ولوجستي", "إغاثي وخيري", "بيئي وزراعي", "طبي وصحي", "تطوير وتدريب", "ثقافي واجتماعي", "إعلامي وتقني"]
    # Filter by the first word for partial matching backward compatibility
    activity_data = [Event.query.filter(Event.title.ilike(f'%{kw.split()[0]}%')).count() for kw in keywords]
    total_activities = Event.query.count()

    chart_data = {
        'city_labels': list(city_counts.keys()),
        'city_data': list(city_counts.values()),
        'growth_labels': growth_labels,
        'growth_data': growth_data,
        'activity_labels': keywords,
        'activity_data': activity_data,
        'total_activities': total_activities
    }

    teams = Team.query.order_by(Team.created_at.desc()).all()

    from services.team import EventTeamAssignmentService
    event_locked_map = EventTeamAssignmentService.get_bulk_historical_locks(events)
    training_courses=TrainingCourse.query.order_by(TrainingCourse.created_at.desc()).all()
    return render_template(
        'admin.html',
        training_courses=training_courses,
        event_locked_map=event_locked_map,
        settings=settings,
        current_admin=current_admin,
        volunteers=volunteers,
        events=events,
        recent_events=recent_events,
        albums=albums,
        excuses=excuses,
        inquiries=inquiries,
        teams=teams,
        chart_data=chart_data,
        hours_chart_data=json.dumps({"labels": growth_labels, "data": growth_data}),
        activities_chart_data=json.dumps({"labels": keywords, "data": activity_data}),
        search_name=search_name,
        filter_city=filter_city,
        filter_skill=filter_skill,
        filter_gender=filter_gender
    )


@app.route('/admin/profile/update', methods=['POST'])
def update_admin_profile():
    denied = _require_admin()

    if denied:

        return denied


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
    denied = _require_admin()

    if denied:

        return denied

    reg = EventRegistration.query.get_or_404(reg_id)
    if not reg.attended:
        hours_to_award = mark_attendance_and_grant_hours(reg)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
            return redirect(url_for('admin_dashboard'))
        flash(f'تم تحضير المتطوع {reg.volunteer.name} ومنحه {hours_to_award} ساعات.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/rsvp/remove/<int:reg_id>', methods=['POST'])
def remove_rsvp_volunteer(reg_id):
    denied = _require_admin()

    if denied:

        return denied

    reg = EventRegistration.query.get_or_404(reg_id)
    v_name = reg.volunteer.name

    if not change_registration_status(reg, 'CANCELLED'):
        flash(f'لا يمكن شطب المتطوع {v_name} لأنه حضر الفعالية بالفعل.', 'danger')
        return redirect(url_for('admin_dashboard'))

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    flash(f'تم شطب المتطوع {v_name} من الفعالية وفتح المقعد تلقائياً.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve/<int:volunteer_id>', methods=['POST'])
def approve_volunteer(volunteer_id):
    denied = _require_admin()

    if denied:

        return denied

    v = Volunteer.query.get_or_404(volunteer_id)

    new_location = request.form.get('location')
    if new_location:
        v.city = new_location
        v.team = new_location  # Usually team and city are updated together here based on previous patches


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
    denied = _require_admin()

    if denied:

        return denied

    v = Volunteer.query.get_or_404(volunteer_id)

    new_location = request.form.get('location')
    if new_location:
        v.city = new_location
        v.team = new_location  # Usually team and city are updated together here based on previous patches

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
    denied = _require_admin()

    if denied:

        return denied

    volunteer_id = request.form.get('volunteer_id', type=int)
    position = request.form.get('position')
    photo_url = request.form.get('photo_url')

    v = Volunteer.query.get_or_404(volunteer_id)

    new_location = request.form.get('location')
    if new_location:
        v.city = new_location
        v.team = new_location  # Usually team and city are updated together here based on previous patches


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

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from flask import jsonify
        return jsonify({'success': True})

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_suspend/<int:vol_id>', methods=['POST'])
def toggle_suspend(vol_id):
    denied = _require_admin()

    if denied:

        return denied

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
    denied = _require_admin()

    if denied:

        return denied

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
    denied = _require_admin()

    if denied:

        return denied

    v = Volunteer.query.get_or_404(volunteer_id)

    new_location = request.form.get('location')
    if new_location:
        v.city = new_location
        v.team = new_location  # Usually team and city are updated together here based on previous patches

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
    denied = _require_admin()

    if denied:

        return denied

    v = Volunteer.query.get_or_404(volunteer_id)

    new_location = request.form.get('location')
    if new_location:
        v.city = new_location
        v.team = new_location  # Usually team and city are updated together here based on previous patches

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
    denied = _require_admin()

    if denied:

        return denied

    v = Volunteer.query.get_or_404(volunteer_id)

    new_location = request.form.get('location')
    if new_location:
        v.city = new_location
        v.team = new_location  # Usually team and city are updated together here based on previous patches

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
    denied = _require_admin()

    if denied:

        return denied

    v = Volunteer.query.get_or_404(volunteer_id)

    new_location = request.form.get('location')
    if new_location:
        v.city = new_location
        v.team = new_location  # Usually team and city are updated together here based on previous patches

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
    denied = _require_admin()

    if denied:

        return denied

    v = Volunteer.query.get_or_404(volunteer_id)

    new_location = request.form.get('location')
    if new_location:
        v.city = new_location
        v.team = new_location  # Usually team and city are updated together here based on previous patches

    if action == 'increment':
        if record_hours(v, 1.0, "تعديل إداري: زيادة ساعات"):
            v.auto_assign_badges()
    elif action == 'decrement' and (v.volunteer_hours or 0) >= 1:
        record_hours(v, -1.0, "تعديل إداري: إنقاص ساعات")
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reset_password/<int:volunteer_id>', methods=['POST'])
def reset_volunteer_password(volunteer_id):
    denied = _require_admin()
    if denied:
        return denied
    v = Volunteer.query.get_or_404(volunteer_id)

    new_location = request.form.get('location')
    if new_location:
        v.city = new_location
        v.team = new_location  # Usually team and city are updated together here based on previous patches

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Generate a secure, single-use, time-limited token
    # We include a portion of the current password_hash.
    # When the password is reset, the hash changes, invalidating the token automatically.
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    token = s.dumps({'id': v.id, 'hash': v.password_hash[-10:]})

    reset_link = url_for('handle_reset_password', token=token, _external=True)

    flash(f'تم إنشاء رابط إعادة تعيين كلمة سر {v.name}. الرابط صالح لمدة ساعة ويستخدم لمرة واحدة فقط: {reset_link}', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def handle_reset_password(token):
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        # Token expires in 1 hour (3600 seconds)
        payload = s.loads(token, max_age=3600)
    except SignatureExpired:
        flash('انتهت صلاحية رابط إعادة التعيين.', 'danger')
        return redirect(url_for('index'))
    except BadSignature:
        flash('رابط إعادة التعيين غير صالح.', 'danger')
        return redirect(url_for('index'))

    v = Volunteer.query.get(payload['id'])
    if not v or v.password_hash[-10:] != payload['hash']:
        flash('تم استخدام هذا الرابط مسبقاً أو أنه غير صالح.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not new_password or new_password != confirm_password:
            flash('كلمة المرور غير متطابقة أو فارغة.', 'danger')
            return redirect(url_for('handle_reset_password', token=token))

        if len(new_password) < 6:
            flash('يجب أن تتكون كلمة المرور من 6 أحرف على الأقل.', 'danger')
            return redirect(url_for('handle_reset_password', token=token))

        v.password_hash = generate_password_hash(new_password)
        try:
            db.session.commit()
            flash('تم تعيين كلمة المرور بنجاح. يمكنك الآن تسجيل الدخول.', 'success')
            return redirect(url_for('index'))
        except Exception:
            db.session.rollback()
            flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')

    # A simple, self-contained HTML form using inline styles consistent with the platform
    # avoiding the need for an external template file.
    html = '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>إعادة تعيين كلمة المرور</title>
        <meta name="csrf-token" content="{{ csrf_token() }}">
        <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        <style>
            .reset-container { max-width: 400px; margin: 50px auto; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .reset-container h2 { text-align: center; color: var(--primary-color, #2b3990); margin-bottom: 20px; }
            .reset-container .form-group { margin-bottom: 15px; }
            .reset-container label { display: block; margin-bottom: 5px; font-weight: bold; }
            .reset-container input { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
            .reset-container button { width: 100%; padding: 10px; background-color: var(--primary-color, #2b3990); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
            .reset-container button:hover { opacity: 0.9; }
            .flash-messages { list-style: none; padding: 0; }
            .flash-messages li { padding: 10px; margin-bottom: 15px; border-radius: 4px; }
            .flash-messages .danger { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .flash-messages .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        </style>
    </head>
    <body>
        <div class="reset-container">
            <h2>إعادة تعيين كلمة المرور</h2>

            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}
                <ul class="flash-messages">
                {% for category, message in messages %}
                  <li class="{{ category }}">{{ message }}</li>
                {% endfor %}
                </ul>
              {% endif %}
            {% endwith %}

            <form method="POST">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <div class="form-group">
                    <label for="new_password">كلمة المرور الجديدة</label>
                    <input type="password" id="new_password" name="new_password" required minlength="6">
                </div>
                <div class="form-group">
                    <label for="confirm_password">تأكيد كلمة المرور</label>
                    <input type="password" id="confirm_password" name="confirm_password" required minlength="6">
                </div>
                <button type="submit">حفظ كلمة المرور</button>
            </form>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html)



@app.route('/admin/delete_volunteer/<int:volunteer_id>', methods=['POST'])
def delete_volunteer_admin(volunteer_id):
    denied = _require_admin()

    if denied:

        return denied

    v = Volunteer.query.get_or_404(volunteer_id)

    new_location = request.form.get('location')
    if new_location:
        v.city = new_location
        v.team = new_location  # Usually team and city are updated together here based on previous patches

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
    denied = _require_admin()

    if denied:

        return denied


    # --- Safe explicit casting to prevent type mismatch on commit ---
    raw_capacity = request.form.get('capacity', '').strip()
    raw_hours    = request.form.get('event_hours', '').strip()
    capacity     = int(raw_capacity) if raw_capacity.isdigit() else 10
    event_hours  = int(raw_hours)    if raw_hours.isdigit()    else 3

    # --- Sanitise required string fields (nullable=False columns must not be None) ---
    title       = (request.form.get('title', '')       or '').strip() or 'فعالية بدون عنوان'
    description = (request.form.get('description', '') or '').strip() or '-'
    date        = (request.form.get('date', '')        or '').strip() or '-'
    time        = (request.form.get('time', '')        or '').strip() or '-'
    location    = (request.form.get('location', '')    or '').strip() or '-'

    # --- Optional team assignment (P3-E3) ---
    # Empty or missing → no team (None). Non-digit → reject. Digit → validate existence and active state.
    team_id_raw = request.form.get('team_id', '').strip()
    assigned_team_id = None
    if team_id_raw:
        if not team_id_raw.isdigit():
            flash('معرّف الفريق غير صالح.', 'danger')
            return redirect(url_for('admin_dashboard'))
        tid = int(team_id_raw)
        t = Team.query.get(tid)
        if not t:
            flash('الفريق المختار غير موجود.', 'danger')
            return redirect(url_for('admin_dashboard'))
        if not t.is_active:
            flash('لا يمكن تعيين فعالية لفريق غير نشط.', 'danger')
            return redirect(url_for('admin_dashboard'))
        assigned_team_id = tid

    code = str(random.randint(1000, 9999))
    new_event = Event(
        title=title,
        description=description,
        date=date,
        time=time,
        location=location,
        capacity=capacity,
        event_hours=event_hours,
        secret_code=code,
        team_id=assigned_team_id,
    )
    db.session.add(new_event)
    try:
        db.session.commit()
        flash(f'تمت إضافة الفعالية بنجاح. كود التحضير السري هو: {code}', 'success')
    except Exception as e:
        app.logger.error(f"CRITICAL DB ERROR in add_event: {str(e)}")
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/event/<int:event_id>/export')
def export_event_roster(event_id):
    denied = _require_admin()

    if denied:

        return denied


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
    denied = _require_admin()

    if denied:

        return denied

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
    denied = _require_admin()

    if denied:

        return denied

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
    denied = _require_admin()

    if denied:

        return denied


    # 1. Create the Album
    new_album = Album(
        title=request.form.get('title'),
        category=request.form.get('category', 'عام')
    )

    # Handle Cover Image Upload via storage adapter
    cover_file = request.files.get('cover_image')
    if cover_file and cover_file.filename:
        try:
            new_album.cover_image_url = upload_file(
                cover_file, folder='gallery_covers',
                allowed_extensions=ALLOWED_IMAGE_EXTENSIONS
            )
        except UploadError as e:
            flash(str(e), 'danger')
            return redirect(url_for('admin_dashboard'))
    else:
        new_album.cover_image_url = request.form.get('cover_image_url', '')

    db.session.add(new_album)
    try:
        db.session.commit()  # Commit to get the album ID
    except Exception:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')
        return redirect(url_for('admin_dashboard'))

    # 2. Handle Multi-Media Upload via storage adapter
    uploaded_files = request.files.getlist('album_media')
    failed_files = []
    for file in uploaded_files:
        if file and file.filename:
            try:
                media_url = upload_file(file, folder='gallery_media',
                                        allowed_extensions=ALLOWED_MEDIA_EXTENSIONS)
                ext = file.filename.rsplit('.', 1)[-1].lower()
                media_type = 'video' if ext in {'mp4', 'webm', 'ogg', 'mov'} else 'image'
                new_media = AlbumMedia(
                    album_id=new_album.id,
                    media_url=media_url,
                    media_type=media_type
                )
                db.session.add(new_media)
            except UploadError as e:
                failed_files.append(file.filename)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash('حدث خطأ في قاعدة البيانات أثناء حفظ الوسائط، يرجى المحاولة لاحقاً', 'error')
        return redirect(url_for('admin_dashboard'))

    if failed_files:
        flash(f'تم إنشاء الألبوم لكن فشل رفع {len(failed_files)} ملفات: {", ".join(failed_files)}', 'warning')
    else:
        flash('تمت إضافة الألبوم بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/gallery/delete/<int:item_id>', methods=['POST'])
def delete_gallery_item(item_id):
    denied = _require_admin()

    if denied:

        return denied

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
    if not is_admin_session():

        return jsonify({'error': 'Unauthorized'}), 403

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
    if not is_admin_session():

        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    vol_id = data.get('vol_id')
    stat_type = data.get('type')
    action = data.get('action')
    v = Volunteer.query.get(vol_id)
    if not v: return jsonify({'error': 'Not found'}), 404

    if stat_type == 'hours':
        if action == 'increment':
            record_hours(v, 1.0, "تعديل AJAX: زيادة ساعات")
        elif action == 'decrement' and (v.volunteer_hours or 0) >= 1:
            record_hours(v, -1.0, "تعديل AJAX: إنقاص ساعات")
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
    if not is_admin_session():

        return jsonify({'error': 'Unauthorized'}), 403

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
    if not is_admin_session():

        return jsonify({'error': 'Unauthorized'}), 403

    vol_ids = request.form.getlist('vol_ids')
    hours = int(request.form.get('hours', 0))
    for vid in vol_ids:
        v = Volunteer.query.get(vid)
        if v:
            record_hours(v, float(hours), "إضافة ساعات جماعية")
    try:
        db.session.commit()
        flash('تمت إضافة الساعات للمتطوعين المحددين', 'success')
    except Exception:
        db.session.rollback()
        flash('حدث خطأ', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/bulk_add_events', methods=['POST'])
def bulk_add_events():
    if not is_admin_session():

        return jsonify({'error': 'Unauthorized'}), 403

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
    if not is_admin_session():

        return jsonify({'error': 'Unauthorized'}), 403

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
    denied = _require_admin()

    if denied:

        return denied

    setting = get_settings()

    setting.site_name = request.form.get('site_name')
    setting.brand_title_main = request.form.get('brand_title_main')
    setting.brand_title_sub = request.form.get('brand_title_sub')
    setting.logo_url = request.form.get('logo_url')
    # Hero Settings
    setting.hero_title = request.form.get('hero_title')
    setting.hero_desc = request.form.get('hero_desc')
    setting.hero_cta_text = request.form.get('hero_cta_text')
    setting.hero_cta_link = request.form.get('hero_cta_link')
    setting.profile_motivational_text = request.form.get('profile_motivational_text')
    if 'hero_cta_text' in request.form:
        setting.hero_cta_text = request.form.get('hero_cta_text')
    if 'hero_cta_link' in request.form:
        setting.hero_cta_link = request.form.get('hero_cta_link')

    hero_img_file = request.files.get('hero_image_file')
    if hero_img_file and hero_img_file.filename:
        try:
            setting.hero_image_url = upload_file(hero_img_file, folder='site_settings', allowed_extensions=ALLOWED_IMAGE_EXTENSIONS)
        except UploadError as e:
            flash(str(e), 'danger')
    else:
        hero_url_field = request.form.get('hero_image_url')
        if hero_url_field:
            setting.hero_image_url = hero_url_field

    # Featured Story Settings
    if 'featured_story_title' in request.form:
        setting.featured_story_title = request.form.get('featured_story_title')
    if 'featured_story_desc' in request.form:
        setting.featured_story_desc = request.form.get('featured_story_desc')
    if 'featured_story_cta_text' in request.form:
        setting.featured_story_cta_text = request.form.get('featured_story_cta_text')
    if 'featured_story_cta_link' in request.form:
        setting.featured_story_cta_link = request.form.get('featured_story_cta_link')

    fs_img_file = request.files.get('featured_story_image_file')
    if fs_img_file and fs_img_file.filename:
        try:
            setting.featured_story_image_url = upload_file(fs_img_file, folder='site_settings', allowed_extensions=ALLOWED_IMAGE_EXTENSIONS)
        except UploadError as e:
            flash(str(e), 'danger')
    else:
        fs_url_field = request.form.get('featured_story_image_url')
        if fs_url_field:
            setting.featured_story_image_url = fs_url_field
    setting.vision_text = request.form.get('vision_text')
    setting.mission_text = request.form.get('mission_text')
    setting.contact_email = request.form.get('contact_email')

    setting.impact_section_title = request.form.get('impact_section_title')
    setting.impact_section_desc = request.form.get('impact_section_desc')
    setting.impact_cta_text = request.form.get('impact_cta_text')
    setting.impact_cta_link = request.form.get('impact_cta_link')

    setting.closing_cta_title = request.form.get('closing_cta_title')
    setting.closing_cta_desc = request.form.get('closing_cta_desc')

    setting.stat_label_hours = request.form.get('stat_label_hours')
    setting.stat_label_volunteers = request.form.get('stat_label_volunteers')
    setting.stat_label_events = request.form.get('stat_label_events')

    setting.activities_section_title = request.form.get('activities_section_title')
    setting.activities_section_desc = request.form.get('activities_section_desc')

    setting.gallery_section_title = request.form.get('gallery_section_title')
    setting.gallery_section_desc = request.form.get('gallery_section_desc')

    setting.footer_about_text = request.form.get('footer_about_text')
    setting.contact_phone1 = request.form.get('contact_phone1')
    setting.contact_phone2 = request.form.get('contact_phone2')


    impact_img_file = request.files.get('impact_image_file')
    if impact_img_file and impact_img_file.filename:
        try:
            setting.impact_image_url = upload_file(impact_img_file, folder='site_settings', allowed_extensions=ALLOWED_IMAGE_EXTENSIONS)
        except UploadError as e:
            flash(str(e), 'danger')
    else:
        impact_url_field = request.form.get('impact_image_url')
        if impact_url_field:
            setting.impact_image_url = impact_url_field

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

    # P2-C fields
    if 'profile_motivational_text' in request.form:
        setting.profile_motivational_text = request.form.get('profile_motivational_text')

    uploaded_hero = request.files.get('profile_hero_image')
    if uploaded_hero and uploaded_hero.filename:
        try:
            hero_url = upload_file(uploaded_hero, folder='site_settings', allowed_extensions=ALLOWED_IMAGE_EXTENSIONS)
            setting.profile_hero_image_url = hero_url
        except UploadError as e:
            flash(str(e), 'danger')
            return redirect(url_for('admin_dashboard'))
    else:
        # Fallback to keep existing or new text URL
        hero_url_field = request.form.get('profile_hero_image_url')
        if hero_url_field:
            setting.profile_hero_image_url = hero_url_field

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
        ("events", "event_hours", "INTEGER DEFAULT 3"),
        ("events", "team_id", "INTEGER"),
        ("system_settings", "banner_text", "VARCHAR(500)"),
        ("system_settings", "is_banner_active", "BOOLEAN DEFAULT FALSE"),

        ("site_settings", "featured_story_title", "VARCHAR(250)"),
        ("site_settings", "featured_story_desc", "TEXT"),
        ("site_settings", "featured_story_image_url", "VARCHAR(500)"),
        ("site_settings", "featured_story_cta_text", "VARCHAR(100)"),
        ("site_settings", "featured_story_cta_link", "VARCHAR(500)"),
        ("site_settings", "impact_section_title", "VARCHAR(250)"),
        ("site_settings", "impact_section_desc", "TEXT"),
        ("site_settings", "impact_image_url", "VARCHAR(500)"),
        ("site_settings", "impact_cta_text", "VARCHAR(100)"),
        ("site_settings", "impact_cta_link", "VARCHAR(500)"),
        ("site_settings", "closing_cta_title", "VARCHAR(250)"),
        ("site_settings", "closing_cta_desc", "TEXT"),
        ("site_settings", "stat_label_hours", "VARCHAR(100)"),
        ("site_settings", "stat_label_volunteers", "VARCHAR(100)"),
        ("site_settings", "stat_label_events", "VARCHAR(100)"),
        ("site_settings", "activities_section_title", "VARCHAR(250)"),
        ("site_settings", "activities_section_desc", "TEXT"),
        ("site_settings", "gallery_section_title", "VARCHAR(250)"),
        ("site_settings", "gallery_section_desc", "TEXT"),
        ("site_settings", "footer_about_text", "TEXT"),
        ("site_settings", "contact_phone1", "VARCHAR(50)"),
        ("site_settings", "contact_phone2", "VARCHAR(50)"),


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

        ("site_settings", "profile_hero_image_url", "VARCHAR(500)"),
        ("site_settings", "profile_motivational_text", "TEXT"),
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
        ("volunteers", "last_active", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("volunteers", "admin_evaluation", "TEXT"),
        ("events", "starts_at", "TIMESTAMP"),
        ("events", "ends_at", "TIMESTAMP"),
        ("hour_ledger", "idempotency_key", "VARCHAR(100)"),
        ("events", "status", "VARCHAR(50)"),
        ("event_registrations", "status", "VARCHAR(50)")
    ]
    for tbl, col, col_type in migrations:
        try:
            if "sqlite" in app.config['SQLALCHEMY_DATABASE_URI']:
                # SQLite allows DATETIME, but translates TIMESTAMP properly anyway.
                # SQLite ALTER TABLE does not support IF NOT EXISTS.
                # So it will fail if it exists and be swallowed by except Exception.
                db.session.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_type};"))
            else:
                db.session.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {col} {col_type};"))
            db.session.commit()
        except Exception:
            db.session.rollback()

    # Apply Unique Constraint on EventRegistration
    duplicates = db.session.execute(text("""
        SELECT volunteer_id, event_id, COUNT(*)
        FROM event_registrations
        GROUP BY volunteer_id, event_id
        HAVING COUNT(*) > 1
    """)).fetchall()

    if duplicates:
        app.logger.error(
            f"CRITICAL DATA INTEGRITY ISSUE: Found {len(duplicates)} duplicate registration(s). "
            f"Cannot safely create unique index 'uix_volunteer_event'. "
            f"Please resolve duplicates manually."
        )
    else:
        try:
            db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uix_volunteer_event ON event_registrations (volunteer_id, event_id);"))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Failed to create unique index 'uix_volunteer_event': {e}")

    # Idempotency index for HourLedger
    try:
        db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uix_hour_ledger_idemp ON hour_ledger (idempotency_key) WHERE idempotency_key IS NOT NULL;"))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Fallback for SQLite which doesn't support WHERE in CREATE INDEX in older versions easily or just generic fail
        try:
            db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uix_hour_ledger_idemp ON hour_ledger (idempotency_key);"))
            db.session.commit()
        except Exception:
            db.session.rollback()

    # Idempotency index for Notifications
    try:
        dups = db.session.execute(text("SELECT volunteer_id, reference_id FROM notifications WHERE reference_id IS NOT NULL GROUP BY volunteer_id, reference_id HAVING COUNT(*) > 1")).fetchall()
        if dups:
            app.logger.warning(f"Duplicate notifications found for (volunteer_id, reference_id): {dups}. Will NOT create unique index to prevent data loss. Please resolve manually.")
        else:
            try:
                db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uix_notif_idemp ON notifications (volunteer_id, reference_id) WHERE reference_id IS NOT NULL;"))
                db.session.commit()
            except Exception:
                db.session.rollback()
                # Fallback for SQLite
                try:
                    db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uix_notif_idemp ON notifications (volunteer_id, reference_id);"))
                    db.session.commit()
                except Exception:
                    db.session.rollback()
    except Exception:
        db.session.rollback()


    try:
        if not SiteSetting.query.first():
            db.session.add(SiteSetting())
            db.session.commit()
    except Exception:
        db.session.rollback()

    # ── Bootstrap admin accounts from env vars on first boot ──────────────────
    # These env vars are ONLY used to create the initial DB record.
    # Once the record exists, these env vars are no longer consulted for auth.
    try:
        _bootstrap_admin(
            email=os.environ.get('ADMIN1_EMAIL', ''),
            password=os.environ.get('ADMIN1_PASSWORD', ''),
            name=os.environ.get('ADMIN1_NAME', ''),
            phone=os.environ.get('ADMIN1_PHONE', ''),
            position=os.environ.get('ADMIN1_POSITION', ''),
        )
        _bootstrap_admin(
            email=os.environ.get('ADMIN2_EMAIL', ''),
            password=os.environ.get('ADMIN2_PASSWORD', ''),
            name=os.environ.get('ADMIN2_NAME', ''),
            phone=os.environ.get('ADMIN2_PHONE', ''),
            position=os.environ.get('ADMIN2_POSITION', ''),
        )
    except Exception:
        pass  # Bootstrap failures should not prevent startup


@app.route('/admin/events/<int:event_id>/team', methods=['POST'])
def admin_assign_event_team(event_id):
    denied = _require_admin()
    if denied: return denied

    event = Event.query.get_or_404(event_id)
    target_team_id_raw = request.form.get('team_id', '').strip()

    if target_team_id_raw == '':
        target_team_id = None
    elif target_team_id_raw.isdigit():
        target_team_id = int(target_team_id_raw)
    else:
        flash('Invalid team ID format.', 'danger')
        return redirect(url_for('admin_dashboard'))

    from services.team import EventTeamAssignmentService
    success, msg = EventTeamAssignmentService.assign_team(event, target_team_id)
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/events/<int:event_id>/feedback')
def admin_event_feedback(event_id):
    return "Feedback"


# ==================== TEAMS ADMIN CRUD ====================

@app.route('/admin/teams/create', methods=['POST'])
def admin_create_team():
    denied = _require_admin()
    if denied: return denied

    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()

    if not name:
        flash('Team name is required.', 'danger')
        return redirect(url_for('admin_dashboard'))

    t = Team(name=name[:100], description=description)
    try:
        db.session.add(t)
        db.session.commit()
        flash('Team created successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Failed to create team: {e}")
        flash('Failed to create team.', 'danger')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/teams/<int:team_id>/edit', methods=['POST'])
def admin_edit_team(team_id):
    denied = _require_admin()
    if denied: return denied

    t = Team.query.get_or_404(team_id)
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()

    if not name:
        flash('Team name is required.', 'danger')
        return redirect(url_for('admin_dashboard'))

    t.name = name[:100]
    t.description = description

    try:
        db.session.commit()
        flash('Team updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Failed to edit team: {e}")
        flash('Failed to update team.', 'danger')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/teams/<int:team_id>/toggle', methods=['POST'])
def admin_toggle_team(team_id):
    denied = _require_admin()
    if denied: return denied

    t = Team.query.get_or_404(team_id)
    t.is_active = not t.is_active

    try:
        db.session.commit()
        state_str = 'Activated' if t.is_active else 'Deactivated'
        flash(f'Team {state_str} successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Failed to toggle team: {e}")
        flash('Failed to toggle team.', 'danger')

    return redirect(url_for('admin_dashboard'))

# ==================== GOALS ADMIN CRUD ====================

@app.route('/admin/goals/create', methods=['POST'])
def admin_create_goal():
    denied = _require_admin()
    if denied: return denied

    team_id_raw = request.form.get('team_id', '').strip()
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    target_value_raw = request.form.get('target_value', '').strip()

    if not team_id_raw or not title or not target_value_raw:
        flash('Missing required fields for goal.', 'danger')
        return redirect(url_for('admin_dashboard'))

    try:
        target_value = int(target_value_raw)
        team_id = int(team_id_raw)
    except ValueError:
        flash('Invalid numeric value.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if target_value <= 0:
        flash('Target value must be greater than zero.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # Verify team exists
    team = Team.query.get(team_id)
    if not team:
        flash('Invalid team: team does not exist.', 'danger')
        return redirect(url_for('admin_dashboard'))

    g = Goal(team_id=team_id, title=title[:150], description=description, target_value=target_value)

    try:
        db.session.add(g)
        db.session.commit()
        flash('Goal created successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Failed to create goal: {e}")
        flash('Failed to create goal.', 'danger')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/goals/<int:goal_id>/edit', methods=['POST'])
def admin_edit_goal(goal_id):
    denied = _require_admin()
    if denied: return denied

    g = Goal.query.get_or_404(goal_id)
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    target_value_raw = request.form.get('target_value', '').strip()

    if not title or not target_value_raw:
        flash('Missing required fields for goal.', 'danger')
        return redirect(url_for('admin_dashboard'))

    try:
        target_value = int(target_value_raw)
    except ValueError:
        flash('Invalid numeric value.', 'danger')
        return redirect(url_for('admin_dashboard'))

    g.title = title[:150]
    g.description = description
    g.target_value = target_value

    try:
        db.session.commit()
        flash('Goal updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Failed to update goal: {e}")
        flash('Failed to update goal.', 'danger')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/goals/<int:goal_id>/status', methods=['POST'])
def admin_status_goal(goal_id):
    denied = _require_admin()
    if denied: return denied

    g = Goal.query.get_or_404(goal_id)
    new_status = request.form.get('status', '').strip()

    if new_status not in ['ACTIVE', 'ACHIEVED', 'ARCHIVED']:
        flash('Invalid status.', 'danger')
        return redirect(url_for('admin_dashboard'))

    g.status = new_status

    try:
        db.session.commit()
        flash('Status updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Failed to update status: {e}")
        flash('Failed to update status.', 'danger')

    return redirect(url_for('admin_dashboard'))



# ==================== TRAINING ADMIN CRUD ====================


@app.route('/admin/training/create', methods=['POST'])
def admin_create_course():
    from services.training import TrainingAdminService
    denied = _require_admin()
    if denied: return denied
    
    success, msg = TrainingAdminService.create_course(
        request.form.get('title'),
        request.form.get('description'),
        request.form.get('cover_image_url')
    )
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('admin_dashboard') + '#trainingTab')

@app.route('/admin/training/<int:course_id>/edit', methods=['POST'])
def admin_edit_course(course_id):
    from services.training import TrainingAdminService
    denied = _require_admin()
    if denied: return denied
    
    success, msg = TrainingAdminService.edit_course(
        course_id,
        request.form.get('title'),
        request.form.get('description'),
        request.form.get('cover_image_url')
    )
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('admin_dashboard') + '#trainingTab')

@app.route('/admin/training/<int:course_id>/toggle', methods=['POST'])
def admin_toggle_course(course_id):
    from services.training import TrainingAdminService
    denied = _require_admin()
    if denied: return denied
    
    success, msg = TrainingAdminService.toggle_course_status(course_id)
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('admin_dashboard') + '#trainingTab')

@app.route('/admin/training/<int:course_id>/delete', methods=['POST'])
def admin_delete_course(course_id):
    from services.training import TrainingAdminService
    denied = _require_admin()
    if denied: return denied
    
    success, msg = TrainingAdminService.delete_course(course_id)
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('admin_dashboard') + '#trainingTab')

@app.route('/admin/training/<int:course_id>/modules/create', methods=['POST'])
def admin_create_module(course_id):
    from services.training import TrainingAdminService
    denied = _require_admin()
    if denied: return denied
    
    success, msg = TrainingAdminService.create_module(
        course_id,
        request.form.get('title'),
        request.form.get('description'),
        request.form.get('content_type'),
        request.form.get('content_url'),
        request.form.get('position')
    )
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('admin_dashboard') + '#trainingTab')

@app.route('/admin/training/modules/<int:module_id>/edit', methods=['POST'])
def admin_edit_module(module_id):
    from services.training import TrainingAdminService
    denied = _require_admin()
    if denied: return denied
    
    success, msg = TrainingAdminService.edit_module(
        module_id,
        request.form.get('title'),
        request.form.get('description'),
        request.form.get('content_type'),
        request.form.get('content_url'),
        request.form.get('position')
    )
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('admin_dashboard') + '#trainingTab')

@app.route('/admin/training/modules/<int:module_id>/delete', methods=['POST'])
def admin_delete_module(module_id):
    from services.training import TrainingAdminService
    denied = _require_admin()
    if denied: return denied
    
    success, msg = TrainingAdminService.delete_module(module_id)
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('admin_dashboard') + '#trainingTab')


# ==================== LEGAL PAGES ====================
@app.route('/privacy')
def privacy():
    return render_template('privacy.html', settings=get_settings())

@app.route('/terms')
def terms():
    return render_template('terms.html', settings=get_settings())

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', settings=get_settings()), 404


from flask_wtf.csrf import CSRFError

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html', settings=get_settings()), 500

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return render_template('csrf_error.html', settings=get_settings(), reason=e.description), 400


@app.route('/sitemap.xml')
def sitemap():
    pages = []
    from flask import make_response
    for rule in app.url_map.iter_rules():
        if rule.endpoint in ['index', 'events_list', 'privacy', 'terms', 'resources']:
            url = url_for(rule.endpoint, _external=True)
            pages.append(f"  <url><loc>{url}</loc></url>")
            
    # events
    events = Event.query.filter(db.or_(Event.status != 'CANCELLED', Event.status.is_(None))).all()
    for ev in events:
        url = url_for('event_detail', event_id=ev.id, _external=True)
        pages.append(f"  <url><loc>{url}</loc></url>")

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(pages) + '\n</urlset>'
    
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route('/robots.txt')
def robots():
    from flask import make_response
    sitemap_url = url_for('sitemap', _external=True)
    text = f"User-agent: *\nDisallow: /admin\nDisallow: /profile\nDisallow: /verify_attendance_code\nSitemap: {sitemap_url}\n"
    response = make_response(text)
    response.headers["Content-Type"] = "text/plain"
    return response


# ==================== VOLUNTEER TRAINING ====================

@app.route('/training')
def training_list():
    if 'user_id' not in session:
        flash('يُرجى تسجيل الدخول أولاً.', 'danger')
        return redirect(url_for('login'))
        
    settings = get_settings()
    courses = TrainingCourse.query.options(db.joinedload(TrainingCourse.modules.and_(TrainingModule.is_published == True))).filter_by(is_published=True).order_by(TrainingCourse.created_at.desc()).all()
    
    return render_template('training_list.html', courses=courses, settings=settings)

@app.route('/training/<int:course_id>/module/<int:module_id>')
def training_module_detail(course_id, module_id):
    if 'user_id' not in session:
        flash('يُرجى تسجيل الدخول أولاً.', 'danger')
        return redirect(url_for('login'))
        
    settings = get_settings()
    course = TrainingCourse.query.filter_by(id=course_id, is_published=True).first_or_404()
    module = TrainingModule.query.filter_by(id=module_id, course_id=course.id, is_published=True).first_or_404()
    
    progress = TrainingProgress.query.filter_by(volunteer_id=session['user_id'], module_id=module.id).first()
    is_completed = progress.is_completed if progress else False
    
    return render_template('training_module.html', course=course, module=module, is_completed=is_completed, settings=settings)

@app.route('/training/<int:course_id>/module/<int:module_id>/complete', methods=['POST'])
def training_module_complete(course_id, module_id):
    if 'user_id' not in session:
        flash('يُرجى تسجيل الدخول أولاً.', 'danger')
        return redirect(url_for('login'))
        
    course = TrainingCourse.query.filter_by(id=course_id, is_published=True).first_or_404()
    module = TrainingModule.query.filter_by(id=module_id, course_id=course.id, is_published=True).first_or_404()
    
    from services.training import TrainingVolunteerService
    success, msg = TrainingVolunteerService.mark_module_completed(session['user_id'], module.id)
    
    if success:
        flash('تم إكمال الوحدة بنجاح!', 'success')
    else:
        flash(msg, 'danger')
        
    return redirect(url_for('training_module_detail', course_id=course.id, module_id=module.id))

@app.route('/training/<int:course_id>')
def training_detail(course_id):
    if 'user_id' not in session:
        flash('يُرجى تسجيل الدخول أولاً.', 'danger')
        return redirect(url_for('login'))
        
    settings = get_settings()
    course = TrainingCourse.query.filter_by(id=course_id, is_published=True).first_or_404()
    modules = TrainingModule.query.filter_by(course_id=course_id, is_published=True).order_by(TrainingModule.position.asc(), TrainingModule.id.asc()).all()
    
    module_ids = [m.id for m in modules]
    progress_records = TrainingProgress.query.filter_by(volunteer_id=session['user_id']).filter(TrainingProgress.module_id.in_(module_ids)).all() if module_ids else []
    completed_module_ids = {p.module_id for p in progress_records if p.is_completed}
    
    from services.training import TrainingVolunteerService
    course_progress = TrainingVolunteerService.get_course_progress(session['user_id'], course_id)
    
    return render_template('training_detail.html', course=course, modules=modules, completed_module_ids=completed_module_ids, settings=settings, course_progress=course_progress)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))  # [DEV] Shifted from 5000 (HSTS-poisoned) to 5001
    # debug mode is only enabled in development; never in production
    app.run(host='0.0.0.0', port=port, debug=_is_dev)
