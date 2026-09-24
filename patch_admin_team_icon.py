import re

with open('templates/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

# I want to update the AJAX script to also update the `fa-users` span
old_js = """if(span.innerHTML.includes('fa-location-dot')) {
                                        span.innerHTML = `<i class="fa-solid fa-location-dot"></i> ${newLoc}`;
                                    }"""
new_js = """if(span.innerHTML.includes('fa-location-dot')) {
                                        span.innerHTML = `<i class="fa-solid fa-location-dot"></i> ${newLoc}`;
                                    }
                                    if(span.innerHTML.includes('fa-users')) {
                                        span.innerHTML = `<i class="fa-solid fa-users"></i> ${newLoc}`;
                                    }"""

if "fa-users" not in content[content.find("AJAX Script for assign_leader"):] and "fa-users" not in content[content.find("assignLeaderForm"):]:
    content = content.replace(old_js, new_js)

with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("admin.html patched to also update team icon.")
