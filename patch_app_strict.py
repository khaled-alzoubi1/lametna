import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Locate def register() block
# Replace the top portion:
old_block = """    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()"""

new_block = """    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        gender = request.form.get('gender', '').strip()
        
        import re as regex
        if not regex.match(r'^[\\u0600-\\u06FF\\s]+$', name):
            db.session.rollback()
            flash('يرجى إدخال الاسم باللغة العربية فقط', 'danger')
            return redirect(url_for('index'))
            
        if gender not in ['ذكر', 'أنثى']:
            db.session.rollback()
            flash('يرجى تحديد الجنس بشكل صحيح', 'danger')
            return redirect(url_for('index'))

        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()"""

if "regex.match" not in content:
    content = content.replace(old_block, new_block)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("app.py patched for strict backend validation.")
