import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace config block
# From app = Flask(__name__) down to SQLALCHEMY_TRACK_MODIFICATIONS
pattern = r'(app = Flask\(__name__\)).*?(app\.config\[\'SQLALCHEMY_TRACK_MODIFICATIONS\'\])'
replacement = r"""\1

import os
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
\2"""

if "os.environ.get('DATABASE_URL', 'sqlite:///local.db')" not in content:
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Secured environment variables in app.py")
