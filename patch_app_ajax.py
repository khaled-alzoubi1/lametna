import re
import json

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. AJAX check for /admin_dashboard
ajax_check = """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('partials/volunteers.html', volunteers=volunteers, settings=settings)
"""
if "request.headers.get('X-Requested-With') == 'XMLHttpRequest'" not in content:
    content = content.replace(
        'events = Event.query.order_by(Event.id.desc()).all()',
        ajax_check + '\n    events = Event.query.order_by(Event.id.desc()).all()'
    )

# 2. Add real chart data logic
chart_logic = """
    # Real Chart Data
    import collections
    
    # 1. Hours Growth Curve (by month of creation)
    hours_dict = collections.defaultdict(int)
    for v in Volunteer.query.all():
        if v.created_at:
            m = v.created_at.strftime('%Y-%m')
            hours_dict[m] += (v.volunteer_hours or 0)
    sorted_months = sorted(hours_dict.keys())[-6:] # last 6 months
    growth_labels = sorted_months
    growth_data = [hours_dict[m] for m in sorted_months]
    if not growth_labels:
        growth_labels = ['لا يوجد بيانات']
        growth_data = [0]
    
    # 2. Activity Stats (Events by Title Category)
    keywords = ['تنظيم', 'تدريب', 'طبي', 'ثقافي', 'بيئي']
    activity_data = [Event.query.filter(Event.title.ilike(f'%{kw}%')).count() for kw in keywords]
    total_activities = Event.query.count()
    
    chart_data = {
        'city_labels': list(city_counts.keys()),
        'city_data': list(city_counts.values()),
        'growth_labels': growth_labels,
        'growth_data': growth_data,
        'activity_labels': keywords,
        'activity_data': activity_data,
        'total_activities': total_activities
    }
"""

if "# Real Chart Data" not in content:
    # Replace the mocked growth_labels, growth_data, activity_labels, activity_data
    # Look for chart_data = { ... }
    start_idx = content.find("growth_labels = [")
    if start_idx == -1:
        start_idx = content.find("chart_data = {") - 50 # rough fallback
    
    end_idx = content.find("return render_template(", start_idx)
    
    if start_idx != -1 and end_idx != -1:
        # We will keep city_counts since it's already dynamically built above!
        # wait, city_counts = dict(Counter(v.city for v in all_volunteers if v.city)) is already there.
        old_block = content[start_idx:end_idx]
        content = content.replace(old_block, chart_logic + '\n    ')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("app.py successfully patched for AJAX and charts.")
