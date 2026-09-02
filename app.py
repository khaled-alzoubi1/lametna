from flask import Flask, render_template, request, jsonify, Response, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timedelta
import os
import io
import csv

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'lametna-production-secure-key-2026-xyz')
database_url = os.environ.get('DATABASE_URL', 'sqlite:///lametna.db')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'mov'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)

SKILLS_MAP = {
    'photography': 'تصوير فوتوغرافي', 'editing': 'مونتاج وصناعة محتوى',
    'design': 'تصميم جرافيك', 'social_media': 'إدارة سوشيال ميديا',
    'organization': 'تنظيم فعاليات', 'speaking': 'إلقاء وتقديم',
    'instrument': 'عزف وموسيقى', 'experience': 'خبرة تطوعية سابقة',
    'تصوير': 'تصوير فوتوغرافي', 'مونتاج': 'مونتاج وصناعة محتوى',
    'تصميم': 'تصميم جرافيك', 'سوشيال_ميديا': 'إدارة سوشيال ميديا',
    'تنظيم': 'تنظيم فعاليات', 'إلقاء': 'إلقاء وتقديم',
    'موسيقى': 'عزف وموسيقى', 'خبرة_سابقة': 'خبرة تطوعية سابقة'
}

BEHAVIOR_MAP = {
    'pressure': {1: 'يحافظ على الهدوء ويعيد ترتيب الأولويات', 2: 'يتعامل بشكل طبيعي ويطلب مساعدة', 3: 'يفقد تركيزه تحت الضغط'},
    'punctuality': {1: 'يحضر قبل الموعد', 2: 'يحضر على الوقت تماماً', 3: 'يتأخر أحياناً'},
    'conflict': {1: 'يفصل المشاعر ويركز على الحلول', 2: 'يلتزم الصمت ويتجنب النقاش', 3: 'يدافع بحدة ويتأثر عاطفياً'},
    'workstyle': {1: 'العمل الجماعي والتعاون', 2: 'المهام الفردية المحددة', 3: 'القيادة وتوجيه الآخرين'}
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'يرجى تسجيل الدخول أولاً.'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('role') != 'admin':
            return jsonify({'success': False, 'message': 'غير مصرح لك بالوصول لهذه الصفحة.'}), 403
        return f(*args, **kwargs)
    return decorated_function

# النماذج
class SiteInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    about_text = db.Column(db.Text, default='مبادرة لمتنا بصمة التطوعية: فريق شبابي يهدف إلى صناعة الأثر الإيجابي في المجتمع من خلال تنظيم الفعاليات الخيرية والتنموية والأنشطة الميدانية المستمرة.')
    announcement = db.Column(db.Text, default='')

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    caption = db.Column(db.Text, nullable=True)
    media_type = db.Column(db.String(20), default='text')
    media_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Volunteer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    avatar_url = db.Column(db.String(500), default='')
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    
    q_pressure = db.Column(db.Integer, nullable=False)
    q_punctuality = db.Column(db.Integer, nullable=False)
    q_conflict = db.Column(db.Integer, nullable=False)
    q_workstyle = db.Column(db.Integer, nullable=False)
    
    skills = db.Column(db.Text, nullable=True)
    experience_details = db.Column(db.Text, nullable=True)
    admin_notes = db.Column(db.Text, default='')
    
    rank = db.Column(db.String(50), default='مستجد')
    is_leader = db.Column(db.Boolean, default=False)
    leadership_role = db.Column(db.String(100), default='')
    events_count = db.Column(db.Integer, default=0)
    warnings_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(30), default='قيد المراجعة')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    event_date = db.Column(db.String(50), nullable=False)
    attendees = db.Column(db.Text, default='')
    registered_volunteers = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'success': False, 'message': 'الصفحة المطلوبة غير موجودة'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'success': False, 'message': 'حدث خطأ في الخادم الداخلي'}), 500

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'لم يتم إرسال أي ملف'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'لم يتم اختيار أي ملف'}), 400
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(file_path)
        media_type = 'video' if ext in {'mp4', 'mov'} else 'image'
        return jsonify({
            'success': True,
            'file_url': f"/static/uploads/{unique_name}",
            'media_type': media_type
        })
    return jsonify({'success': False, 'message': 'نوع الملف غير مدعوم'}), 400

