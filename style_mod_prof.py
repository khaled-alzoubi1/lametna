with open(r'templates\profile.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''{% if user.is_leader %}
                        <span class=\"badge-volunteer-status\" style=\"background: #e0f2fe; color: #0284c7;\"><i class=\"fa-solid fa-star\"></i> {{ user.position or 'مهمة خاصة' }}</span>
                    {% endif %}'''
replacement = '''{% if user.is_leader %}
                        {% if user.position == 'مدرب معتمد' %}
                        <span class=\"badge-volunteer-status\" style=\"background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%); color: #fff; box-shadow: 0 2px 4px rgba(245, 158, 11, 0.3);\"><i class=\"fa-solid fa-circle-check\"></i> {{ user.position }}</span>
                        {% else %}
                        <span class=\"badge-volunteer-status\" style=\"background: #e0f2fe; color: #0284c7;\"><i class=\"fa-solid fa-star\"></i> {{ user.position or 'مهمة خاصة' }}</span>
                        {% endif %}
                    {% endif %}'''
text = text.replace(target, replacement)
with open(r'templates\profile.html', 'w', encoding='utf-8') as f:
    f.write(text)
