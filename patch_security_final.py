import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Imports
imports = """
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from sqlalchemy.exc import IntegrityError
"""
if "from flask_limiter import Limiter" not in content:
    content = content.replace("from flask_sqlalchemy import SQLAlchemy", "from flask_sqlalchemy import SQLAlchemy" + imports)

# 2. Init Limiter & Talisman
init_code = """
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]
)

csp = {
    'default-src': [
        '\\'self\\'',
        '\\'unsafe-inline\\'',
        '\\'unsafe-eval\\'',
        'https://cdn.jsdelivr.net',
        'https://cdnjs.cloudflare.com',
        'https://fonts.googleapis.com',
        'https://fonts.gstatic.com',
        'https://ka-f.fontawesome.com'
    ],
    'img-src': ['*', 'data:'],
    'font-src': ['*', 'data:']
}
Talisman(app, content_security_policy=csp)
"""
if "limiter = Limiter" not in content:
    # Insert after app = Flask(__name__)
    content = content.replace("app = Flask(__name__)", "app = Flask(__name__)\n" + init_code)

# 3. Unique Constraint on phone
content = re.sub(
    r"phone = db\.Column\(db\.String\(20\), nullable=False\)",
    "phone = db.Column(db.String(20), unique=True, nullable=False)",
    content
)

# 4. Update /register to catch IntegrityError
# The current try/except is:
# try:
#     db.session.commit()
# except Exception as e:
#     db.session.rollback()
#     flash('...', 'error')
# 
# We'll replace it with:
register_try_catch = """
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('رقم الهاتف أو البريد الإلكتروني مسجل مسبقاً', 'danger')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ أثناء التسجيل، يرجى المحاولة لاحقاً', 'danger')
            return redirect(url_for('index'))
"""
# Need to find the commit block in /register precisely.
# I will use a simple regex replacing the commit block in register.
register_pattern = r"(new_volunteer = Volunteer\(.*?\n\s+db\.session\.add\(new_volunteer\))\n\s+try:\n\s+db\.session\.commit\(\)\n\s+except Exception as e:\n\s+db\.session\.rollback\(\)\n\s+flash\([^)]+\)"
if "except IntegrityError:" not in content:
    # Let's do a targeted string replacement for the register route's exception block
    # We find where `def register():` starts, then the first `try: db.session.commit()`
    reg_idx = content.find("def register():")
    if reg_idx != -1:
        commit_idx = content.find("try:", reg_idx)
        end_commit_idx = content.find("flash('تم تسجيلك بنجاح", commit_idx)
        if end_commit_idx == -1: # fallback
            end_commit_idx = content.find("return redirect(url_for('index'))", commit_idx) + 35
            
        old_commit_block = content[commit_idx:end_commit_idx]
        new_commit_block = """try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('رقم الهاتف أو البريد الإلكتروني مسجل مسبقاً', 'danger')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ أثناء التسجيل، يرجى المحاولة لاحقاً', 'danger')
            return redirect(url_for('index'))
        
        """
        content = content[:commit_idx] + new_commit_block + content[end_commit_idx:]


# 5. Admin Brute-Force Protection
# Decorate /login with @limiter.limit("5 per hour", exempt_when=lambda: request.method != 'POST')
login_decorator = """@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per hour", exempt_when=lambda: request.method != 'POST')"""
content = content.replace("@app.route('/login', methods=['GET', 'POST'])", login_decorator)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("app.py successfully secured.")
