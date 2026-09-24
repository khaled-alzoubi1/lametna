import re

with open('templates/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

event_filter_html = """
                <div>
                    <select name="event_id" class="form-control mb-3 custom-input" style="width: 100%; border: 1px solid var(--jo-border); background: var(--jo-bg); color: var(--jo-light-gray); padding: 9px 12px; border-radius: var(--radius-sm);">
                        <option value="">التصفية حسب التواجد في الفعاليات (الكل)</option>
                        {% for event in recent_events %}
                        <option value="{{ event.id }}" {% if request.args.get('event_id') == event.id|string %}selected{% endif %}>{{ event.title }}</option>
                        {% endfor %}
                    </select>
                </div>"""

if 'name="event_id"' not in content:
    content = re.sub(
        r'(<select name="filter_gender"[^>]*>.*?</select>\s*</div>)',
        r'\1\n' + event_filter_html,
        content,
        flags=re.DOTALL
    )

    # I also need to make sure the "Clear filter" button checks for event_id
    # `{% if search_name or filter_city or filter_skill or filter_gender %}`
    # Replace it with `{% if search_name or filter_city or filter_skill or filter_gender or request.args.get('event_id') %}`
    content = content.replace(
        '{% if search_name or filter_city or filter_skill or filter_gender %}',
        '{% if search_name or filter_city or filter_skill or filter_gender or request.args.get(\'event_id\') %}'
    )

with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("admin.html successfully patched with event_id filter.")
