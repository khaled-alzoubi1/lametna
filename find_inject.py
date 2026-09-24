import re

with open('templates/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's find where the search form buttons are.
# Search for '<button type="submit"' in the form that has 'filter_gender'
match = re.search(r'<select name="filter_gender"[^>]*>.*?</select>.*?</div>', content, flags=re.DOTALL)
if match:
    print("Found filter_gender select!")
else:
    print("Could not find filter_gender select.")
