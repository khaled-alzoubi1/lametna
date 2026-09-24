import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I will precisely replace the end of def register() with the correct block
proper_end = """
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
"""

# Let's find db.session.add(new_volunteer) inside register()
idx1 = content.find("db.session.add(new_volunteer)")
if idx1 != -1:
    idx2 = content.find("@app.route('/login", idx1)
    if idx2 != -1:
        # replace everything between add() and @app.route('/login')
        content = content[:idx1] + "db.session.add(new_volunteer)\n" + proper_end + "\n" + content[idx2:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("register route fixed.")
