import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update filter args
content = content.replace(
    "filter_gender = request.args.get('filter_gender', '').strip()",
    "filter_gender = request.args.get('filter_gender', '').strip()\n    filter_event_id = request.args.get('event_id', '').strip()"
)

# 2. Add query filter
filter_logic = """    if filter_gender:
        vol_query = vol_query.filter(Volunteer.gender == filter_gender)"""

new_filter_logic = """    if filter_gender:
        vol_query = vol_query.filter(Volunteer.gender == filter_gender)
    if filter_event_id and filter_event_id.isdigit():
        vol_query = vol_query.join(EventRegistration).filter(
            EventRegistration.event_id == int(filter_event_id),
            EventRegistration.attended == True
        )"""

content = content.replace(filter_logic, new_filter_logic)

# 3. Add recent_events
content = content.replace(
    "events = Event.query.order_by(Event.id.desc()).all()",
    "events = Event.query.order_by(Event.id.desc()).all()\n    recent_events = Event.query.order_by(Event.id.desc()).limit(15).all()"
)

# 4. Add to render_template
content = content.replace(
    "events=events,",
    "events=events,\n        recent_events=recent_events,"
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("app.py successfully patched.")
