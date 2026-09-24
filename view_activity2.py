import ast
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(repr(lines[784:800]))
