with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def admin_dashboard():')
end_idx = text.find('X-Requested-With', idx)
if end_idx != -1:
    with open('ajax_check.txt', 'w', encoding='utf-8') as out:
        out.write(text[idx:end_idx+60])
else:
    with open('ajax_check.txt', 'w', encoding='utf-8') as out:
        out.write("Not found")
