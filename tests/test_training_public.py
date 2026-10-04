import os
import sys

os.environ.setdefault('FLASK_ENV', 'development')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_training_list_auth_required(client):
    resp = client.get('/training')
    # Should redirect to login (index in fallback, but we use login or index, 302)
    assert resp.status_code == 302

def test_training_list_shows_published_courses(client, test_app, volunteer1):
    from app import db, TrainingCourse
    with test_app.app_context():
        c1 = TrainingCourse(title='Public Course', is_published=True)
        c2 = TrainingCourse(title='Private Course', is_published=False)
        db.session.add_all([c1, c2])
        db.session.commit()
    
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
    
    resp = client.get('/training')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Public Course' in html
    assert 'Private Course' not in html

def test_training_detail_published_only(client, test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule
    with test_app.app_context():
        c1 = TrainingCourse(title='Public Course', is_published=True)
        db.session.add(c1)
        db.session.commit()
        
        m1 = TrainingModule(course_id=c1.id, title='Public Mod', is_published=True, position=1)
        m2 = TrainingModule(course_id=c1.id, title='Private Mod', is_published=False, position=2)
        db.session.add_all([m1, m2])
        db.session.commit()
        c1_id = c1.id
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    resp = client.get(f'/training/{c1_id}')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Public Course' in html
    assert 'Public Mod' in html
    assert 'Private Mod' not in html

def test_training_detail_unpublished_course_404(client, test_app, volunteer1):
    from app import db, TrainingCourse
    with test_app.app_context():
        c2 = TrainingCourse(title='Private Course', is_published=False)
        db.session.add(c2)
        db.session.commit()
        c2_id = c2.id
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    resp = client.get(f'/training/{c2_id}')
    assert resp.status_code == 404


def test_training_detail_xss_protection(client, test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule
    with test_app.app_context():
        # Clean up
        TrainingCourse.query.filter_by(title='XSS Course <script>').delete()
        db.session.commit()
        
        c = TrainingCourse(
            title='XSS Course <script>',
            description='Line 1\nLine 2 <img src=x onerror=alert(1)>',
            is_published=True
        )
        db.session.add(c)
        db.session.commit()
        
        m = TrainingModule(
            course_id=c.id,
            title='XSS Mod <script>',
            description='Mod Desc <script>',
            content_type='<script>',
            is_published=True,
            position=1
        )
        db.session.add(m)
        db.session.commit()
        c_id = c.id
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    resp = client.get(f'/training/{c_id}')
    html = resp.data.decode('utf-8')
    
    # Assert that raw script/img tags are not present in the HTML (they should be escaped)
    assert '<script>' not in html
    assert '<img src=x onerror=alert(1)>' not in html
    
    # Assert the escaped versions are present
    assert '&lt;script&gt;' in html
    assert '&lt;img src=x onerror=alert(1)&gt;' in html
