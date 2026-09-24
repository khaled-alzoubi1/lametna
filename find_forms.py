import re

with open('templates/admin.html', 'r', encoding='utf-8') as f:
    text = f.read()

for match in re.finditer(r'<form[^>]*action=["\'](.*?)["\']', text):
    print(match.group(1))
