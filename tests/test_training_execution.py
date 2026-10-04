import os
import sys

os.environ.setdefault('FLASK_ENV', 'development')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_module_detail_access(client, test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule
    with test_app.app_context():
        c = TrainingCourse(title='Course1', is_published=True)
        db.session.add(c)
        db.session.commit()
        m = TrainingModule(title='Mod1', course_id=c.id, is_published=True, content_type='VIDEO', content_url='https://example.com/video')
        db.session.add(m)
        db.session.commit()
        c_id = c.id
        m_id = m.id
        
    # Anonymous -> Redirect
    resp = client.get(f'/training/{c_id}/module/{m_id}')
    assert resp.status_code == 302
    
    # Authenticated -> 200
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
    resp = client.get(f'/training/{c_id}/module/{m_id}')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Mod1' in html
    assert 'محتوى مرئي' in html

def test_module_detail_unpublished(client, test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule
    with test_app.app_context():
        c = TrainingCourse(title='Course2', is_published=True)
        db.session.add(c)
        db.session.commit()
        m = TrainingModule(title='Mod2', course_id=c.id, is_published=False)
        db.session.add(m)
        db.session.commit()
        c_id = c.id
        m_id = m.id
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
    resp = client.get(f'/training/{c_id}/module/{m_id}')
    assert resp.status_code == 404

def test_module_detail_wrong_course(client, test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule
    with test_app.app_context():
        c1 = TrainingCourse(title='Course3A', is_published=True)
        c2 = TrainingCourse(title='Course3B', is_published=True)
        db.session.add_all([c1, c2])
        db.session.commit()
        m = TrainingModule(title='Mod3', course_id=c1.id, is_published=True)
        db.session.add(m)
        db.session.commit()
        c2_id = c2.id
        m_id = m.id
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
    resp = client.get(f'/training/{c2_id}/module/{m_id}')
    assert resp.status_code == 404

def test_module_rendering_safe_url(client, test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule
    with test_app.app_context():
        c = TrainingCourse(title='Course4', is_published=True)
        db.session.add(c)
        db.session.commit()
        m_safe = TrainingModule(title='Mod4S', course_id=c.id, is_published=True, content_type='DOCUMENT', content_url='https://example.com/doc.pdf')
        m_unsafe = TrainingModule(title='Mod4U', course_id=c.id, is_published=True, content_type='DOCUMENT', content_url='javascript:alert(1)')
        db.session.add_all([m_safe, m_unsafe])
        db.session.commit()
        c_id = c.id
        ms_id = m_safe.id
        mu_id = m_unsafe.id
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    resp_safe = client.get(f'/training/{c_id}/module/{ms_id}')
    assert 'href="https://example.com/doc.pdf"' in resp_safe.data.decode('utf-8')
    
    resp_unsafe = client.get(f'/training/{c_id}/module/{mu_id}')
    assert 'href="javascript:alert(1)"' not in resp_unsafe.data.decode('utf-8')

def test_module_completion_idempotency_and_isolation(client, test_app, volunteer1, volunteer2):
    from app import db, TrainingCourse, TrainingModule, TrainingProgress, Volunteer, HourLedger
    with test_app.app_context():
        # Make sure WTF CSRF is bypassed for testing or we send it
        test_app.config['WTF_CSRF_ENABLED'] = False
        
        c = TrainingCourse(title='Course5', is_published=True)
        db.session.add(c)
        db.session.commit()
        m = TrainingModule(title='Mod5', course_id=c.id, is_published=True)
        db.session.add(m)
        db.session.commit()
        c_id = c.id
        m_id = m.id
        
        v1_hours = db.session.query(db.func.sum(HourLedger.hours)).filter_by(volunteer_id=volunteer1).scalar() or 0
        v2_hours = db.session.query(db.func.sum(HourLedger.hours)).filter_by(volunteer_id=volunteer2).scalar() or 0
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    # Mark complete
    resp = client.post(f'/training/{c_id}/module/{m_id}/complete', follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'تم الإكمال' in html
    
    # Mark complete AGAIN (idempotent)
    resp = client.post(f'/training/{c_id}/module/{m_id}/complete', follow_redirects=True)
    assert resp.status_code == 200
    
    with test_app.app_context():
        progs = TrainingProgress.query.filter_by(volunteer_id=volunteer1, module_id=m_id).all()
        assert len(progs) == 1
        assert progs[0].is_completed is True
        
        # Check hour ledger didn't change
        assert db.session.query(db.func.sum(HourLedger.hours)).filter_by(volunteer_id=volunteer1).scalar() or 0 == v1_hours
        
        # Check volunteer2 wasn't affected
        prog2 = TrainingProgress.query.filter_by(volunteer_id=volunteer2, module_id=m_id).first()
        assert prog2 is None
        
        # Re-enable CSRF
        test_app.config['WTF_CSRF_ENABLED'] = True


def test_module_completion_requires_csrf(client, test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule
    with test_app.app_context():
        c = TrainingCourse(title='Course6', is_published=True)
        db.session.add(c)
        db.session.commit()
        m = TrainingModule(title='Mod6', course_id=c.id, is_published=True)
        db.session.add(m)
        db.session.commit()
        c_id = c.id
        m_id = m.id
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    # Attempt to POST without CSRF token (default in test_app is WTF_CSRF_ENABLED=False usually, but we enable it here)
    test_app.config['WTF_CSRF_ENABLED'] = True
    
    resp = client.post(f'/training/{c_id}/module/{m_id}/complete')
    # Should get a 400 Bad Request because of missing CSRF token
    assert resp.status_code == 400
    
    test_app.config['WTF_CSRF_ENABLED'] = False

def test_module_completion_hides_internal_exceptions(client, test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule
    with test_app.app_context():
        c = TrainingCourse(title='Course_Err', is_published=True)
        db.session.add(c)
        db.session.commit()
        m = TrainingModule(title='Mod_Err', course_id=c.id, is_published=True)
        db.session.add(m)
        db.session.commit()
        c_id = c.id
        m_id = m.id
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    # Mock db.session.commit to throw a generic Exception
    original_commit = db.session.commit
    def mock_commit(*args, **kwargs):
        raise Exception("RAW_DATABASE_CREDENTIALS_AND_SQL_QUERY_INFO_LEAK")
    
    test_app.config['WTF_CSRF_ENABLED'] = False
    
    db.session.commit = mock_commit
    try:
        resp = client.post(f'/training/{c_id}/module/{m_id}/complete', follow_redirects=True)
    finally:
        db.session.commit = original_commit
        
    html = resp.data.decode('utf-8')
    assert "RAW_DATABASE_CREDENTIALS" not in html
    assert "حدث خطأ غير متوقع" in html

def test_module_completion_concurrency_integrity_recovery_success(client, test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule, TrainingProgress
    from sqlalchemy.exc import IntegrityError
    from datetime import datetime
    with test_app.app_context():
        c = TrainingCourse(title='Course_Race1', is_published=True)
        db.session.add(c)
        db.session.commit()
        m = TrainingModule(title='Mod_Race1', course_id=c.id, is_published=True)
        db.session.add(m)
        db.session.commit()
        c_id = c.id
        m_id = m.id
        
        # PRE-CREATE the completed row to simulate another request beating us to the punch
        # We must insert it directly into DB so that when rollback happens, it's there
        prog = TrainingProgress(volunteer_id=volunteer1, module_id=m_id, is_completed=True, completed_at=datetime.utcnow())
        db.session.add(prog)
        db.session.commit()
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    original_commit = db.session.commit
    def mock_commit(*args, **kwargs):
        raise IntegrityError("UNIQUE constraint failed", orig=None, params=None)
    
    test_app.config['WTF_CSRF_ENABLED'] = False
    db.session.commit = mock_commit
    try:
        resp = client.post(f'/training/{c_id}/module/{m_id}/complete', follow_redirects=True)
    finally:
        db.session.commit = original_commit
        
    # The service should catch IntegrityError, rollback, query the DB, find the row is complete, and return Success
    html = resp.data.decode('utf-8')
    assert "تم إكمال الوحدة بنجاح" in html

def test_module_completion_concurrency_integrity_recovery_failure(client, test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule
    from sqlalchemy.exc import IntegrityError
    with test_app.app_context():
        c = TrainingCourse(title='Course_Race2', is_published=True)
        db.session.add(c)
        db.session.commit()
        m = TrainingModule(title='Mod_Race2', course_id=c.id, is_published=True)
        db.session.add(m)
        db.session.commit()
        c_id = c.id
        m_id = m.id
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    original_commit = db.session.commit
    def mock_commit(*args, **kwargs):
        raise IntegrityError("Some other FK constraint failed", orig=None, params=None)
    
    test_app.config['WTF_CSRF_ENABLED'] = False
    db.session.commit = mock_commit
    try:
        resp = client.post(f'/training/{c_id}/module/{m_id}/complete', follow_redirects=True)
    finally:
        db.session.commit = original_commit
        
    # The service should catch IntegrityError, rollback, query the DB, find NO completed row, and return safe generic error
    html = resp.data.decode('utf-8')
    assert "حدث خطأ غير متوقع" in html
    assert "تم إكمال الوحدة بنجاح" not in html
    assert "Some other FK constraint failed" not in html
