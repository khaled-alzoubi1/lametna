with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def assign_leader():')
end_idx = text.find('return redirect(url_for(\'admin_dashboard\'))', idx)
with open('leader_route.txt', 'w', encoding='utf-8') as out:
    out.write(text[idx:end_idx+60])
