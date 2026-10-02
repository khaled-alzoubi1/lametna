import pytest
from app import app, db, Event, EventRegistration, can_register, can_edit, can_cancel, can_complete, migrate_event_lifecycle
from datetime import datetime, timedelta

def test_lifecycle_helpers():
    with app.app_context():
        ev = Event(title="Test", description="-", date="2027-01-01", time="10:00", location="Amman", status="REGISTRATION_OPEN")
        
        # Test valid initial state
        assert can_register(ev) == True
        assert can_edit(ev) == True
        assert can_cancel(ev) == True
        assert can_complete(ev) == True
        
        # Cancel event
        ev.status = 'CANCELLED'
        assert ev.is_cancelled == True
        assert can_register(ev) == False
        assert can_edit(ev) == False
        assert can_cancel(ev) == False
        assert can_complete(ev) == False
        
        # Complete event
        ev.status = 'COMPLETED'
        assert ev.is_completed == True
        assert can_register(ev) == False
        assert can_edit(ev) == False
        assert can_cancel(ev) == False
        assert can_complete(ev) == False

def test_compatibility_fallback():
    with app.app_context():
        past_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        future_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        
        # No status, relies on date
        ev_past = Event(title="Past", description="-", date=past_date, time="10:00", location="A")
        assert ev_past.is_completed == True
        assert can_register(ev_past) == False
        
        ev_future = Event(title="Future", description="-", date=future_date, time="10:00", location="A")
        assert ev_future.is_completed == False
        assert can_register(ev_future) == True
        
def test_migration_mapping():
    with app.app_context():
        past_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        future_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        
        ev1 = Event(title="E1", description="-", date=past_date, time="10:00", location="A")
        ev2 = Event(title="E2", description="-", date=future_date, time="10:00", location="A")
        db.session.add_all([ev1, ev2])
        db.session.commit()
        
        assert ev1.status is None
        assert ev2.status is None
        
        migrate_event_lifecycle()
        
        # refresh
        e1 = db.session.get(Event, ev1.id)
        e2 = db.session.get(Event, ev2.id)
        
        assert e1.status == 'COMPLETED'
        assert e2.status == 'REGISTRATION_OPEN'

def test_registration_blocked_by_lifecycle(client, volunteer1):
    with app.app_context():
        ev = Event(title="Blocked", description="-", date="2027-01-01", time="10", location="A", status="CANCELLED")
        db.session.add(ev)
        db.session.commit()
        ev_id = ev.id
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    resp = client.post(f'/events/rsvp/{ev_id}', follow_redirects=True)
    assert 'انتهت هذه الفعالية أو تم إلغاؤها ولا يمكن التسجيل بها' in resp.data.decode('utf-8')
