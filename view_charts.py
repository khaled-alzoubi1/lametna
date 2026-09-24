with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(790, 820):
    print(lines[i].strip().encode('ascii', 'ignore').decode('ascii'))
