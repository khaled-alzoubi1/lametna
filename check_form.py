with open('templates/admin.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('searchForm')
with open('form.txt', 'w', encoding='utf-8') as out:
    out.write(text[idx-200:idx+200])
