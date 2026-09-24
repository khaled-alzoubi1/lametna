import re

with open('templates/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

banner_btn = """
                <button onclick="openAdminModal('bannerModal')" class="btn-ctrl-action" style="background: #dc3545; color: white; padding: 9px 18px; border-radius: 50px; font-weight: 800; border: none; cursor: pointer;">
                    <i class="fa-solid fa-bullhorn"></i> لوحة الإعلانات
                </button>"""
wa_btn = """
                <button onclick="openAdminModal('waBroadcastModal')" class="btn-ctrl-action" style="background: #28a745; color: white; padding: 9px 18px; border-radius: 50px; font-weight: 800; border: none; cursor: pointer;">
                    <i class="fa-brands fa-whatsapp"></i> رسالة واتساب مخصصة
                </button>"""

if 'لوحة الإعلانات' not in content:
    wa_comm_btn_start = '<a href="{{ settings.whatsapp_url'
    content = content.replace(wa_comm_btn_start, banner_btn + '\n' + wa_btn + '\n                ' + wa_comm_btn_start)

modals = """
    <div id="bannerModal" class="admin-modal-overlay">
        <div class="admin-modal-box">
            <button class="close-modal-btn" onclick="closeAdminModal('bannerModal')">&times;</button>
            <h3 style="margin-bottom: 15px; color: var(--jo-black);">إدارة لوحة الإعلانات</h3>
            <form action="{{ url_for('update_banner') }}" method="POST">
                <textarea name="banner_text" class="custom-input" rows="3" placeholder="نص الإعلان...">{{ sys_settings.banner_text if sys_settings else '' }}</textarea>
                <label style="display: flex; align-items: center; gap: 10px; margin-top: 15px;">
                    <input type="checkbox" name="is_banner_active" {% if sys_settings and sys_settings.is_banner_active %}checked{% endif %}>
                    تفعيل لوحة الإعلانات
                </label>
                <button type="submit" class="btn-primary-block" style="margin-top: 15px;">حفظ</button>
            </form>
        </div>
    </div>
    <div id="waBroadcastModal" class="admin-modal-overlay">
        <div class="admin-modal-box" style="max-width: 600px;">
            <button class="close-modal-btn" onclick="closeAdminModal('waBroadcastModal')">&times;</button>
            <h3 style="margin-bottom: 15px; color: var(--jo-black);">رسالة واتساب مخصصة للمحددين</h3>
            <textarea id="waMessageText" class="custom-input" rows="4" placeholder="اكتب الرسالة هنا..."></textarea>
            <button type="button" class="btn-primary-block" onclick="generateWALinks()" style="margin-top: 15px; background: #28a745;">توليد الروابط</button>
            <div id="waLinksContainer" style="margin-top: 15px; display: flex; flex-direction: column; gap: 8px; max-height: 300px; overflow-y: auto;"></div>
        </div>
    </div>
"""
if 'id="bannerModal"' not in content:
    content = content.replace('</body>', modals + '\n</body>')

checkbox_html = '<input type="checkbox" class="vol-select" value="{{ v.id }}" data-name="{{ v.name }}" data-phone="{{ v.phone }}" style="transform: scale(1.5); margin-left: 10px; cursor: pointer;">'
if 'class="vol-select"' not in content:
    content = content.replace('<h3 style="margin-bottom: 5px; color: var(--jo-black); font-size: 1.1rem; font-weight: 900; display: flex; align-items: center;">',
                              '<h3 style="margin-bottom: 5px; color: var(--jo-black); font-size: 1.1rem; font-weight: 900; display: flex; align-items: center;">\n' + checkbox_html)

select_all_html = """
<div style="background: rgba(15,23,42,0.8); padding: 15px; border-radius: 12px; margin-bottom: 15px; display: flex; align-items: center; gap: 15px;">
    <input type="checkbox" id="selectAllVols" style="transform: scale(1.5); cursor: pointer;">
    <label for="selectAllVols" style="color: white; font-weight: bold; cursor: pointer; margin-bottom:0;">تحديد الكل</label>
</div>
"""
if 'id="selectAllVols"' not in content:
    content = content.replace('<!-- Grid: Approved Volunteers -->', select_all_html + '\n<!-- Grid: Approved Volunteers -->')

sticky_toolbar = """
    <div id="bulkToolbar" style="display: none; position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: #1e293b; padding: 15px 25px; border-radius: 50px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); z-index: 1000; align-items: center; gap: 15px; border: 2px solid #3b82f6;">
        <span style="color: white; font-weight: bold; background: #3b82f6; padding: 5px 12px; border-radius: 20px;" id="bulkCountDisplay">0</span>
        <form id="bulkApproveForm" action="{{ url_for('bulk_approve') }}" method="POST" style="margin:0;"><button type="submit" class="btn-ctrl-action" style="background:#10b981; color:white; border:none; padding: 8px 15px;">اعتماد المحدد</button></form>
        <button type="button" class="btn-ctrl-action" style="background:#f59e0b; color:white; border:none; padding: 8px 15px;" onclick="promptBulk('hours')">إضافة ساعات</button>
        <button type="button" class="btn-ctrl-action" style="background:#8b5cf6; color:white; border:none; padding: 8px 15px;" onclick="promptBulk('events')">إضافة فعاليات</button>
        <button type="button" class="btn-ctrl-action" style="background:#ef4444; color:white; border:none; padding: 8px 15px;" onclick="promptBulk('evaluation')">ملاحظة إدارية</button>
        <form id="bulkActionFormHidden" method="POST" style="display:none;"></form>
    </div>
"""
if 'id="bulkToolbar"' not in content:
    content = content.replace('</body>', sticky_toolbar + '\n</body>')


# regex for update forms
# Events
content = re.sub(
    r'<form action="\{\{\s*url_for\(\'adjust_events\',\s*volunteer_id=v\.id,\s*action=\'increment\'\)\s*\}\}" method="POST" style="margin: 0;">\s*<button type="submit" class="btn-step-arrow" title="[^"]*">\+</button>\s*</form>',
    r'<button type="button" class="btn-step-arrow" onclick="updateStat({{ v.id }}, \'events\', \'increment\')">+</button>',
    content
)
content = re.sub(
    r'<form action="\{\{\s*url_for\(\'adjust_events\',\s*volunteer_id=v\.id,\s*action=\'decrement\'\)\s*\}\}" method="POST" style="margin: 0;">\s*<button type="submit" class="btn-step-arrow" title="[^"]*">-</button>\s*</form>',
    r'<button type="button" class="btn-step-arrow" onclick="updateStat({{ v.id }}, \'events\', \'decrement\')">-</button>',
    content
)
# Note: we need to replace text `الفعاليات: ` carefully. I'll just find `class="counter-val-display"` wrapping it.
content = re.sub(
    r'<span class="counter-val-display">الفعاليات:\s*\{\{\s*v\.attended_events_count\|default\(0\)\s*\}\}</span>',
    r'<span id="events-count-{{ v.id }}" class="counter-val-display">الفعاليات: {{ v.attended_events_count|default(0) }}</span>',
    content
)

# Hours
content = re.sub(
    r'<form action="\{\{\s*url_for\(\'adjust_hours\',\s*volunteer_id=v\.id,\s*action=\'increment\'\)\s*\}\}" method="POST" style="margin: 0;">\s*<button type="submit" class="btn-step-arrow" title="[^"]*">\+</button>\s*</form>',
    r'<button type="button" class="btn-step-arrow" onclick="updateStat({{ v.id }}, \'hours\', \'increment\')">+</button>',
    content
)
content = re.sub(
    r'<form action="\{\{\s*url_for\(\'adjust_hours\',\s*volunteer_id=v\.id,\s*action=\'decrement\'\)\s*\}\}" method="POST" style="margin: 0;">\s*<button type="submit" class="btn-step-arrow" title="[^"]*">-</button>\s*</form>',
    r'<button type="button" class="btn-step-arrow" onclick="updateStat({{ v.id }}, \'hours\', \'decrement\')">-</button>',
    content
)
content = re.sub(
    r'<span class="counter-val-display">ساعات:\s*\{\{\s*v\.volunteer_hours\|default\(0\)\s*\}\}</span>',
    r'<span id="hours-count-{{ v.id }}" class="counter-val-display">ساعات: {{ v.volunteer_hours|default(0) }}</span>',
    content
)


# Remove welcome WhatsApp
content = re.sub(
    r'<a href="https://wa\.me/962\{\{ v\.phone[^"]*"[^>]*title="واتساب ترحيبي"[^>]*>.*?</a>',
    '',
    content,
    flags=re.DOTALL
)

js_code = """
<script>
const selectAll = document.getElementById('selectAllVols');
const volCheckboxes = document.querySelectorAll('.vol-select');
const bulkToolbar = document.getElementById('bulkToolbar');
const bulkCount = document.getElementById('bulkCountDisplay');

function updateBulkToolbar() {
    const checked = document.querySelectorAll('.vol-select:checked');
    if (checked.length > 0) {
        bulkToolbar.style.display = 'flex';
        bulkCount.innerText = checked.length;
    } else {
        bulkToolbar.style.display = 'none';
    }
}

if(selectAll) {
    selectAll.addEventListener('change', (e) => {
        volCheckboxes.forEach(cb => cb.checked = e.target.checked);
        updateBulkToolbar();
    });
}
volCheckboxes.forEach(cb => cb.addEventListener('change', updateBulkToolbar));

function getSelectedVols() {
    return Array.from(document.querySelectorAll('.vol-select:checked')).map(cb => cb.value);
}

function promptBulk(type) {
    const vols = getSelectedVols();
    if(vols.length === 0) return;
    
    let actionUrl = '';
    let extraInput = '';
    
    if(type === 'hours') {
        let val = prompt('أدخل عدد الساعات لإضافتها:');
        if(!val) return;
        actionUrl = '{{ url_for("bulk_add_hours") }}';
        extraInput = `<input type="hidden" name="hours" value="${val}">`;
    } else if(type === 'events') {
        let val = prompt('أدخل عدد الفعاليات لإضافتها:');
        if(!val) return;
        actionUrl = '{{ url_for("bulk_add_events") }}';
        extraInput = `<input type="hidden" name="events" value="${val}">`;
    } else if(type === 'evaluation') {
        let val = prompt('أدخل الملاحظة الإدارية:');
        if(!val) return;
        actionUrl = '{{ url_for("bulk_evaluation") }}';
        extraInput = `<input type="hidden" name="evaluation" value="${val}">`;
    }
    
    const form = document.getElementById('bulkActionFormHidden');
    form.action = actionUrl;
    form.innerHTML = extraInput;
    vols.forEach(vid => {
        form.innerHTML += `<input type="hidden" name="vol_ids" value="${vid}">`;
    });
    form.submit();
}

const bForm = document.getElementById('bulkApproveForm');
if(bForm) {
    bForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const vols = getSelectedVols();
        if(vols.length === 0) return;
        const form = e.target;
        form.innerHTML = '<button type="submit" class="btn-ctrl-action" style="background:#10b981; color:white; border:none; padding: 8px 15px;">اعتماد المحدد</button>';
        vols.forEach(vid => {
            form.innerHTML += `<input type="hidden" name="vol_ids" value="${vid}">`;
        });
        form.submit();
    });
}

function generateWALinks() {
    const msg = document.getElementById('waMessageText').value;
    const container = document.getElementById('waLinksContainer');
    container.innerHTML = '';
    const checked = document.querySelectorAll('.vol-select:checked');
    if(checked.length === 0) {
        container.innerHTML = '<p style="color:red; font-weight:bold;">الرجاء تحديد متطوعين أولاً.</p>';
        return;
    }
    checked.forEach(cb => {
        let phone = cb.getAttribute('data-phone');
        let name = cb.getAttribute('data-name');
        if(phone.startsWith('0')) phone = phone.substring(1);
        let link = `https://wa.me/962${phone}?text=${encodeURIComponent(msg)}`;
        container.innerHTML += `<a href="${link}" target="_blank" class="btn-ctrl-action" style="background:#dcfce7; color:#16a34a; text-decoration:none; padding:10px; display:block; text-align:center;">إرسال إلى ${name}</a>`;
    });
}

function updateStat(volId, type, action) {
    fetch('{{ url_for("ajax_update_stat") }}', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({vol_id: volId, type: type, action: action})
    })
    .then(r => r.json())
    .then(data => {
        if(data.success) {
            if(type === 'hours') document.getElementById('hours-count-'+volId).innerText = 'ساعات: ' + data.hours;
            if(type === 'events') document.getElementById('events-count-'+volId).innerText = 'الفعاليات: ' + data.events;
        } else {
            alert('حدث خطأ أثناء التحديث');
        }
    })
    .catch(err => {
        alert('حدث خطأ في الاتصال');
    });
}
</script>
"""
if 'updateStat(' not in content:
    content = content.replace('</body>', js_code + '\n</body>')

with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('admin.html patched.')
