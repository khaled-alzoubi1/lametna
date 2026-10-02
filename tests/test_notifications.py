import pytest
from app import app, db, Notification, notify_volunteer

def test_notification_creation_and_ownership(client, test_app, volunteer1):
    with app.app_context():
        # Create notification
        notify_volunteer(volunteer1, 'SYSTEM', 'Test', 'Test msg', 'sys:1')
        db.session.commit()
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    # Read notifications
    resp = client.get('/notifications')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data['notifications']) == 1
    assert data['notifications'][0]['title'] == 'Test'
    assert data['notifications'][0]['is_read'] == False

def test_notification_idempotency(test_app, volunteer1):
    with app.app_context():
        notify_volunteer(volunteer1, 'SYSTEM', 'Idem1', 'msg', 'ref1')
        notify_volunteer(volunteer1, 'SYSTEM', 'Idem2', 'msg', 'ref1') # Duplicate ref
        db.session.commit()
        
        count = Notification.query.filter_by(volunteer_id=volunteer1, reference_id='ref1').count()
        assert count == 1
        
def test_notification_transaction_safety(test_app, volunteer1):
    with app.app_context():
        # Simulate a transaction that rolls back
        notify_volunteer(volunteer1, 'SYSTEM', 'Fail', 'msg', 'fail1')
        db.session.rollback()
        
        count = Notification.query.filter_by(volunteer_id=volunteer1, reference_id='fail1').count()
        assert count == 0

def test_notification_mark_read(client, test_app, volunteer1):
    with app.app_context():
        n = notify_volunteer(volunteer1, 'SYSTEM', 'ReadTest', 'msg', 'read1')
        db.session.commit()
        n_id = n.id
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    resp = client.post(f'/notifications/read/{n_id}')
    assert resp.status_code == 200
    
    with app.app_context():
        n = db.session.get(Notification, n_id)
        assert n.is_read == True

def test_notification_unauthorized_access(client, test_app, volunteer1, volunteer2):
    with app.app_context():
        n = notify_volunteer(volunteer1, 'SYSTEM', 'Private', 'msg', 'priv1')
        db.session.commit()
        n_id = n.id
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer2 # Different user
        
    # Try to mark another user's notification as read
    resp = client.post(f'/notifications/read/{n_id}')
    assert resp.status_code == 404
    
    with app.app_context():
        n = db.session.get(Notification, n_id)
        assert n.is_read == False # Remains unread
