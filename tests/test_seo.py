import os
import sys

os.environ.setdefault('FLASK_ENV', 'development')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_sitemap_xml_renders(test_app):
    # Need to create a cancelled event and an active event in the database
    from app import db, Event
    with test_app.app_context():
        # Clean up any existing test events to avoid conflicts
        Event.query.filter_by(title='Test Cancelled Event').delete()
        Event.query.filter_by(title='Test Active Event').delete()
        
        cancelled = Event(title='Test Cancelled Event', description='desc', date='2030-01-01', time='10:00', location='Amman', status='CANCELLED')
        active = Event(title='Test Active Event', description='desc', date='2030-01-01', time='10:00', location='Amman', status='REGISTRATION_OPEN')
        db.session.add(cancelled)
        db.session.add(active)
        db.session.commit()
        
        client = test_app.test_client()
        resp = client.get('/sitemap.xml')
        assert resp.status_code == 200
        
        data = resp.data.decode('utf-8')
        assert f'/events/{active.id}' in data
        assert f'/events/{cancelled.id}' not in data
        
        # Also assert auth pages are not included
        assert '/login' not in data
        assert '/register' not in data
        assert '/admin' not in data
        
        # Cleanup
        db.session.delete(cancelled)
        db.session.delete(active)
        db.session.commit()

def test_robots_txt_renders(test_app):
    client = test_app.test_client()
    resp = client.get('/robots.txt')
    assert resp.status_code == 200
    assert resp.content_type.startswith('text/plain')
    assert b'User-agent: *' in resp.data
    assert b'Disallow: /admin' in resp.data
    assert b'Sitemap:' in resp.data

def test_homepage_seo_tags(test_app):
    client = test_app.test_client()
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert '<title>' in html
    assert '<meta name="description"' in html
    assert 'property="og:title"' in html
    assert '<link rel="canonical"' in html
    assert 'rel="icon"' in html

def test_events_page_seo_tags(test_app):
    client = test_app.test_client()
    resp = client.get('/events')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert '<meta name="description"' in html
    assert 'property="og:title"' in html

def test_alt_text_improved(test_app):
    client = test_app.test_client()
    resp = client.get('/')
    html = resp.data.decode('utf-8')
    assert 'alt="Event Image"' not in html

def test_event_detail_metadata_escaping(test_app):
    from app import db, Event
    with test_app.app_context():
        Event.query.filter_by(title='Test Escaping <>&"').delete()
        
        evil_event = Event(
            title='Test Escaping <>&"',
            description='This has <script>alert(1)</script> and "quotes" & ampersands',
            date='2030-01-01', time='10:00', location='Amman'
        )
        db.session.add(evil_event)
        db.session.commit()
        
        client = test_app.test_client()
        resp = client.get(f"/events/{evil_event.id}")
        
        db.session.delete(evil_event)
        db.session.commit()
        
        html = resp.data.decode('utf-8')
        
        assert 'content="This has &lt;script&gt;alert(1)&lt;/script&gt; and &#34;quotes&#34; &amp; ampersands..."' in html
        assert 'content="Test Escaping &lt;&gt;&amp;&#34; | لمتنا بصمة"' in html

def test_auth_pages_noindex(test_app):
    client = test_app.test_client()
    for route in ['/login', '/register']:
        resp = client.get(route)
        html = resp.data.decode('utf-8')
        assert '<meta name="robots" content="noindex">' in html
