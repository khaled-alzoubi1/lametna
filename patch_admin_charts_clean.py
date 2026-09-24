import re

with open('templates/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's clean it up to assign to const variables
js_vars = """
        const data = {{ chart_data | tojson }};
        const hoursData = {{ hours_chart_data | safe if hours_chart_data else 'null' }};
        const activitiesData = {{ activities_chart_data | safe if activities_chart_data else 'null' }};
"""
content = re.sub(r'const data = \{\{ chart_data \| tojson \}\};', js_vars, content)

content = re.sub(r"labels: \{\{ hours_chart_data.*?\.labels", "labels: hoursData ? hoursData.labels : data.growth_labels", content)
content = re.sub(r"data: \{\{ hours_chart_data.*?\.data", "data: hoursData ? hoursData.data : data.growth_data", content)

content = re.sub(r"labels: \{\{ activities_chart_data.*?\.labels", "labels: activitiesData ? activitiesData.labels : data.activity_labels", content)
content = re.sub(r"data: \{\{ activities_chart_data.*?\.data", "data: activitiesData ? activitiesData.data : data.activity_data", content)

with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("admin.html patched to use clean JS consts.")
