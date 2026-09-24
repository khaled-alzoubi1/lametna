import re
import os

files = ['templates/admin.html', 'templates/partials/volunteers.html']
for filepath in files:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        print(f"--- {filepath} ---")
        for match in re.finditer(r'url_for\([\'"](.*?)[\'"]', text):
            print(match.group(1))
