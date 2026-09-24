with open('templates/admin.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find("url_for('assign_leader'")
with open('form3.txt', 'w', encoding='utf-8') as out:
    out.write(text[idx:idx+2500])