@app.route('/api/check_session', methods=['GET'])
def check_session():
    user = session.get('user')
    if not user:
        return jsonify({'logged_in': False})

    if user.get('role') == 'admin':
        return jsonify({
            'logged_in': True,
            'role': 'admin',
            'name': user.get('name'),
            'title': user.get('title')
        })

    volunteer = Volunteer.query.get(user.get('id'))
    if not volunteer:
        session.clear()
        return jsonify({'logged_in': False})

    return jsonify({
        'logged_in': True,
        'role': 'volunteer',
        'volunteer': {
            'id': volunteer.id,
            'name': volunteer.full_name,
            'phone': volunteer.phone,
            'location': volunteer.location,
            'avatar_url': volunteer.avatar_url or '',
            'rank': volunteer.rank,
            'is_leader': volunteer.is_leader,
            'leadership_role': volunteer.leadership_role,
            'events_count': volunteer.events_count,
            'warnings_count': volunteer.warnings_count,
            'status': volunteer.status
        }
    })

@app.route('/api/site_info', methods=['GET', 'POST'])
def site_info():
    info = SiteInfo.query.first()
    if not info:
        info = SiteInfo()
        db.session.add(info)
        db.session.commit()

    if request.method == 'POST':
        if not session.get('user') or session.get('user', {}).get('role') != 'admin':
            return jsonify({'success': False, 'message': 'غير مصرح'}), 403
        data = request.get_json()
        info.about_text = data.get('about_text', info.about_text)
        info.announcement = data.get('announcement', info.announcement)
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم تحديث معلومات الموقع بنجاح!'})

    return jsonify({
        'success': True,
        'about_text': info.about_text,
        'announcement': info.announcement
    })

@app.route('/api/posts', methods=['GET', 'POST'])
def handle_posts():
    if request.method == 'POST':
        if not session.get('user') or session.get('user', {}).get('role') != 'admin':
            return jsonify({'success': False, 'message': 'غير مصرح'}), 403
        data = request.get_json()
        new_post = Post(
            title=data.get('title', ''),
            caption=data.get('caption', ''),
            media_type=data.get('media_type', 'text'),
            media_url=data.get('media_url', '')
        )
        db.session.add(new_post)
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم نشر المحتوى بنجاح!'})

    posts = Post.query.order_by(Post.id.desc()).all()
    posts_list = [{
        'id': p.id,
        'title': p.title,
        'caption': p.caption,
        'media_type': p.media_type,
        'media_url': p.media_url,
        'created_at': p.created_at.strftime('%Y-%m-%d %H:%M')
    } for p in posts]
    return jsonify({'success': True, 'posts': posts_list})

