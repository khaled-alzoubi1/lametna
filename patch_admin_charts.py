import re

with open('templates/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace references in the JS
content = re.sub(r"labels:\s*data\.growth_labels", "labels: {{ hours_chart_data | safe }}.labels", content)
content = re.sub(r"data:\s*data\.growth_data", "data: {{ hours_chart_data | safe }}.data", content)

content = re.sub(r"labels:\s*data\.activity_labels", "labels: {{ activities_chart_data | safe }}.labels", content)
content = re.sub(r"data:\s*data\.activity_data", "data: {{ activities_chart_data | safe }}.data", content)

with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("admin.html patched to use exact JSON vars.")
