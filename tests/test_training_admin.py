import os
import sys
import pytest

os.environ.setdefault('FLASK_ENV', 'development')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, TrainingCourse, TrainingModule, TrainingProgress

@pytest.fixture
def client(test_app):
    with test_app.test_client() as client:
        yield client

def test_admin_create_course(client, test_app):
    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'
    
    resp = client.post('/admin/training/create', data={
        'title': 'New Admin Course',
        'description': 'Admin Desc'
    }, follow_redirects=True)
    assert resp.status_code == 200
    
    with test_app.app_context():
        c = TrainingCourse.query.filter_by(title='New Admin Course').first()
        assert c is not None
        assert c.description == 'Admin Desc'
        assert c.is_published is False

def test_admin_edit_course(client, test_app):
    with test_app.app_context():
        c = TrainingCourse(title='Old Title')
        db.session.add(c)
        db.session.commit()
        cid = c.id

    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'
    
    resp = client.post(f'/admin/training/{cid}/edit', data={
        'title': 'New Title',
        'description': 'New Desc',
        'cover_image_url': 'http://image'
    }, follow_redirects=True)
    
    with test_app.app_context():
        c = TrainingCourse.query.get(cid)
        assert c.title == 'New Title'
        assert c.description == 'New Desc'
        assert c.cover_image_url == 'http://image'

def test_admin_toggle_course(client, test_app):
    with test_app.app_context():
        c = TrainingCourse(title='Toggle Course')
        db.session.add(c)
        db.session.commit()
        cid = c.id

    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'
    
    client.post(f'/admin/training/{cid}/toggle', follow_redirects=True)
    with test_app.app_context():
        assert TrainingCourse.query.get(cid).is_published is True
    
    client.post(f'/admin/training/{cid}/toggle', follow_redirects=True)
    with test_app.app_context():
        assert TrainingCourse.query.get(cid).is_published is False

def test_admin_create_edit_delete_module(client, test_app):
    with test_app.app_context():
        c = TrainingCourse(title='Course for Mod')
        db.session.add(c)
        db.session.commit()
        cid = c.id

    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'
    
    # Create module
    client.post(f'/admin/training/{cid}/modules/create', data={
        'title': 'New Mod',
        'content_type': 'VIDEO',
        'position': '1'
    }, follow_redirects=True)
    
    with test_app.app_context():
        m = TrainingModule.query.filter_by(title='New Mod').first()
        assert m is not None
        assert m.content_type == 'VIDEO'
        assert m.position == 1
        mid = m.id

    # Edit module
    client.post(f'/admin/training/modules/{mid}/edit', data={
        'title': 'Edited Mod',
        'content_type': 'TEXT',
        'position': '2'
    }, follow_redirects=True)
    
    with test_app.app_context():
        m = TrainingModule.query.get(mid)
        assert m.title == 'Edited Mod'
        assert m.content_type == 'TEXT'
        assert m.position == 2

    # Delete module
    client.post(f'/admin/training/modules/{mid}/delete', follow_redirects=True)
    with test_app.app_context():
        assert TrainingModule.query.get(mid) is None

def test_course_admin_requires_auth(client):
    resp = client.post('/admin/training/create', data={'title': 'Hacker'})
    assert resp.status_code in (302, 403)
    if resp.status_code == 302:
        assert '/admin' not in resp.headers.get('Location', '')

def test_course_admin_rejects_volunteer(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 999
    resp = client.post('/admin/training/create', data={'title': 'Hacker'})
    assert resp.status_code in (302, 403)

def test_course_admin_rejects_leader(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 999
        sess['is_leader'] = True
    resp = client.post('/admin/training/create', data={'title': 'Hacker'})
    assert resp.status_code in (302, 403)

def test_deleting_course_clears_modules_and_progress(client, test_app):
    from app import Volunteer
    with test_app.app_context():
        c = TrainingCourse(title='Course to delete')
        db.session.add(c)
        db.session.commit()
        cid = c.id
        
        m = TrainingModule(title='Mod', course_id=cid)
        db.session.add(m)
        db.session.commit()
        mid = m.id
        
        v = Volunteer(name='V', email='v@v.v', phone='1234', password_hash='x')
        db.session.add(v)
        db.session.commit()
        
        prog = TrainingProgress(volunteer_id=v.id, module_id=mid)
        db.session.add(prog)
        db.session.commit()
        pid = prog.id

    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'
        
    client.post(f'/admin/training/{cid}/delete', follow_redirects=True)
    
    with test_app.app_context():
        assert TrainingCourse.query.get(cid) is None
        assert TrainingModule.query.get(mid) is None
        assert TrainingProgress.query.get(pid) is None


def test_training_csrf_rejection(test_app):
    """Prove that state changing endpoints reject missing CSRF tokens."""
    test_app.config['WTF_CSRF_ENABLED'] = True
    csrf_client = test_app.test_client()
    
    with csrf_client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'
    
    # Missing CSRF token will yield 400 Bad Request
    resp = csrf_client.post('/admin/training/create', data={
        'title': 'No CSRF',
    })
    assert resp.status_code == 400
    
    # Restore config
    test_app.config['WTF_CSRF_ENABLED'] = False

def test_course_validation_rejection(client, test_app):
    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'
    
    # Test empty title
    resp = client.post('/admin/training/create', data={
        'title': '   ', # empty after strip
    }, follow_redirects=True)
    
    # Check flash message or db
    with test_app.app_context():
        assert TrainingCourse.query.count() == 0
        
    # Test invalid URL
    resp = client.post('/admin/training/create', data={
        'title': 'Valid Title',
        'cover_image_url': 'not_a_url'
    }, follow_redirects=True)
    
    with test_app.app_context():
        assert TrainingCourse.query.count() == 0

def test_module_validation_rejection(client, test_app):
    with test_app.app_context():
        c = TrainingCourse(title='Course')
        db.session.add(c)
        db.session.commit()
        cid = c.id

    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'

    # Test invalid position parsing does not 500
    resp = client.post(f'/admin/training/{cid}/modules/create', data={
        'title': 'Valid Mod',
        'position': 'abc_not_number'
    }, follow_redirects=True)
    assert resp.status_code == 200
    
    with test_app.app_context():
        m = TrainingModule.query.first()
        assert m is not None
        assert m.position == 0 # Defaults to 0 safely

