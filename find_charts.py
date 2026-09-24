with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'chart_data' in line or 'hours_chart_data' in line or 'activities_chart_data' in line:
        print(f"Line {i}: {line.strip().encode('ascii', 'ignore').decode('ascii')}")
