with open('templates/admin.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find("url_for('assign_leader'")
with open('form2.txt', 'w', encoding='utf-8') as out:
    out.write(text[idx:idx+1500])
