import re

new_options = """
                            <option value="">-- اختر --</option>
                            <option value="عمان">عمان</option>
                            <option value="اربد">اربد</option>
                            <option value="الزرقاء">الزرقاء</option>
                            <option value="البلقاء (السلط)">البلقاء (السلط)</option>
                            <option value="جرش">جرش</option>
                            <option value="أخرى">أخرى</option>
"""

new_filter_options = """
                          <option value="">تصفية حسب المحافظة/الفريق</option>
                          <option value="عمان"{% if filter_city == 'عمان' %} selected{% endif %}>عمان</option>
                          <option value="اربد"{% if filter_city == 'اربد' %} selected{% endif %}>اربد</option>
                          <option value="الزرقاء"{% if filter_city == 'الزرقاء' %} selected{% endif %}>الزرقاء</option>
                          <option value="البلقاء (السلط)"{% if filter_city == 'البلقاء (السلط)' %} selected{% endif %}>البلقاء (السلط)</option>
                          <option value="جرش"{% if filter_city == 'جرش' %} selected{% endif %}>جرش</option>
                          <option value="أخرى"{% if filter_city == 'أخرى' %} selected{% endif %}>أخرى</option>
"""

# Patch index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    idx_content = f.read()

def replacer_idx(match):
    # keep the <select ...> opening tag, replace the inner contents
    return match.group(1) + new_options + "                        </select>"

idx_content = re.sub(r'(<select name="city"[^>]*>).*?</select>', replacer_idx, idx_content, flags=re.IGNORECASE|re.DOTALL)
idx_content = re.sub(r'(<select name="team"[^>]*>).*?</select>', replacer_idx, idx_content, flags=re.IGNORECASE|re.DOTALL)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(idx_content)

# Patch admin.html
with open('templates/admin.html', 'r', encoding='utf-8') as f:
    admin_content = f.read()

def replacer_admin(match):
    return match.group(1) + new_filter_options + "                      </select>"

admin_content = re.sub(r'(<select name="filter_city"[^>]*>).*?</select>', replacer_admin, admin_content, flags=re.IGNORECASE|re.DOTALL)

with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(admin_content)

print("Regions strictly updated.")
