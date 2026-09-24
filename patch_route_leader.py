import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update def assign_leader() to capture location and return JSON if AJAX
old_leader = """    v = Volunteer.query.get_or_404(volunteer_id)"""

new_leader = """    v = Volunteer.query.get_or_404(volunteer_id)
    
    new_location = request.form.get('location')
    if new_location:
        v.city = new_location
        v.team = new_location  # Usually team and city are updated together here based on previous patches
"""
content = content.replace(old_leader, new_leader)

# Let's find where db.session.commit() happens inside assign_leader
commit_idx = content.find("db.session.commit()", content.find("def assign_leader():"))
if commit_idx != -1:
    end_idx = content.find("return redirect(url_for('admin_dashboard')", commit_idx)
    if end_idx != -1:
        ajax_check = """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from flask import jsonify
        return jsonify({'success': True})
    
    return redirect(url_for('admin_dashboard')"""
        content = content[:end_idx] + ajax_check + content[end_idx+len("return redirect(url_for('admin_dashboard')"):]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("app.py patched for assign_leader AJAX and location updates.")
