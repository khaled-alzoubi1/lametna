import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to find def index(): and then the FIRST return render_template( in that block.
# We'll split the content into routes and patch just index()
parts = content.split('def index():')
if len(parts) == 2:
    head = parts[0]
    tail = parts[1]
    
    # In tail, find the first 'return render_template('
    # and insert the query before it.
    insert_str = "    recent_events = Event.query.order_by(Event.id.desc()).limit(15).all()\n    "
    
    # We can replace '    return render_template(' with '    recent_events = Event.query.order_by(Event.id.desc()).limit(15).all()\n    return render_template('
    # Make sure we only do it for the FIRST occurrence in tail.
    tail = tail.replace('    return render_template(', insert_str + 'return render_template(', 1)
    
    new_content = head + 'def index():' + tail
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Fixed app.py successfully!")
else:
    print("Could not find def index():")
