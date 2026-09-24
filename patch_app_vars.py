import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add explicit variables to render_template
content = content.replace(
    'chart_data=chart_data,',
    'chart_data=chart_data,\n        hours_chart_data=json.dumps({"labels": growth_labels, "data": growth_data}),\n        activities_chart_data=json.dumps({"labels": keywords, "data": activity_data}),'
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Added exact variables requested to render_template")