@app.route('/api/post/<int:p_id>/delete', methods=['POST'])
@admin_required
def delete_post(p_id):
    post = Post.query.get_or_404(p_id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({'success': True, 'message': 'تم حذف المنشور بنجاح'})

@app.route('/api/register', methods=['POST'])
def register_volunteer():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'بيانات غير صالحة'}), 400

    email = data.get('email', '').strip().lower()
    if Volunteer.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'البريد الإلكتروني مسجل مسبقاً.'}), 400

    raw_password = data.get('password', '').strip()
    hashed_pwd = generate_password_hash(raw_password) if raw_password else None

    new_volunteer = Volunteer(
        full_name=data.get('full_name'),
        phone=data.get('phone'),
        email=email if email else None,
        password_hash=hashed_pwd,
        age=int(data.get('age')),
        gender=data.get('gender'),
        location=data.get('location'),
        q_pressure=int(data.get('q_pressure')),
        q_punctuality=int(data.get('q_punctuality')),
        q_conflict=int(data.get('q_conflict')),
        q_workstyle=int(data.get('q_workstyle')),
        skills=','.join(data.get('skills', [])),
        experience_details=data.get('experience_details', '')
    )

    db.session.add(new_volunteer)
    db.session.commit()
    return jsonify({'success': True, 'message': 'تم إرسال طلب الانضمام بنجاح!'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    session.permanent = True

    if email == 'lanooshabdo7@gmail.com' and password == 'Lanooshabdo7':
        session['user'] = {'role': 'admin', 'name': 'لين عبده', 'title': 'أهلاً وسهلاً برئيسة المبادرة'}
        return jsonify({'success': True, 'role': 'admin', 'title': 'أهلاً وسهلاً برئيسة المبادرة', 'name': 'لين عبده'})

    if email == 'khaledsalzoubi1352006@gmail.com' and password == 'kh13s5alzoubi2006':
        session['user'] = {'role': 'admin', 'name': 'خالد الزعبي', 'title': 'أهلاً وسهلاً بنائب رئيس المبادرة'}
        return jsonify({'success': True, 'role': 'admin', 'title': 'أهلاً وسهلاً بنائب رئيس المبادرة', 'name': 'خالد الزعبي'})

    volunteer = Volunteer.query.filter_by(email=email).first()
    if volunteer and volunteer.password_hash and check_password_hash(volunteer.password_hash, password):
        session['user'] = {'role': 'volunteer', 'id': volunteer.id}
        return jsonify({
            'success': True,
            'role': 'volunteer',
            'volunteer': {
                'id': volunteer.id,
                'name': volunteer.full_name,
                'phone': volunteer.phone,
                'location': volunteer.location,
                'avatar_url': volunteer.avatar_url or '',
                'rank': volunteer.rank,
                'is_leader': volunteer.is_leader,
                'leadership_role': volunteer.leadership_role,
                'events_count': volunteer.events_count,
                'warnings_count': volunteer.warnings_count,
                'status': volunteer.status
            }
        })

    return jsonify({'success': False, 'message': 'بيانات الدخول غير صحيحة.'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/volunteer/update_profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    user = session.get('user')
    v_id = user.get('id') if user.get('role') == 'volunteer' else data.get('id')

    volunteer = Volunteer.query.get_or_404(v_id)
    volunteer.phone = data.get('phone', volunteer.phone)
    volunteer.location = data.get('location', volunteer.location)
    if 'avatar_url' in data:
        volunteer.avatar_url = data.get('avatar_url')
    db.session.commit()
    return jsonify({'success': True, 'message': 'تم تحديث البيانات الشخصية بنجاح!'})

@app.route('/api/volunteers', methods=['GET'])
@admin_required
def get_volunteers():
    skill_filter = request.args.get('skill', '')
    search_query = request.args.get('search', '').strip()
    
    query = Volunteer.query
    if skill_filter:
        query = query.filter(Volunteer.skills.contains(skill_filter))
    if search_query:
        query = query.filter(
            (Volunteer.full_name.contains(search_query)) | 
            (Volunteer.phone.contains(search_query)) |
            (Volunteer.location.contains(search_query)) |
            (Volunteer.email.contains(search_query))
        )
        
    volunteers = query.all()
    results = []
    for v in volunteers:
        raw_skills = v.skills.split(',') if v.skills else []
        arabic_skills = [SKILLS_MAP.get(s.strip(), s.strip()) for s in raw_skills if s.strip()]

        results.append({
            'id': v.id,
            'full_name': v.full_name,
            'phone': v.phone,
            'email': v.email or 'غير مسجل',
            'avatar_url': v.avatar_url or '',
            'age': v.age,
            'gender': v.gender,
            'location': v.location,
            'skills': arabic_skills,
            'experience_details': v.experience_details,
            'admin_notes': v.admin_notes or '',
            'is_leader': v.is_leader,
            'leadership_role': v.leadership_role or '',
            'behavior': {
                'pressure': BEHAVIOR_MAP['pressure'].get(v.q_pressure, ''),
                'punctuality': BEHAVIOR_MAP['punctuality'].get(v.q_punctuality, ''),
                'conflict': BEHAVIOR_MAP['conflict'].get(v.q_conflict, ''),
                'workstyle': BEHAVIOR_MAP['workstyle'].get(v.q_workstyle, '')
            },
            'rank': v.rank,
            'events_count': v.events_count,
            'warnings_count': v.warnings_count,
            'status': v.status
        })

    return jsonify({'success': True, 'volunteers': results})

@app.route('/api/stats', methods=['GET'])
@admin_required
def get_stats():
    return jsonify({
        'success': True,
        'stats': {
            'total': Volunteer.query.count(),
            'accepted': Volunteer.query.filter_by(status='مقبول').count(),
            'pending': Volunteer.query.filter_by(status='قيد المراجعة').count(),
            'events': Event.query.count()
        }
    })

@app.route('/api/volunteer/<int:v_id>/update', methods=['POST'])
@admin_required
def update_volunteer(v_id):
    volunteer = Volunteer.query.get_or_404(v_id)
    data = request.get_json()
    action = data.get('action')

    if action == 'accept':
        volunteer.status = 'مقبول'
    elif action == 'reject':
        volunteer.status = 'مرفوض'
    elif action == 'add_event':
        volunteer.events_count += 1
        if volunteer.events_count >= 10: volunteer.rank = 'قائد ميداني'
        elif volunteer.events_count >= 5: volunteer.rank = 'عضو فعال'
        elif volunteer.events_count >= 1: volunteer.rank = 'متطوع رسمي'
    elif action == 'add_warning':
        volunteer.warnings_count += 1
    elif action == 'save_notes':
        volunteer.admin_notes = data.get('notes', '')
    elif action == 'set_leadership':
        volunteer.is_leader = data.get('is_leader', True)
        volunteer.leadership_role = data.get('role_title', 'قائد فريق')
        if volunteer.is_leader and volunteer.rank == 'مستجد':
            volunteer.rank = 'قائد ميداني'
    elif action == 'reset_password':
        new_pass = data.get('new_password', '').strip()
        if not new_pass or len(new_pass) < 4:
            return jsonify({'success': False, 'message': 'كلمة المرور يجب أن تكون 4 خانات على الأقل'}), 400
        volunteer.password_hash = generate_password_hash(new_pass)
        db.session.commit()
        return jsonify({'success': True, 'message': f'تم تعيين كلمة مرور جديدة للمتطوع ({volunteer.full_name}) بنجاح!'})
    elif action == 'delete':
        db.session.delete(volunteer)
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم الحذف بنجاح'})

    db.session.commit()
    return jsonify({'success': True, 'message': 'تم التحديث بنجاح'})

@app.route('/api/events', methods=['GET', 'POST'])
def handle_events():
    if request.method == 'POST':
        if not session.get('user') or session.get('user', {}).get('role') != 'admin':
            return jsonify({'success': False, 'message': 'غير مصرح'}), 403
        data = request.get_json()
        new_event = Event(
            title=data.get('title'),
            location=data.get('location'),
            event_date=data.get('event_date')
        )
        db.session.add(new_event)
        db.session.commit()
        return jsonify({'success': True, 'message': 'تمت إضافة الفعالية بنجاح!'})
    
    events = Event.query.order_by(Event.id.desc()).all()
    events_list = []
    for e in events:
        attendee_ids = [int(i) for i in e.attendees.split(',') if i.isdigit()]
        reg_ids = [int(i) for i in e.registered_volunteers.split(',') if i.isdigit()]
        
        attendees_data = []
        if attendee_ids:
            v_list = Volunteer.query.filter(Volunteer.id.in_(attendee_ids)).all()
            attendees_data = [{'id': v.id, 'name': v.full_name} for v in v_list]

        registered_data = []
        if reg_ids:
            r_list = Volunteer.query.filter(Volunteer.id.in_(reg_ids)).all()
            registered_data = [{'id': v.id, 'name': v.full_name} for v in r_list]

        events_list.append({
            'id': e.id,
            'title': e.title,
            'location': e.location,
            'event_date': e.event_date,
            'attendees': attendees_data,
            'attendees_count': len(attendees_data),
            'registered_volunteers': registered_data,
            'registered_count': len(registered_data)
        })
    return jsonify({'success': True, 'events': events_list})

@app.route('/api/event/<int:e_id>/register_interest', methods=['POST'])
@login_required
def register_event_interest(e_id):
    event = Event.query.get_or_404(e_id)
    user = session.get('user')
    v_id = str(user.get('id'))

    regs = [i for i in event.registered_volunteers.split(',') if i] if event.registered_volunteers else []
    if v_id in regs:
        return jsonify({'success': False, 'message': 'أنت مسجل بالفعل في هذه الفعالية.'})

    regs.append(v_id)
    event.registered_volunteers = ','.join(regs)
    db.session.commit()
    return jsonify({'success': True, 'message': 'تم تسجيل رغبتك بالانضمام للفعالية بنجاح!'})

@app.route('/api/event/<int:e_id>/delete', methods=['POST'])
@admin_required
def delete_event(e_id):
    event = Event.query.get_or_404(e_id)
    db.session.delete(event)
    db.session.commit()
    return jsonify({'success': True, 'message': 'تم حذف الفعالية بنجاح'})

@app.route('/api/event/<int:e_id>/attend', methods=['POST'])
@admin_required
def record_attendance(e_id):
    event = Event.query.get_or_404(e_id)
    data = request.get_json()
    v_id = str(data.get('volunteer_id')).strip()

    volunteer = Volunteer.query.get(int(v_id)) if v_id.isdigit() else None
    if not volunteer:
        return jsonify({'success': False, 'message': 'رقم المتطوع غير موجود.'}), 404

    attendees = [i for i in event.attendees.split(',') if i] if event.attendees else []
    if v_id in attendees:
        return jsonify({'success': False, 'message': 'تم توثيق الحضور لهذا المتطوع مسبقاً.'})

    attendees.append(v_id)
    event.attendees = ','.join(attendees)
    volunteer.events_count += 1
    if volunteer.events_count >= 10: volunteer.rank = 'قائد ميداني'
    elif volunteer.events_count >= 5: volunteer.rank = 'عضو فعال'
    elif volunteer.events_count >= 1: volunteer.rank = 'متطوع رسمي'

    db.session.commit()
    return jsonify({'success': True, 'message': f'تم تسجيل حضور ({volunteer.full_name}) وترقيته!'})

@app.route('/api/event/<int:e_id>/remove_attendee', methods=['POST'])
@admin_required
def remove_attendance(e_id):
    event = Event.query.get_or_404(e_id)
    data = request.get_json()
    v_id = str(data.get('volunteer_id')).strip()

    attendees = [i for i in event.attendees.split(',') if i] if event.attendees else []
    if v_id in attendees:
        attendees.remove(v_id)
        event.attendees = ','.join(attendees)
        volunteer = Volunteer.query.get(int(v_id))
        if volunteer and volunteer.events_count > 0:
            volunteer.events_count -= 1
            if volunteer.events_count < 1: volunteer.rank = 'مستجد'
            elif volunteer.events_count < 5: volunteer.rank = 'متطوع رسمي'
            elif volunteer.events_count < 10: volunteer.rank = 'عضو فعال'
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم إلغاء توثيق الحضور وتعديل الرتبة!'})

    return jsonify({'success': False, 'message': 'المتطوع غير مسجل في هذه الفعالية.'})

@app.route('/api/export/volunteers', methods=['GET'])
@admin_required
def export_volunteers():
    volunteers = Volunteer.query.all()
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow(['الرقم', 'الاسم الكامل', 'رقم الهاتف', 'البريد الإلكتروني', 'العمر', 'الجنس', 'مكان السكن', 'المهارات', 'الخبرات السابقة', 'ملاحظات الإدارة', 'الرتبة القيادية', 'الرتبة', 'الفعاليات', 'الإنذارات', 'الحالة'])
    
    for v in volunteers:
        raw_skills = v.skills.split(',') if v.skills else []
        arabic_skills = [SKILLS_MAP.get(s.strip(), s.strip()) for s in raw_skills if s.strip()]
        leader_title = v.leadership_role if v.is_leader else 'متطوع'
        writer.writerow([v.id, v.full_name, v.phone, v.email or '', v.age, v.gender, v.location, ' - '.join(arabic_skills), v.experience_details or '', v.admin_notes or '', leader_title, v.rank, v.events_count, v.warnings_count, v.status])
    
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment;filename=volunteers_lametna.csv"})

@app.route('/api/export/event/<int:e_id>', methods=['GET'])
@admin_required
def export_event_attendees(e_id):
    event = Event.query.get_or_404(e_id)
    attendee_ids = [int(i) for i in event.attendees.split(',') if i.isdigit()] if event.attendees else []
    volunteers = Volunteer.query.filter(Volunteer.id.in_(attendee_ids)).all() if attendee_ids else []

    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow([f'كشف حضور فعالية: {event.title}', f'التاريخ: {event.event_date}', f'الموقع: {event.location}'])
    writer.writerow([])
    writer.writerow(['رقم المتطوع', 'الاسم الكامل', 'رقم الهاتف', 'البريد الإلكتروني', 'الرتبة'])

    for v in volunteers:
        writer.writerow([v.id, v.full_name, v.phone, v.email or '', v.rank])

    output.seek(0)
    filename = f"attendance_event_{event.id}.csv"
    return Response(output.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": f"attachment;filename={filename}"})

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
