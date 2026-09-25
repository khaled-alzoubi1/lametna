import re
with open('templates/admin.html', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('<option value=\"هيئة إدارية\">هيئة إدارية</option>', '<option value=\"هيئة إدارية\">هيئة إدارية</option>\n                            <option value=\"مدرب معتمد\">مدرب معتمد</option>')
with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(text)
