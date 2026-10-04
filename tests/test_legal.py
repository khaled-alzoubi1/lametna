
import os
import sys
from unittest.mock import patch

os.environ.setdefault('FLASK_ENV', 'development')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_privacy_page_renders(test_app):
    client = test_app.test_client()
    resp = client.get('/privacy')
    assert resp.status_code == 200
    assert resp.content_type.startswith('text/html')
    assert 'سياسة الخصوصية'.encode('utf-8') in resp.data

def test_terms_page_renders(test_app):
    client = test_app.test_client()
    resp = client.get('/terms')
    assert resp.status_code == 200
    assert resp.content_type.startswith('text/html')
    assert 'الشروط والأحكام'.encode('utf-8') in resp.data

def test_404_page_renders_custom(test_app):
    client = test_app.test_client()
    resp = client.get('/this_route_does_not_exist_404')
    assert resp.status_code == 404
    assert resp.content_type.startswith('text/html')
    assert 'عذراً، الصفحة غير موجودة! (404)'.encode('utf-8') in resp.data

def test_500_page_renders_custom(test_app):
    def failing_view(*args, **kwargs):
        raise Exception("Simulated Server Crash!")
        
    original_view = test_app.view_functions['events_list']
    test_app.view_functions['events_list'] = failing_view
    
    test_app.config['TESTING'] = False
    test_app.config['DEBUG'] = False
    test_app.config['PROPAGATE_EXCEPTIONS'] = False
    
    client = test_app.test_client()
    
    resp = client.get('/events')
    
    test_app.view_functions['events_list'] = original_view
    test_app.config['TESTING'] = True
    
    assert resp.status_code == 500
    assert resp.content_type.startswith('text/html')
    assert 'عذراً، حدث خطأ غير متوقع (500)'.encode('utf-8') in resp.data
    assert b"Simulated Server Crash!" not in resp.data

def test_csrf_failure_ux(test_app):
    test_app.config['WTF_CSRF_ENABLED'] = True
    csrf_client = test_app.test_client()
    
    resp = csrf_client.post('/login', data={'email': 'bad@bad.com', 'password': '123'})
    
    assert resp.status_code == 400
    assert resp.content_type.startswith('text/html')
    assert 'انتهت صلاحية الجلسة أو الطلب غير صالح (400)'.encode('utf-8') in resp.data
    
    test_app.config['WTF_CSRF_ENABLED'] = False
