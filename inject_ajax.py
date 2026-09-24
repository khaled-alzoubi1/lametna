import re

with open('templates/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

ajax_script = """
<!-- AJAX Filter Script -->
<script>
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    if(searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(searchForm);
            const params = new URLSearchParams(formData);
            const url = searchForm.action + '?' + params.toString();
            
            fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.text())
            .then(html => {
                document.getElementById('volunteersContainer').innerHTML = html;
                
                // Re-bind checkboxes for bulk logic
                if(typeof updateBulkToolbar === 'function') {
                    const newCheckboxes = document.querySelectorAll('.vol-select');
                    newCheckboxes.forEach(cb => cb.addEventListener('change', updateBulkToolbar));
                }
            })
            .catch(err => console.error('AJAX Error:', err));
        });
    }
});
</script>
"""

# Append to body if not exists
if "AJAX Filter Script" not in content:
    content = content.replace('</body>', ajax_script + '\n</body>')
    with open('templates/admin.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("AJAX filter script injected.")
else:
    print("AJAX filter script already exists.")
