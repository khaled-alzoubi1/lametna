import re

with open('templates/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's just use Jinja {% if not is_ajax %} around everything EXCEPT the container!
# Wait, that's messy. Let's just replace the container with {% include 'partials/volunteers.html' %}

start_tag = '<div class="volunteers-list-container" id="volunteersContainer">'
end_marker = '<div id="eventsTab"' # The next tab

idx_start = content.find(start_tag)
idx_next = content.find(end_marker)

# find the last </div> before idx_next
idx_end = content.rfind('</div>', idx_start, idx_next) + 6

partial_content = content[idx_start:idx_end]

import os
os.makedirs('templates/partials', exist_ok=True)
with open('templates/partials/volunteers.html', 'w', encoding='utf-8') as f:
    f.write(partial_content)

new_content = content[:idx_start] + "{% include 'partials/volunteers.html' %}" + content[idx_end:]

with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Partial extracted successfully.")
