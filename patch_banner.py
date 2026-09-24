import re

def update_banner(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_banner = r"""    <!-- شريط الإعلانات -->
    <div style="background: #facc15; color: #854d0e; text-align: center; padding: 10px; font-weight: bold; border-bottom: 2px solid #eab308; font-size: 0.95rem;">
        أهلاً بكم في المنصة الرسمية لفريق لمتنا بصمة
    </div>"""
    new_banner = """    <!-- شريط الإعلانات -->
    {% if sys_settings and sys_settings.is_banner_active and sys_settings.banner_text %}
    <div style="background: #facc15; color: #854d0e; text-align: center; padding: 10px; font-weight: bold; border-bottom: 2px solid #eab308; font-size: 0.95rem;">
        {{ sys_settings.banner_text }}
    </div>
    {% endif %}"""
    
    if '{% if sys_settings' not in content:
        content = content.replace(old_banner, new_banner)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

update_banner('templates/index.html')
update_banner('templates/profile.html')
print('Banner updated in templates.')
