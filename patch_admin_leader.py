import re

with open('templates/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's find the grid template columns. It was `repeat(auto-fit, minmax(220px, 1fr)) 150px`
# We might need to change it to accommodate the new column.
content = content.replace(
    'repeat(auto-fit, minmax(220px, 1fr)) 150px',
    'repeat(auto-fit, minmax(220px, 1fr)) 150px' # Let's keep it auto-fit
)

# 1. Update the volunteer_id select to include data-location
content = content.replace(
    '<option value="{{ v.id }}" data-email="{{ v.email|lower }}">{{ v.name }} - ({{ v.city }})</option>',
    '<option value="{{ v.id }}" data-email="{{ v.email|lower }}" data-location="{{ v.city }}">{{ v.name }} - ({{ v.city }})</option>'
)

# 2. Update the onchange javascript to also set location
old_onchange = """const email = opt.getAttribute('data-email');
                            const posSelect = document.getElementById('assignLeaderPosSelect');"""
new_onchange = """const email = opt.getAttribute('data-email');
                            const loc = opt.getAttribute('data-location');
                            const posSelect = document.getElementById('assignLeaderPosSelect');
                            const locSelect = document.getElementById('assignLeaderLocSelect');
                            if(locSelect && loc) { locSelect.value = loc; }"""
content = content.replace(old_onchange, new_onchange)

# 3. Inject the new `<select name="location" ...>`
new_field = """                    <div>
                        <label style="display:block; margin-bottom: 6px; font-weight: 700; font-size: 0.9rem;">تغيير المحافظة/الفريق</label>
                        <select name="location" id="assignLeaderLocSelect" class="form-select custom-input">
                            <option value="">-- المحافظة الحالية --</option>
                            <option value="عمان">عمان</option>
                            <option value="اربد">اربد</option>
                            <option value="الزرقاء">الزرقاء</option>
                            <option value="البلقاء (السلط)">البلقاء (السلط)</option>
                            <option value="جرش">جرش</option>
                            <option value="أخرى">أخرى</option>
                        </select>
                    </div>
"""
# Insert it before the photo_url field
content = content.replace(
    '<div>\n                        <label style="display:block; margin-bottom: 6px; font-weight: 700; font-size: 0.9rem;">رابط الصورة الشخصية (اختياري)</label>',
    new_field + '                    <div>\n                        <label style="display:block; margin-bottom: 6px; font-weight: 700; font-size: 0.9rem;">رابط الصورة الشخصية (اختياري)</label>'
)

# 4. Change the form to use AJAX
old_form = """<form action="{{ url_for('assign_leader') }}" method="POST" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)) 150px; gap: 12px; align-items: flex-end;">"""
new_form = """<form id="assignLeaderForm" action="{{ url_for('assign_leader') }}" method="POST" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; align-items: flex-end;">"""
content = content.replace(old_form, new_form)

# Add the AJAX script for this form
ajax_script = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    const assignLeaderForm = document.getElementById('assignLeaderForm');
    if(assignLeaderForm) {
        assignLeaderForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(assignLeaderForm);
            fetch(assignLeaderForm.action, {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(res => res.json())
            .then(data => {
                if(data.success) {
                    alert('تم التحديث بنجاح!');
                    // Locate the volunteer's card and update the location
                    const volId = formData.get('volunteer_id');
                    const newLoc = formData.get('location');
                    if(newLoc) {
                        const locSpans = document.querySelectorAll(`.admin-swipe-card input[value="${volId}"]`);
                        locSpans.forEach(input => {
                            const card = input.closest('.admin-swipe-card');
                            if(card) {
                                // Find the location span inside the card
                                const spans = card.querySelectorAll('span');
                                spans.forEach(span => {
                                    if(span.innerHTML.includes('fa-location-dot')) {
                                        span.innerHTML = `<i class="fa-solid fa-location-dot"></i> ${newLoc}`;
                                    }
                                });
                                // Also update the dropdown option data-location
                                const opt = document.querySelector(`#assignLeaderVolSelect option[value="${volId}"]`);
                                if(opt) opt.setAttribute('data-location', newLoc);
                            }
                        });
                    }
                } else {
                    alert('حدث خطأ: ' + (data.message || ''));
                }
            })
            .catch(err => console.error(err));
        });
    }
});
</script>
"""
if "assignLeaderForm" not in content and "AJAX Script for assign_leader" not in content:
    content = content.replace('</body>', ajax_script + '\n</body>')

with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("admin.html patched for assign_leader updates.")
