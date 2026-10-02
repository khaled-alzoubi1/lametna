import pytest
from app import app, db, EventRegistration, change_registration_status

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
