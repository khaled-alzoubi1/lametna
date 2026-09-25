with open(r'templates\partials\volunteers.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''{% if v.is_leader %}
                                    <span style=\"background: #e0f2fe; color: #0284c7; font-weight: 800; padding: 4px 10px; border-radius: 12px; font-size: 0.85rem;\">
                                        <i class=\"fa-solid fa-star\"></i> {{ v.position }}
                                    </span>'''
replacement = '''{% if v.is_leader %}
                                    {% if v.position == 'مدرب معتمد' %}
                                    <span style=\"background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%); color: #fff; font-weight: 800; padding: 4px 10px; border-radius: 12px; font-size: 0.85rem; box-shadow: 0 2px 4px rgba(245, 158, 11, 0.3);\">
                                        <i class=\"fa-solid fa-circle-check\"></i> {{ v.position }}
                                    </span>
                                    {% else %}
                                    <span style=\"background: #e0f2fe; color: #0284c7; font-weight: 800; padding: 4px 10px; border-radius: 12px; font-size: 0.85rem;\">
                                        <i class=\"fa-solid fa-star\"></i> {{ v.position }}
                                    </span>
                                    {% endif %}'''
text = text.replace(target, replacement)
with open(r'templates\partials\volunteers.html', 'w', encoding='utf-8') as f:
    f.write(text)
