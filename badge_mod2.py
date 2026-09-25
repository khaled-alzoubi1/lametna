with open(r'templates\partials\volunteers.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '<option value=\"وسام درع الطوارئ\">وسام درع الطوارئ</option>'
replacement = '<option value=\"وسام درع الطوارئ\">وسام درع الطوارئ</option>\n                                    <option value=\"وسام مدرب خيري معتمد\">وسام مدرب خيري معتمد</option>'
text = text.replace(target, replacement)
with open(r'templates\partials\volunteers.html', 'w', encoding='utf-8') as f:
    f.write(text)
