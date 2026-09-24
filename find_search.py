with open('templates/admin.html', 'r', encoding='utf-8') as f:
    for line in f:
        if 'search_name' in line:
            print(line.strip().encode('ascii', 'ignore').decode('ascii'))
