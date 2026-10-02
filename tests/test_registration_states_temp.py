import pytest
from app import app, db, Event, EventRegistration, change_registration_status, can_register, Volunteer
from datetime import datetime, timedelta

def test_registration_states_basic(client, test_app, volunteer1):
    with app.app_context():
        # Setup event
        ev = Event(title="R-State", description="-", date="2030-01-01", time="10:00", location="A", capacity=2)
        db.session.add(ev)
        db.session.commit()
        ev_id = ev.id
        
        # Test 1: Register
        with client.session_transaction() as sess:
            sess['user_id'] = volunteer1
            
        client.post(f'/events/rsvp/{ev_id}', follow_redirects=True)
        reg = EventRegistration.query.filter_by(event_id=ev_id, volunteer_id=volunteer1).first()
        assert reg is not None
        assert reg.status == 'REGISTERED'
        assert reg.is_active == True
        
        # Event should have 1 registered count
        ev = db.session.get(Event, ev_id)
        assert ev.registered_count == 1
        
        # Test 2: Cancel
        client.post(f'/events/cancel_rsvp/{ev_id}', follow_redirects=True)
        reg = db.session.get(EventRegistration, reg.id)
        assert reg.status == 'CANCELLED'
        assert reg.is_active == False
        
        # Capacity should be freed
        ev = db.session.get(Event, ev_id)
        assert ev.registered_count == 0
        
        # Test 3: Re-register reactivates
        client.post(f'/events/rsvp/{ev_id}', follow_redirects=True)
        reg = db.session.get(EventRegistration, reg.id)
        assert reg.status == 'REGISTERED'
        assert reg.is_active == True
        assert ev.registered_count == 1
        
def test_attended_cannot_cancel(client, test_app, volunteer1):
    with app.app_context():
        ev = Event(title="R-State-Att", description="-", date="2030-01-01", time="10:00", location="A", capacity=2)
        db.session.add(ev)
        db.session.commit()
        ev_id = ev.id
        
        reg = EventRegistration(volunteer_id=volunteer1, event_id=ev_id, status='ATTENDED', attended=True)
        db.session.add(reg)
        db.session.commit()
        reg_id = reg.id
        
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
        
    resp = client.post(f'/events/cancel_rsvp/{ev_id}', follow_redirects=True)
    assert 'لا يمكن إلغاء التسجيل' in resp.data.decode('utf-8')
    
    with app.app_context():
        reg = db.session.get(EventRegistration, reg_id)
        assert reg.status == 'ATTENDED'

def test_unknown_status_is_inactive():
    with app.app_context():
        # Valid active
        reg1 = EventRegistration(status='REGISTERED')
        assert reg1.is_active == True
        
        reg2 = EventRegistration(status='ATTENDED')
        assert reg2.is_active == True
        
        reg3 = EventRegistration(status=None)
        assert reg3.is_active == True
        
        # Inactive
        reg4 = EventRegistration(status='CANCELLED')
        assert reg4.is_active == False
        
        reg5 = EventRegistration(status='WAITLISTED')
        assert reg5.is_active == False
        
        # Unknown should default to inactive explicitly
        reg6 = EventRegistration(status='SOMETHING_ELSE')
        assert reg6.is_active == False

def test_central_transition_validation():
    with app.app_context():
        # REGISTERED -> ATTENDED
        reg = EventRegistration(status='REGISTERED')
        assert change_registration_status(reg, 'ATTENDED') == True
        assert reg.status == 'ATTENDED'
        
        # ATTENDED -> CANCELLED (Blocked)
        assert change_registration_status(reg, 'CANCELLED') == False
        assert reg.status == 'ATTENDED'
        
        # CANCELLED -> ATTENDED (Blocked)
        reg.status = 'CANCELLED'
        assert change_registration_status(reg, 'ATTENDED') == False
        assert reg.status == 'CANCELLED'
        
        # WAITLISTED -> ATTENDED (Blocked)
        reg.status = 'WAITLISTED'
        assert change_registration_status(reg, 'ATTENDED') == False
        assert reg.status == 'WAITLISTED'
