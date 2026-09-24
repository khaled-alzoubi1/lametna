with open('templates/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("\\'", "'")

with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(content)
