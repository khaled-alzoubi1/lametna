import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add SystemSettings model
model_code = """
class SystemSettings(db.Model):
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    banner_text = db.Column(db.String(500), default='أهلاً بكم في المنصة الرسمية لفريق لمتنا بصمة')
    is_banner_active = db.Column(db.Boolean, default=False)
"""
if 'class SystemSettings' not in content:
    content = content.replace('class SiteSetting(db.Model):', model_code + '\nclass SiteSetting(db.Model):')

# 2. Add Context Processor
context_code = """
@app.context_processor
def inject_sys_settings():
    try:
        sys_settings = SystemSettings.query.first()
        if not sys_settings:
            sys_settings = SystemSettings()
            db.session.add(sys_settings)
            db.session.commit()
    except Exception:
        db.session.rollback()
        sys_settings = None
    return dict(sys_settings=sys_settings)
"""
if 'def inject_sys_settings():' not in content:
    content = content.replace('@app.context_processor\ndef inject_settings():', context_code + '\n@app.context_processor\ndef inject_settings():')
    # Or just put it above def get_settings()
    if 'def inject_sys_settings():' not in content:
        content = content.replace('def get_settings():', context_code + '\ndef get_settings():')


# 3. Add Endpoints
endpoints_code = """
@app.route('/admin/settings/banner', methods=['POST'])
def update_banner():
    if not session.get('admin_logged_in'): return jsonify({'error': 'Unauthorized'}), 403
    sys_settings = SystemSettings.query.first()
    if not sys_settings:
        sys_settings = SystemSettings()
        db.session.add(sys_settings)
    sys_settings.banner_text = request.form.get('banner_text', '')
    sys_settings.is_banner_active = request.form.get('is_banner_active') == 'on'
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    flash('تم تحديث لوحة الإعلانات بنجاح', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/ajax/update_stat', methods=['POST'])
def ajax_update_stat():
    if not session.get('admin_logged_in'): return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    vol_id = data.get('vol_id')
    stat_type = data.get('type')
    action = data.get('action')
    v = Volunteer.query.get(vol_id)
    if not v: return jsonify({'error': 'Not found'}), 404
    
    if stat_type == 'hours':
        if action == 'increment': v.volunteer_hours = (v.volunteer_hours or 0) + 1
        elif action == 'decrement' and (v.volunteer_hours or 0) >= 1: v.volunteer_hours = (v.volunteer_hours or 0) - 1
    elif stat_type == 'events':
        if action == 'increment': v.attended_events_count = (v.attended_events_count or 0) + 1
        elif action == 'decrement' and (v.attended_events_count or 0) > 0: v.attended_events_count = (v.attended_events_count or 0) - 1
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'hours': v.volunteer_hours, 'events': v.attended_events_count})
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'DB Error'}), 500

@app.route('/admin/bulk_approve', methods=['POST'])
def bulk_approve():
    if not session.get('admin_logged_in'): return jsonify({'error': 'Unauthorized'}), 403
    vol_ids = request.form.getlist('vol_ids')
    for vid in vol_ids:
        v = Volunteer.query.get(vid)
        if v:
            v.status = 'approved'
            v.badge_number = None # Or assign next available if logic needed
    try:
        db.session.commit()
        flash('تم اعتماد المتطوعين المحددين بنجاح', 'success')
    except Exception:
        db.session.rollback()
        flash('حدث خطأ', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/bulk_add_hours', methods=['POST'])
def bulk_add_hours():
    if not session.get('admin_logged_in'): return jsonify({'error': 'Unauthorized'}), 403
    vol_ids = request.form.getlist('vol_ids')
    hours = int(request.form.get('hours', 0))
    for vid in vol_ids:
        v = Volunteer.query.get(vid)
        if v: v.volunteer_hours = (v.volunteer_hours or 0) + hours
    try:
        db.session.commit()
        flash('تمت إضافة الساعات للمتطوعين المحددين', 'success')
    except Exception:
        db.session.rollback()
        flash('حدث خطأ', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/bulk_add_events', methods=['POST'])
def bulk_add_events():
    if not session.get('admin_logged_in'): return jsonify({'error': 'Unauthorized'}), 403
    vol_ids = request.form.getlist('vol_ids')
    events = int(request.form.get('events', 0))
    for vid in vol_ids:
        v = Volunteer.query.get(vid)
        if v: v.attended_events_count = (v.attended_events_count or 0) + events
    try:
        db.session.commit()
        flash('تمت إضافة الفعاليات للمتطوعين المحددين', 'success')
    except Exception:
        db.session.rollback()
        flash('حدث خطأ', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/bulk_evaluation', methods=['POST'])
def bulk_evaluation():
    if not session.get('admin_logged_in'): return jsonify({'error': 'Unauthorized'}), 403
    vol_ids = request.form.getlist('vol_ids')
    note = request.form.get('evaluation', '')
    for vid in vol_ids:
        v = Volunteer.query.get(vid)
        if v:
            v.admin_evaluation = (v.admin_evaluation + '\\n' + note) if v.admin_evaluation else note
    try:
        db.session.commit()
        flash('تم إضافة الملاحظة للمتطوعين المحددين', 'success')
    except Exception:
        db.session.rollback()
        flash('حدث خطأ', 'error')
    return redirect(url_for('admin_dashboard'))
"""

if '/admin/settings/banner' not in content:
    content = content.replace('@app.route(\'/admin/settings/update\', methods=[\'POST\'])', endpoints_code + '\n@app.route(\'/admin/settings/update\', methods=[\'POST\'])')

# 4. Add to migrations
migration_append = """        ("system_settings", "banner_text", "VARCHAR(500)"),
        ("system_settings", "is_banner_active", "BOOLEAN DEFAULT FALSE"),
"""
if '("system_settings", "banner_text"' not in content:
    content = content.replace('migrations = [', 'migrations = [\n' + migration_append)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Backend updated.")
