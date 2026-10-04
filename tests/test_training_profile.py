
def test_profile_training_integration_progress(client, test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule, TrainingProgress
    with test_app.app_context():
        c = TrainingCourse(title='Profile_Course1', is_published=True)
        db.session.add(c)
        db.session.commit()
        
        m = TrainingModule(course_id=c.id, title='Profile_Mod1', is_published=True)
        db.session.add(m)
        db.session.commit()
        
        # Mark completed
        db.session.add(TrainingProgress(volunteer_id=volunteer1, module_id=m.id, is_completed=True))
        db.session.commit()
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    resp = client.get('/profile')
    html = resp.data.decode('utf-8')
    assert resp.status_code == 200
    assert 'الأكاديمية والتدريب' in html
    assert 'Profile_Course1' in html
    assert '100%' in html
    assert 'مكتمل' in html

def test_profile_training_integration_hides_unpublished(client, test_app, volunteer1):
    from app import db, TrainingCourse
    with test_app.app_context():
        c = TrainingCourse(title='Hidden_Unpub_Profile', is_published=False)
        db.session.add(c)
        db.session.commit()
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    resp = client.get('/profile')
    html = resp.data.decode('utf-8')
    assert 'Hidden_Unpub_Profile' not in html

def test_training_detail_shows_progress(client, test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule
    with test_app.app_context():
        c = TrainingCourse(title='Detail_Prog_Course', is_published=True)
        db.session.add(c)
        db.session.commit()
        
        m1 = TrainingModule(course_id=c.id, title='DMod1', is_published=True)
        m2 = TrainingModule(course_id=c.id, title='DMod2', is_published=True)
        db.session.add_all([m1, m2])
        db.session.commit()
        c_id = c.id
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    # 0 completed
    resp = client.get(f'/training/{c_id}')
    html = resp.data.decode('utf-8')
    assert 'نسبة الإنجاز' in html
    assert '0 / 2' in html
    assert '0%' in html

def test_training_detail_isolation(client, test_app, volunteer1, volunteer2):
    from app import db, TrainingCourse, TrainingModule, TrainingProgress
    with test_app.app_context():
        c = TrainingCourse(title='Iso_Course', is_published=True)
        db.session.add(c)
        db.session.commit()
        m = TrainingModule(course_id=c.id, title='Iso_Mod', is_published=True)
        db.session.add(m)
        db.session.commit()
        c_id = c.id
        
        # Vol1 completes
        db.session.add(TrainingProgress(volunteer_id=volunteer1, module_id=m.id, is_completed=True))
        db.session.commit()
        
    # Vol 2 checks
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer2
        
    resp = client.get(f'/training/{c_id}')
    html = resp.data.decode('utf-8')
    assert '0 / 1' in html  # Vol 2 sees 0
    assert 'مكتمل' not in html
