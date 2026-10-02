import pytest
from app import app, db, Event, EventRegistration, HourLedger, Notification

def test_qr_attendance_valid(client, test_app, volunteer1, today_event):
    with test_app.app_context():
        reg = EventRegistration(volunteer_id=volunteer1, event_id=today_event, status='REGISTERED')
        db.session.add(reg)
        db.session.commit()
    
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        sess['email'] = 'vol1@example.com'
    
    rv = client.get(f'/verify_attendance_code/{today_event}?token=ABC123')
    assert rv.status_code == 302
    
    with test_app.app_context():
        reg = EventRegistration.query.filter_by(volunteer_id=volunteer1, event_id=today_event).first()
        assert reg.attended is True
        assert reg.status == 'ATTENDED'
        ledger = HourLedger.query.filter_by(idempotency_key=f"attendance:reg:{reg.id}").first()
        assert ledger is not None
        assert ledger.hours == 7
        notif = Notification.query.filter_by(reference_id=f"attendance:reg:{reg.id}:confirmed").first()
        assert notif is not None

def test_qr_attendance_invalid_token(client, test_app, volunteer1, today_event):
    with test_app.app_context():
        reg = EventRegistration(volunteer_id=volunteer1, event_id=today_event, status='REGISTERED')
        db.session.add(reg)
        db.session.commit()
    
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        sess['email'] = 'vol1@example.com'
    
    client.get(f'/verify_attendance_code/{today_event}?token=WRONG')
    
    with test_app.app_context():
        reg = EventRegistration.query.filter_by(volunteer_id=volunteer1, event_id=today_event).first()
        assert reg.attended is False
        assert reg.status == 'REGISTERED'

def test_qr_attendance_unregistered(client, test_app, volunteer1, today_event):
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        sess['email'] = 'vol1@example.com'
    
    client.get(f'/verify_attendance_code/{today_event}?token=ABC123')
    
    with test_app.app_context():
        assert HourLedger.query.count() == 0

def test_qr_attendance_cancelled_registration(client, test_app, volunteer1, today_event):
    with test_app.app_context():
        reg = EventRegistration(volunteer_id=volunteer1, event_id=today_event, status='CANCELLED')
        db.session.add(reg)
        db.session.commit()
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        sess['email'] = 'vol1@example.com'
        
    client.get(f'/verify_attendance_code/{today_event}?token=ABC123')
    
    with test_app.app_context():
        reg = EventRegistration.query.filter_by(volunteer_id=volunteer1, event_id=today_event).first()
        assert reg.attended is False

def test_qr_attendance_waitlisted(client, test_app, volunteer1, today_event):
    with test_app.app_context():
        reg = EventRegistration(volunteer_id=volunteer1, event_id=today_event, status='WAITLISTED')
        db.session.add(reg)
        db.session.commit()
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        sess['email'] = 'vol1@example.com'
        
    client.get(f'/verify_attendance_code/{today_event}?token=ABC123')
    
    with test_app.app_context():
        reg = EventRegistration.query.filter_by(volunteer_id=volunteer1, event_id=today_event).first()
        assert reg.attended is False

def test_qr_attendance_completed_event(client, test_app, volunteer1, past_event):
    with test_app.app_context():
        ev = Event.query.get(past_event)
        ev.secret_code = 'XYZ987'
        reg = EventRegistration(volunteer_id=volunteer1, event_id=past_event, status='REGISTERED')
        db.session.add(reg)
        db.session.commit()
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        sess['email'] = 'vol1@example.com'
        
    client.get(f'/verify_attendance_code/{past_event}?token=XYZ987')
    
    with test_app.app_context():
        reg = EventRegistration.query.filter_by(volunteer_id=volunteer1, event_id=past_event).first()
        assert reg.attended is False

def test_qr_attendance_cancelled_event(client, test_app, volunteer1, fresh_event):
    with test_app.app_context():
        ev = Event.query.get(fresh_event)
        ev.status = 'CANCELLED'
        ev.secret_code = 'CANC'
        reg = EventRegistration(volunteer_id=volunteer1, event_id=fresh_event, status='REGISTERED')
        db.session.add(reg)
        db.session.commit()
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        sess['email'] = 'vol1@example.com'
        
    client.get(f'/verify_attendance_code/{fresh_event}?token=CANC')
    
    with test_app.app_context():
        reg = EventRegistration.query.filter_by(volunteer_id=volunteer1, event_id=fresh_event).first()
        assert reg.attended is False

def test_qr_attendance_unauthenticated(client, test_app, volunteer1, today_event):
    rv = client.get(f'/verify_attendance_code/{today_event}?token=ABC123')
    assert rv.status_code == 302
    assert '/verify_attendance_code' not in rv.location

def test_qr_attendance_concurrent_duplicate_idempotency(client, test_app, volunteer1, today_event):
    with test_app.app_context():
        reg = EventRegistration(volunteer_id=volunteer1, event_id=today_event, status='REGISTERED')
        db.session.add(reg)
        db.session.commit()
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        sess['email'] = 'vol1@example.com'
        
    client.get(f'/verify_attendance_code/{today_event}?token=ABC123')
    client.get(f'/verify_attendance_code/{today_event}?token=ABC123')
    
    with test_app.app_context():
        reg = EventRegistration.query.filter_by(volunteer_id=volunteer1, event_id=today_event).first()
        assert HourLedger.query.filter_by(idempotency_key=f"attendance:reg:{reg.id}").count() == 1
        assert Notification.query.filter_by(reference_id=f"attendance:reg:{reg.id}:confirmed").count() == 1
