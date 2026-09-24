import re
with open('templates/admin.html', 'r', encoding='utf-8') as f:
    text = f.read()
modals = re.findall(r'id=["\']([^"\']*(?:[mM]odal|Modal)[^"\']*)["\']', text)
print(modals)
