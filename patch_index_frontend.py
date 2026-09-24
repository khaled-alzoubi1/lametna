import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Gender Validation
gender_pattern = r'<select name="gender" class="custom-input" required>.*?</select>'
gender_repl = """<select name="gender" class="custom-input" required>
                            <option value="ذكر">ذكر</option>
                            <option value="أنثى">أنثى</option>
                        </select>"""
content = re.sub(gender_pattern, gender_repl, content, flags=re.IGNORECASE|re.DOTALL)

# 2. Name validation (Using replace to avoid regex escape issues)
old_name = '<input type="text" name="name" class="custom-input" placeholder="الاسم الرباعي" required>'
new_name = '<input type="text" name="name" class="custom-input" placeholder="الاسم الرباعي" pattern="^[\\u0600-\\u06FF\\s]+$" title="يرجى إدخال الاسم باللغة العربية فقط" required>'

# If exact match fails, use regex with a safe replacement string
match = re.search(r'<input type="text" name="name"[^>]*>', content, flags=re.IGNORECASE)
if match:
    content = content[:match.start()] + new_name + content[match.end():]

# 3. Form Dropdown Cleanup (city and team)
options_html = """
                            <option value="عمان">عمان</option>
                            <option value="الزرقاء">الزرقاء</option>
                            <option value="إربد">إربد</option>
                            <option value="البلقاء">البلقاء</option>
                            <option value="السلط">السلط</option>
                            <option value="مأدبا">مأدبا</option>
                            <option value="أخرى">أخرى</option>
"""

city_pattern = r'<select name="city" id="modalCitySelect" class="custom-input" required>.*?</select>'
city_repl = f'<select name="city" id="modalCitySelect" class="custom-input" required>\n{options_html}                        </select>'
content = re.sub(city_pattern, city_repl, content, flags=re.IGNORECASE|re.DOTALL)

team_pattern = r'<select name="team" id="modalTeamSelect" class="custom-input" required>.*?</select>'
team_repl = f'<select name="team" id="modalTeamSelect" class="custom-input" required>\n{options_html}                        </select>'
content = re.sub(team_pattern, team_repl, content, flags=re.IGNORECASE|re.DOTALL)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("index.html patched.")
