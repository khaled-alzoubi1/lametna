document.addEventListener('DOMContentLoaded', () => {
    // شاشة البداية
    setTimeout(() => {
        const splash = document.getElementById('splash-screen');
        const mainContent = document.getElementById('main-content');
        if (splash && mainContent) {
            splash.style.display = 'none';
            mainContent.classList.remove('hidden');
        }
    }, 2000);

    const homeSection = document.getElementById('home-section');
    const registerSection = document.getElementById('register-section');
    const volunteerHubSection = document.getElementById('volunteer-hub-section');
    const adminDashboard = document.getElementById('admin-dashboard');
    
    const registerBtn = document.getElementById('register-btn');
    const backBtn = document.getElementById('back-btn');
    const profileBtn = document.getElementById('profile-btn');
    
    const loginBtn = document.getElementById('login-btn');
    const loginModal = document.getElementById('login-modal');
    const closeLogin = document.getElementById('close-login');
    const loginForm = document.getElementById('login-form');
    const forgotPasswordLink = document.getElementById('forgot-password-link');
    const toastBanner = document.getElementById('toast-banner');
    const copyPhonesBtn = document.getElementById('copy-phones-btn');

    let currentLoadedVolunteers = [];
    let currentVolunteer = null;

    // إشعار الترحيب المخصص
    function showToast(title, subtitle) {
        if (!toastBanner) return;
        toastBanner.innerHTML = `
            <div class="toast-title">${title}</div>
            <div class="toast-subtitle">${subtitle}</div>
        `;
        toastBanner.classList.remove('hidden');
        setTimeout(() => {
            toastBanner.classList.add('hidden');
        }, 4000);
    }

    // استعادة كلمة المرور
    if (forgotPasswordLink) {
        forgotPasswordLink.addEventListener('click', (e) => {
            e.preventDefault();
            const waMsg = encodeURIComponent('مرحباً إدارة لمتنا بصمة، نسيت كلمة المرور الخاصة بحسابي وأرغب في استعادتها.');
            const choice = confirm('لاستعادة كلمة المرور، سيتم توجيهك لمراسلة إدارة المبادرة عبر واتساب لتعيين كلمة مرور جديدة لحسابك. هل ترغب بالمتابعة؟');
            if (choice) {
                window.open(`https://wa.me/962791234567?text=${waMsg}`, '_blank');
            }
        });
    }

    // فحص الجلسة عند بدء التشغيل
    async function checkAuthSession() {
        try {
            const res = await fetch('/api/check_session');
            const data = await res.json();
            if (data.logged_in) {
                homeSection.classList.add('hidden');
                registerSection.classList.add('hidden');

                if (data.role === 'admin') {
                    adminDashboard.classList.remove('hidden');
                    resetAdminTabs();
                    tabVolunteersBtn.classList.add('active');
                    sectionVolunteersView.classList.remove('hidden');
                    triggerLoadVolunteers();
                    updateStats();
                } else if (data.role === 'volunteer') {
                    setupVolunteerDashboard(data.volunteer);
                }
            }
        } catch (err) {
            console.error('Session check failed:', err);
        }
    }

    // إعداد واجهة المتطوع
    function setupVolunteerDashboard(vol) {
        currentVolunteer = vol;
        document.getElementById('hub-volunteer-name').textContent = vol.name;
        document.getElementById('profile-display-name').textContent = vol.name;
        document.getElementById('profile-display-rank').textContent = vol.rank;
        document.getElementById('profile-display-events').textContent = vol.events_count;
        document.getElementById('profile-display-warnings').textContent = vol.warnings_count;
        document.getElementById('profile-display-status').textContent = 'حالة الطلب: ' + vol.status;
        document.getElementById('edit-profile-phone').value = vol.phone;
        document.getElementById('edit-profile-location').value = vol.location;

        const defaultAvatar = document.getElementById('profile-default-avatar');
        const imgAvatar = document.getElementById('profile-image-avatar');
        if (vol.avatar_url && vol.avatar_url.trim()) {
            imgAvatar.src = vol.avatar_url;
            imgAvatar.classList.remove('hidden');
            defaultAvatar.classList.add('hidden');
        } else {
            imgAvatar.classList.add('hidden');
            defaultAvatar.classList.remove('hidden');
        }

        const leaderBadge = document.getElementById('profile-leader-badge');
        if (vol.is_leader) {
            leaderBadge.textContent = '⭐ ' + (vol.leadership_role || 'قائد ميداني');
            leaderBadge.classList.remove('hidden');
        } else {
            leaderBadge.classList.add('hidden');
        }

        volunteerHubSection.classList.remove('hidden');
        resetHubTabs();
        hubTabFeed.classList.add('active');
        hubViewFeed.classList.remove('hidden');
        loadHubPosts();
    }

    // جلب معلومات النبذة والإعلان
    async function loadSiteInfo() {
        try {
            const res = await fetch('/api/site_info');
            const data = await res.json();
            if (data.success) {
                const aboutP = document.getElementById('display-about-text');
                if (aboutP) aboutP.textContent = data.about_text;

                const annDiv = document.getElementById('global-announcement');
                if (annDiv) {
                    if (data.announcement && data.announcement.trim()) {
                        annDiv.textContent = '📢 إعلان: ' + data.announcement;
                        annDiv.classList.remove('hidden');
                    } else {
                        annDiv.classList.add('hidden');
                    }
                }

                const editAbout = document.getElementById('admin-edit-about');
                const editAnn = document.getElementById('admin-edit-announcement');
                if (editAbout) editAbout.value = data.about_text;
                if (editAnn) editAnn.value = data.announcement || '';
            }
        } catch (err) {
            console.error('Site Info Error:', err);
        }
    }

    // تحديث إحصائيات الإدارة
    async function updateStats() {
        try {
            const res = await fetch('/api/stats');
            if (res.status === 401 || res.status === 403) return;
            const data = await res.json();
            if (data.success) {
                document.getElementById('stat-total').textContent = data.stats.total;
                document.getElementById('stat-accepted').textContent = data.stats.accepted;
                document.getElementById('stat-pending').textContent = data.stats.pending;
                document.getElementById('stat-events').textContent = data.stats.events;
            }
        } catch (err) {
            console.error('Stats error:', err);
        }
    }

    // تبويبات الإدارة
    const tabVolunteersBtn = document.getElementById('tab-volunteers-btn');
    const tabEventsBtn = document.getElementById('tab-events-btn');
    const tabContentBtn = document.getElementById('tab-content-btn');
    const tabLeadersBtn = document.getElementById('tab-leaders-btn');

    const sectionVolunteersView = document.getElementById('section-volunteers-view');
    const sectionEventsView = document.getElementById('section-events-view');
    const sectionContentView = document.getElementById('section-content-view');
    const sectionLeadersView = document.getElementById('section-leaders-view');

    function resetAdminTabs() {
        [tabVolunteersBtn, tabEventsBtn, tabContentBtn, tabLeadersBtn].forEach(b => b && b.classList.remove('active'));
        [sectionVolunteersView, sectionEventsView, sectionContentView, sectionLeadersView].forEach(s => s && s.classList.add('hidden'));
    }

    if (tabVolunteersBtn) {
        tabVolunteersBtn.addEventListener('click', () => {
            resetAdminTabs();
            tabVolunteersBtn.classList.add('active');
            sectionVolunteersView.classList.remove('hidden');
            triggerLoadVolunteers();
        });
    }

    if (tabEventsBtn) {
        tabEventsBtn.addEventListener('click', () => {
            resetAdminTabs();
            tabEventsBtn.classList.add('active');
            sectionEventsView.classList.remove('hidden');
            loadEvents();
        });
    }

    if (tabContentBtn) {
        tabContentBtn.addEventListener('click', () => {
            resetAdminTabs();
            tabContentBtn.classList.add('active');
            sectionContentView.classList.remove('hidden');
            loadAdminPosts();
        });
    }

    if (tabLeadersBtn) {
        tabLeadersBtn.addEventListener('click', () => {
            resetAdminTabs();
            tabLeadersBtn.classList.add('active');
            sectionLeadersView.classList.remove('hidden');
            loadLeaders();
        });
    }

    // تبويبات منصة المتطوع
    const hubTabFeed = document.getElementById('hub-tab-feed');
    const hubTabEvents = document.getElementById('hub-tab-events');
    const hubTabProfile = document.getElementById('hub-tab-profile');
    const hubViewFeed = document.getElementById('hub-view-feed');
    const hubViewEvents = document.getElementById('hub-view-events');
    const hubViewProfile = document.getElementById('hub-view-profile');

    function resetHubTabs() {
        [hubTabFeed, hubTabEvents, hubTabProfile].forEach(b => b && b.classList.remove('active'));
        [hubViewFeed, hubViewEvents, hubViewProfile].forEach(v => v && v.classList.add('hidden'));
    }

    if (hubTabFeed) {
        hubTabFeed.addEventListener('click', () => {
            resetHubTabs();
            hubTabFeed.classList.add('active');
            hubViewFeed.classList.remove('hidden');
            loadHubPosts();
        });
    }

    if (hubTabEvents) {
        hubTabEvents.addEventListener('click', () => {
            resetHubTabs();
            hubTabEvents.classList.add('active');
            hubViewEvents.classList.remove('hidden');
            loadHubEvents();
        });
    }

    if (hubTabProfile) {
        hubTabProfile.addEventListener('click', () => {
            resetHubTabs();
            hubTabProfile.classList.add('active');
            hubViewProfile.classList.remove('hidden');
        });
    }

    if (registerBtn) {
        registerBtn.addEventListener('click', () => {
            homeSection.classList.add('hidden');
            registerSection.classList.remove('hidden');
        });
    }

    if (backBtn) {
        backBtn.addEventListener('click', () => {
            registerSection.classList.add('hidden');
            homeSection.classList.remove('hidden');
        });
    }

    if (profileBtn) {
        profileBtn.addEventListener('click', () => {
            if (currentVolunteer) {
                homeSection.classList.add('hidden');
                registerSection.classList.add('hidden');
                adminDashboard.classList.add('hidden');
                volunteerHubSection.classList.remove('hidden');
                resetHubTabs();
                hubTabProfile.classList.add('active');
                hubViewProfile.classList.remove('hidden');
            } else {
                loginModal.classList.remove('hidden');
            }
        });
    }

    document.querySelectorAll('.logout-trigger-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            await fetch('/api/logout', { method: 'POST' });
            currentVolunteer = null;
            adminDashboard.classList.add('hidden');
            volunteerHubSection.classList.add('hidden');
            homeSection.classList.remove('hidden');
        });
    });

    const expCheckbox = document.getElementById('exp-checkbox');
    const expDetails = document.getElementById('exp-details');
    if (expCheckbox && expDetails) {
        expCheckbox.addEventListener('change', () => {
            if (expCheckbox.checked) {
                expDetails.classList.remove('hidden');
            } else {
                expDetails.classList.add('hidden');
            }
        });
    }

    if (loginBtn && loginModal) {
        loginBtn.addEventListener('click', () => loginModal.classList.remove('hidden'));
    }
    if (closeLogin) {
        closeLogin.addEventListener('click', () => loginModal.classList.add('hidden'));
    }

    // إرسال نموذج التسجيل
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const skills = [];
            document.querySelectorAll('input[name="skill"]:checked').forEach((cb) => {
                skills.push(cb.value);
            });

            const formData = {
                full_name: document.getElementById('reg-name').value,
                phone: document.getElementById('reg-phone').value,
                email: document.getElementById('reg-email').value,
                password: document.getElementById('reg-password').value,
                age: document.getElementById('reg-age').value,
                gender: document.querySelector('input[name="gender"]:checked').value,
                location: document.getElementById('reg-location').value,
                q_pressure: document.getElementById('reg-pressure').value,
                q_punctuality: document.getElementById('reg-punctuality').value,
                q_conflict: document.getElementById('reg-conflict').value,
                q_workstyle: document.getElementById('reg-workstyle').value,
                skills: skills,
                experience_details: document.getElementById('exp-details').value
            };

            try {
                const response = await fetch('/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });

                const result = await response.json();
                if (result.success) {
                    alert('تم إرسال طلب الانضمام بنجاح!');
                    registerForm.reset();
                    registerSection.classList.add('hidden');
                    homeSection.classList.remove('hidden');
                } else {
                    alert('حدث خطأ: ' + result.message);
                }
            } catch (error) {
                alert('فشل الاتصال بالخادم.');
            }
        });
    }

    // حفظ التعديلات والملف الشخصي
    const saveProfileBtn = document.getElementById('save-profile-btn');
    if (saveProfileBtn) {
        saveProfileBtn.addEventListener('click', async () => {
            const phone = document.getElementById('edit-profile-phone').value;
            const location = document.getElementById('edit-profile-location').value;
            const avatarInput = document.getElementById('edit-profile-avatar');
            let avatar_url = currentVolunteer ? (currentVolunteer.avatar_url || '') : '';

            if (avatarInput && avatarInput.files.length > 0) {
                const formData = new FormData();
                formData.append('file', avatarInput.files[0]);
                try {
                    const upRes = await fetch('/api/upload', { method: 'POST', body: formData });
                    const upData = await upRes.json();
                    if (upData.success) {
                        avatar_url = upData.file_url;
                    }
                } catch (err) {
                    alert('فشل رفع الصورة الشخصية.');
                }
            }

            const res = await fetch('/api/volunteer/update_profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone, location, avatar_url })
            });
            const data = await res.json();
            alert(data.message);
            if (currentVolunteer) {
                currentVolunteer.phone = phone;
                currentVolunteer.location = location;
                currentVolunteer.avatar_url = avatar_url;
                setupVolunteerDashboard(currentVolunteer);
            }
        });
    }

    // إعادة تعيين كلمة المرور للمتطوع
    window.resetVolunteerPassword = async (vId) => {
        const newPassword = prompt('أدخل كلمة المرور الجديدة لهذا المتطوع:');
        if (!newPassword) return;

        try {
            const res = await fetch(`/api/volunteer/${vId}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'reset_password', new_password: newPassword })
            });
            const data = await res.json();
            alert(data.message);
        } catch (err) {
            alert('حدث خطأ أثناء تغيير كلمة المرور.');
        }
    };

    // إجراءات الإدارة على المتطوعين
    window.handleVolunteerAction = async (vId, action) => {
        if (action === 'delete' && !confirm('هل أنت متأكد من حذف هذا المتطوع نهائياً؟')) {
            return;
        }

        let bodyData = { action };
        if (action === 'save_notes') {
            const noteText = document.getElementById(`notes-${vId}`).value;
            bodyData.notes = noteText;
        }

        try {
            const res = await fetch(`/api/volunteer/${vId}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bodyData)
            });
            const data = await res.json();
            if (data.success) {
                triggerLoadVolunteers();
                updateStats();
            } else {
                alert(data.message);
            }
        } catch (err) {
            alert('حدث خطأ أثناء تنفيذ الإجراء.');
        }
    };

    const volunteerSearchInput = document.getElementById('volunteer-search-input');
    const skillFilterSelect = document.getElementById('skill-filter-select');

    function triggerLoadVolunteers() {
        const skill = skillFilterSelect ? skillFilterSelect.value : '';
        const search = volunteerSearchInput ? volunteerSearchInput.value : '';
        loadVolunteers(skill, search);
    }

    function formatPhoneForWhatsApp(phone) {
        let clean = phone.replace(/[^0-9]/g, '');
        if (clean.startsWith('07')) {
            clean = '962' + clean.substring(1);
        } else if (clean.startsWith('7') && clean.length === 9) {
            clean = '962' + clean;
        }
        return clean;
    }

    // جلب قائمة المتطوعين للإدارة
    async function loadVolunteers(skill = '', search = '') {
        const listContainer = document.getElementById('volunteers-list');
        listContainer.innerHTML = '<p style="text-align:center;">جاري جلب البيانات...</p>';

        try {
            const res = await fetch(`/api/volunteers?skill=${encodeURIComponent(skill)}&search=${encodeURIComponent(search)}`);
            if (res.status === 401 || res.status === 403) {
                listContainer.innerHTML = '<p style="text-align:center; color:red;">غير مصرح لك بعرض هذه البيانات.</p>';
                return;
            }
            const data = await res.json();

            if (data.success) {
                currentLoadedVolunteers = data.volunteers;
                listContainer.innerHTML = '';
                if (data.volunteers.length === 0) {
                    listContainer.innerHTML = '<p style="text-align:center; padding: 20px;">لا توجد نتائج مطابقة.</p>';
                    return;
                }

                data.volunteers.forEach(v => {
                    const waPhone = formatPhoneForWhatsApp(v.phone);
                    const waMessage = encodeURIComponent(`مرحباً ${v.full_name}، نتواصل معك من إدارة مبادرة لمتنا بصمة بخصوص انضمامك لفريقنا.`);
                    const waLink = `https://wa.me/${waPhone}?text=${waMessage}`;

                    const avatarHtml = v.avatar_url 
                        ? `<img src="${v.avatar_url}" class="admin-volunteer-thumb" alt="${v.full_name}">` 
                        : `<span style="font-size:32px;">👤</span>`;

                    const card = document.createElement('div');
                    card.className = 'volunteer-card';
                    card.innerHTML = `
                        <div class="card-header">
                            <div style="display:flex; align-items:center; gap:10px;">
                                ${avatarHtml}
                                <div>
                                    <h3 style="margin:0;">${v.full_name} (رقم: ${v.id}) - ${v.age} سنة</h3>
                                    ${v.is_leader ? `<span class="leader-tag" style="margin-top:4px;">⭐ ${v.leadership_role || 'قائد ميداني'}</span>` : ''}
                                </div>
                            </div>
                            <span class="status-badge status-${v.status}">${v.status}</span>
                        </div>
                        <p><strong>📞 الهاتف:</strong> ${v.phone} | <strong>📧 البريد:</strong> ${v.email}</p>
                        <p><strong>📍 مكان السكن:</strong> ${v.location}</p>
                        <p><strong>🛠️ المهارات:</strong> ${v.skills.join(' - ') || 'لا توجد'}</p>
                        ${v.experience_details ? `<p><strong>الخبرة السابقة:</strong> ${v.experience_details}</p>` : ''}
                        
                        <div class="behavior-box">
                            <strong>التقييم السلوكي:</strong>
                            <p>• الضغط: ${v.behavior.pressure}</p>
                            <p>• الالتزام: ${v.behavior.punctuality}</p>
                            <p>• الخلافات: ${v.behavior.conflict}</p>
                            <p>• نمط العمل: ${v.behavior.workstyle}</p>
                        </div>

                        <div style="margin-top: 8px;">
                            <input type="text" id="notes-${v.id}" value="${v.admin_notes}" placeholder="ملاحظات سرية للإدارة..." class="input-field" style="margin-bottom: 4px;">
                            <button class="action-btn" style="background:#0f172a; color:#fff;" onclick="handleVolunteerAction(${v.id}, 'save_notes')">💾 حفظ الملاحظة</button>
                        </div>

                        <p style="margin-top:8px;"><strong>الرتبة:</strong> ${v.rank} | <strong>الفعاليات:</strong> ${v.events_count} | <strong>الإنذارات:</strong> ${v.warnings_count}</p>
                        
                        <div class="card-actions">
                            <a href="${waLink}" target="_blank" class="action-btn btn-whatsapp">💬 واتساب مباشر</a>
                            <button class="action-btn btn-accept" onclick="handleVolunteerAction(${v.id}, 'accept')">قبول</button>
                            <button class="action-btn btn-reject" onclick="handleVolunteerAction(${v.id}, 'reject')">رفض</button>
                            <button class="action-btn btn-event" onclick="handleVolunteerAction(${v.id}, 'add_event')">+ فعالية (ترقية)</button>
                            <button class="action-btn btn-warn" onclick="handleVolunteerAction(${v.id}, 'add_warning')">+ إنذار</button>
                            <button class="action-btn" style="background:#475569; color:#fff;" onclick="resetVolunteerPassword(${v.id})">🔑 تعيين كلمة السر</button>
                            <button class="action-btn btn-del" onclick="handleVolunteerAction(${v.id}, 'delete')">حذف</button>
                        </div>
                    `;
                    listContainer.appendChild(card);
                });
            }
        } catch (err) {
            listContainer.innerHTML = '<p style="text-align:center; color:red;">تعذر تحميل القائمة.</p>';
        }
    }

    if (copyPhonesBtn) {
        copyPhonesBtn.addEventListener('click', () => {
            if (!currentLoadedVolunteers || currentLoadedVolunteers.length === 0) {
                alert('لا توجد أرقام لنسخها حالياً.');
                return;
            }
            const phoneList = currentLoadedVolunteers.map(v => v.phone).filter(p => p).join('\n');
            navigator.clipboard.writeText(phoneList).then(() => {
                alert(`تم نسخ (${currentLoadedVolunteers.length}) رقم إلى الحافظة بنجاح!`);
            }).catch(() => {
                alert('فشل النسخ التلقائي.');
            });
        });
    }

    if (volunteerSearchInput) {
        volunteerSearchInput.addEventListener('input', () => {
            triggerLoadVolunteers();
        });
    }

    if (skillFilterSelect) {
        skillFilterSelect.addEventListener('change', () => {
            triggerLoadVolunteers();
        });
    }

    // إنشاء الفعاليات
    const createEventForm = document.getElementById('create-event-form');
    if (createEventForm) {
        createEventForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const title = document.getElementById('event-title').value;
            const location = document.getElementById('event-location').value;
            const event_date = document.getElementById('event-date').value;

            try {
                const res = await fetch('/api/events', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, location, event_date })
                });
                const data = await res.json();
                if (data.success) {
                    alert('تم إنشاء الفعالية بنجاح!');
                    createEventForm.reset();
                    loadEvents();
                    updateStats();
                }
            } catch (err) {
                alert('فشل إنشاء الفعالية.');
            }
        });
    }

    // جلب الفعاليات
    async function loadEvents() {
        const eventsList = document.getElementById('events-list');
        eventsList.innerHTML = '<p style="text-align:center;">جاري جلب الفعاليات...</p>';

        try {
            const res = await fetch('/api/events');
            const data = await res.json();

            if (data.success) {
                eventsList.innerHTML = '';
                if (data.events.length === 0) {
                    eventsList.innerHTML = '<p style="text-align:center; padding: 20px;">لا توجد فعاليات مسجلة حالياً.</p>';
                    return;
                }

                data.events.forEach(e => {
                    const attendeesTags = e.attendees.length > 0 
                        ? e.attendees.map(a => `<span class="attendee-tag">👤 ${a.name} (#${a.id}) <button class="remove-attendee-btn" onclick="removeAttendee(${e.id}, ${a.id})">×</button></span>`).join(' ')
                        : '<span style="color:#888; font-size:13px;">لم يتم توثيق حضور أحد بعد.</span>';

                    const registeredTags = e.registered_volunteers.length > 0
                        ? e.registered_volunteers.map(r => `<span class="attendee-tag" style="background:#e0f2fe; color:#0369a1;">🙋‍♂️ ${r.name} (#${r.id})</span>`).join(' ')
                        : '<span style="color:#888; font-size:13px;">لا يوجد مسجلين مسبقاً.</span>';

                    const card = document.createElement('div');
                    card.className = 'volunteer-card';
                    card.innerHTML = `
                        <div class="card-header">
                            <h3>${e.title}</h3>
                            <span class="status-badge status-مقبول">حضور فعلي: ${e.attendees_count} | رغبة انضمام: ${e.registered_count}</span>
                        </div>
                        <p><strong>📍 المكان:</strong> ${e.location} | <strong>📅 التاريخ:</strong> ${e.event_date}</p>
                        
                        <div style="margin: 8px 0;">
                            <strong>المتطوعون الذين أبدوا رغبتهم بالانضمام:</strong>
                            <div class="attendees-wrap">${registeredTags}</div>
                        </div>

                        <div style="margin: 8px 0;">
                            <strong>قائمة الحضور الفعلي الموثق:</strong>
                            <div class="attendees-wrap">${attendeesTags}</div>
                        </div>
                        
                        <div class="card-actions">
                            <button class="action-btn btn-event" onclick="promptAttendance(${e.id})">+ توثيق حضور متطوع</button>
                            <a href="/api/export/event/${e.id}" class="action-btn export-btn" style="text-decoration:none; padding:5px 10px; font-size:12px;" download>📥 كشف الحضور (Excel)</a>
                            <button class="action-btn btn-del" onclick="deleteEvent(${e.id})">حذف الفعالية</button>
                        </div>
                    `;
                    eventsList.appendChild(card);
                });
            }
        } catch (err) {
            eventsList.innerHTML = '<p style="text-align:center; color:red;">تعذر تحميل الفعاليات.</p>';
        }
    }

    window.removeAttendee = async (eventId, volunteerId) => {
        if (!confirm('هل تريد إلغاء توثيق حضور هذا المتطوع؟')) return;
        const res = await fetch(`/api/event/${eventId}/remove_attendee`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ volunteer_id: volunteerId })
        });
        const data = await res.json();
        alert(data.message);
        loadEvents();
        updateStats();
    };

    window.deleteEvent = async (eventId) => {
        if (!confirm('هل أنت متأكد من حذف هذه الفعالية؟')) return;

        try {
            const res = await fetch(`/api/event/${eventId}/delete`, { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                loadEvents();
                updateStats();
            }
        } catch (err) {
            alert('حدث خطأ أثناء حذف الفعالية.');
        }
    };

    window.promptAttendance = async (eventId) => {
        const volunteerId = prompt('أدخل رقم المتطوع (ID) لتوثيق حضوره وترقيته:');
        if (!volunteerId) return;

        try {
            const res = await fetch(`/api/event/${eventId}/attend`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ volunteer_id: volunteerId })
            });
            const data = await res.json();
            alert(data.message);
            loadEvents();
            updateStats();
        } catch (err) {
            alert('حدث خطأ أثناء تسجيل الحضور.');
        }
    };

    // حفظ معلومات الموقع
    const saveSiteInfoBtn = document.getElementById('save-site-info-btn');
    if (saveSiteInfoBtn) {
        saveSiteInfoBtn.addEventListener('click', async () => {
            const about_text = document.getElementById('admin-edit-about').value;
            const announcement = document.getElementById('admin-edit-announcement').value;

            const res = await fetch('/api/site_info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ about_text, announcement })
            });
            const data = await res.json();
            alert(data.message);
            loadSiteInfo();
        });
    }

    // إنشاء المنشورات والتغطيات
    const createPostBtn = document.getElementById('create-post-btn');
    if (createPostBtn) {
        createPostBtn.addEventListener('click', async () => {
            const title = document.getElementById('post-title').value;
            const caption = document.getElementById('post-caption').value;
            const fileInput = document.getElementById('post-file-input');
            let media_url = document.getElementById('post-media-url').value;
            let media_type = 'text';

            if (!title) {
                alert('يرجى كتابة عنوان للمنشور');
                return;
            }

            if (fileInput && fileInput.files.length > 0) {
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);

                try {
                    const uploadRes = await fetch('/api/upload', {
                        method: 'POST',
                        body: formData
                    });
                    const uploadData = await uploadRes.json();
                    if (!uploadData.success) {
                        alert('فشل رفع الملف: ' + uploadData.message);
                        return;
                    }
                    media_url = uploadData.file_url;
                    media_type = uploadData.media_type;
                } catch (err) {
                    alert('حدث خطأ أثناء رفع الملف.');
                    return;
                }
            } else if (media_url.trim()) {
                media_type = (media_url.includes('youtube') || media_url.endsWith('.mp4')) ? 'video' : 'image';
            }

            const res = await fetch('/api/posts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, caption, media_type, media_url })
            });
            const data = await res.json();
            if (data.success) {
                alert(data.message);
                document.getElementById('post-title').value = '';
                document.getElementById('post-caption').value = '';
                document.getElementById('post-media-url').value = '';
                if (fileInput) fileInput.value = '';
                loadAdminPosts();
            }
        });
    }

    async function loadAdminPosts() {
        const list = document.getElementById('admin-posts-list');
        list.innerHTML = '<p style="text-align:center;">جاري جلب المنشورات...</p>';
        const res = await fetch('/api/posts');
        const data = await res.json();
        if (data.success) {
            list.innerHTML = '';
            if (data.posts.length === 0) {
                list.innerHTML = '<p style="text-align:center; padding:15px;">لا توجد منشورات حتى الآن.</p>';
                return;
            }
            data.posts.forEach(p => {
                const item = document.createElement('div');
                item.className = 'volunteer-card';
                item.innerHTML = `
                    <div class="card-header">
                        <h3>${p.title}</h3>
                        <span style="font-size:12px; color:#666;">${p.created_at}</span>
                    </div>
                    <p>${p.caption || ''}</p>
                    ${p.media_type === 'image' && p.media_url ? `<img src="${p.media_url}" style="max-width:100%; border-radius:6px; margin:8px 0;">` : ''}
                    ${p.media_type === 'video' && p.media_url ? `<p><a href="${p.media_url}" target="_blank">🔗 رابط الفيديو</a></p>` : ''}
                    <div class="card-actions">
                        <button class="action-btn btn-del" onclick="deletePost(${p.id})">حذف المنشور</button>
                    </div>
                `;
                list.appendChild(item);
            });
        }
    }

    window.deletePost = async (postId) => {
        if (!confirm('هل أنت متأكد من حذف هذا المنشور؟')) return;
        const res = await fetch(`/api/post/${postId}/delete`, { method: 'POST' });
        const data = await res.json();
        if (data.success) loadAdminPosts();
    };

    // الهيكل القيادي
    const assignLeaderBtn = document.getElementById('assign-leader-btn');
    if (assignLeaderBtn) {
        assignLeaderBtn.addEventListener('click', async () => {
            const vId = document.getElementById('leader-v-id').value;
            const role_title = document.getElementById('leader-role-title').value;

            if (!vId) {
                alert('أدخل رقم المتطوع');
                return;
            }

            const res = await fetch(`/api/volunteer/${vId}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'set_leadership', is_leader: true, role_title })
            });
            const data = await res.json();
            alert(data.message);
            document.getElementById('leader-v-id').value = '';
            document.getElementById('leader-role-title').value = '';
            loadLeaders();
        });
    }

    async function loadLeaders() {
        const list = document.getElementById('leaders-list');
        list.innerHTML = '<p style="text-align:center;">جاري جلب القادة...</p>';
        const res = await fetch('/api/volunteers');
        if (res.status === 401 || res.status === 403) return;
        const data = await res.json();
        if (data.success) {
            list.innerHTML = '';
            const leaders = data.volunteers.filter(v => v.is_leader);
            if (leaders.length === 0) {
                list.innerHTML = '<p style="text-align:center; padding:15px;">لا يوجد قادة معينون حالياً.</p>';
                return;
            }
            leaders.forEach(l => {
                const item = document.createElement('div');
                item.className = 'volunteer-card';
                item.innerHTML = `
                    <div class="card-header">
                        <h3>${l.full_name}</h3>
                        <span class="leader-tag">⭐ ${l.leadership_role || 'قائد ميداني'}</span>
                    </div>
                    <p><strong>الهاتف:</strong> ${l.phone} | <strong>الموقع:</strong> ${l.location}</p>
                    <p><strong>الفعاليات المنجزة:</strong> ${l.events_count}</p>
                    <div class="card-actions">
                        <button class="action-btn btn-del" onclick="revokeLeadership(${l.id})">إلغاء صفة القيادة</button>
                    </div>
                `;
                list.appendChild(item);
            });
        }
    }

    window.revokeLeadership = async (vId) => {
        if (!confirm('هل تريد إلغاء الصفة القيادية لهذا المتطوع؟')) return;
        const res = await fetch(`/api/volunteer/${vId}/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'set_leadership', is_leader: false, role_title: '' })
        });
        const data = await res.json();
        alert(data.message);
        loadLeaders();
    };

    // منصة المتطوع (Feed & Events)
    async function loadHubPosts() {
        const feed = document.getElementById('hub-posts-container');
        feed.innerHTML = '<p style="text-align:center;">جاري جلب الأخبار والتغطيات...</p>';
        const res = await fetch('/api/posts');
        const data = await res.json();
        if (data.success) {
            feed.innerHTML = '';
            if (data.posts.length === 0) {
                feed.innerHTML = '<p style="text-align:center; padding:30px; color:#666;">لا توجد منشورات أو تغطيات منشورة حالياً.</p>';
                return;
            }
            data.posts.forEach(p => {
                const postBox = document.createElement('div');
                postBox.className = 'post-card';
                postBox.innerHTML = `
                    <h3 class="post-title">${p.title}</h3>
                    <span class="post-date">📅 ${p.created_at}</span>
                    <p class="post-caption">${p.caption || ''}</p>
                    ${p.media_type === 'image' && p.media_url ? `<img src="${p.media_url}" class="post-media-img" alt="تغطية">` : ''}
                    ${p.media_type === 'video' && p.media_url ? `
                        <div class="post-video-container">
                            <a href="${p.media_url}" target="_blank" class="btn-primary" style="display:inline-block; margin-top:8px;">▶️ مشاهدة الفيديو / Reels</a>
                        </div>
                    ` : ''}
                `;
                feed.appendChild(postBox);
            });
        }
    }

    async function loadHubEvents() {
        const list = document.getElementById('hub-events-container');
        list.innerHTML = '<p style="text-align:center;">جاري جلب الفعاليات...</p>';
        const res = await fetch('/api/events');
        const data = await res.json();
        if (data.success) {
            list.innerHTML = '';
            if (data.events.length === 0) {
                list.innerHTML = '<p style="text-align:center; padding:20px;">لا توجد فعاليات قادمة متاحة حالياً.</p>';
                return;
            }
            data.events.forEach(e => {
                const isRegistered = currentVolunteer && e.registered_volunteers.some(r => r.id === currentVolunteer.id);

                const card = document.createElement('div');
                card.className = 'volunteer-card';
                card.innerHTML = `
                    <div class="card-header">
                        <h3>${e.title}</h3>
                        <span class="status-badge status-مقبول">📅 ${e.event_date}</span>
                    </div>
                    <p><strong>📍 الموقع:</strong> ${e.location}</p>
                    <p><strong>👥 المسجلون بالفعالية:</strong> ${e.registered_count} متطوع</p>
                    <div class="card-actions">
                        ${isRegistered 
                            ? `<span class="status-badge status-مقبول" style="padding:6px 12px;">✅ تم تسجيل اهتمامك</span>` 
                            : `<button class="action-btn btn-accept" onclick="registerInterest(${e.id})">🙋‍♂️ تسجيل اهتمامي بالانضمام</button>`}
                    </div>
                `;
                list.appendChild(card);
            });
        }
    }

    window.registerInterest = async (eventId) => {
        const res = await fetch(`/api/event/${eventId}/register_interest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        alert(data.message);
        loadHubEvents();
    };

    // تسجيل الدخول
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;

            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                const data = await res.json();

                if (data.success) {
                    loginModal.classList.add('hidden');
                    homeSection.classList.add('hidden');

                    if (data.role === 'admin') {
                        showToast(data.title, data.name);
                        adminDashboard.classList.remove('hidden');
                        resetAdminTabs();
                        tabVolunteersBtn.classList.add('active');
                        sectionVolunteersView.classList.remove('hidden');
                        triggerLoadVolunteers();
                        updateStats();
                    } else {
                        setupVolunteerDashboard(data.volunteer);
                    }
                    loginForm.reset();
                } else {
                    alert(data.message || 'بيانات الدخول غير صحيحة.');
                }
            } catch (err) {
                alert('فشل الاتصال بالخادم.');
            }
        });
    }

    loadSiteInfo();
    checkAuthSession();
});