import sys

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    line_num = i + 1
    stripped = line.strip()
    
    if line_num > 1170 or line_num == 280:
        new_lines.append(line)
        continue
        
    if stripped.startswith('db.session.commit()'):
        indent = line[:len(line) - len(line.lstrip())]
        comment = ''
        if '#' in stripped:
            comment = ' ' + stripped[stripped.index('#'):]
            
        new_lines.append(indent + 'try:\n')
        new_lines.append(indent + '    db.session.commit()' + comment + '\n')
        new_lines.append(indent + 'except Exception as e:\n')
        new_lines.append(indent + '    db.session.rollback()\n')
        new_lines.append(indent + "    flash('حدث خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً', 'error')\n")
    else:
        new_lines.append(line)

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Patch applied successfully.')
