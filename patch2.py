import re

with open('templates/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace target="_blank" inside tags that have url_for
new_content = re.sub(
    r'(<a\s+[^>]*href\s*=\s*"{{\s*url_for[^}]*}}"[^>]*)target="_blank"([^>]*>)',
    r'\1\2',
    content
)

with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Patched admin.html successfully')
