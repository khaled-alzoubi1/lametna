import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

city_match = re.search(r'<select name="city"[^>]*>(.*?)</select>', content, re.IGNORECASE | re.DOTALL)
if city_match:
    print("CITY options found")

with open('templates/admin.html', 'r', encoding='utf-8') as f:
    admin_content = f.read()
    
city_admin_match = re.search(r'<select name="filter_city"[^>]*>(.*?)</select>', admin_content, re.IGNORECASE | re.DOTALL)
if city_admin_match:
    print("FILTER_CITY options found")
