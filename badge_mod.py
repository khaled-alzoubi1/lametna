with open(r'templates\partials\volunteers.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''<option value="وسام الانضباط الذهبي">وسام الانضباط الذهبي</option>
                                    <option value="وسام بطل الميدان">وسام بطل الميدان</option>
                                </select>'''
replacement = '''<option value="وسام الانضباط الذهبي">وسام الانضباط الذهبي</option>
                                    <option value="وسام بطل الميدان">وسام بطل الميدان</option>
                                    <option value="وسام مدرب خيري معتمد">وسام مدرب خيري معتمد</option>
                                </select>'''
text = text.replace(target, replacement)
with open(r'templates\partials\volunteers.html', 'w', encoding='utf-8') as f:
    f.write(text)
