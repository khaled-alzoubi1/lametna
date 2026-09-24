with open('templates/partials/volunteers.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find("{% for v in volunteers if v.status != 'pending' %}")
if idx != -1:
    with open('sep.txt', 'w', encoding='utf-8') as out:
        out.write(text[max(0, idx-300):idx+100])
