import re
with open('templates/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()
idx = content.find('name="search_name"')
start = content.rfind('<form', 0, idx)
end = content.find('>', start) + 1
print(content[start:end])
