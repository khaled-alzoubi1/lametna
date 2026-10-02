from app import app, EventRegistration, change_registration_status

def test_unknown_status_is_inactive(test_app):
    with app.app_context():
        reg1 = EventRegistration(status='REGISTERED')
        assert reg1.is_active == True
        reg2 = EventRegistration(status='ATTENDED')
        assert reg2.is_active == True
        reg3 = EventRegistration(status=None)
        assert reg3.is_active == True
        reg4 = EventRegistration(status='CANCELLED')
        assert reg4.is_active == False
        reg5 = EventRegistration(status='WAITLISTED')
        assert reg5.is_active == False
        reg6 = EventRegistration(status='SOMETHING_ELSE')
        assert reg6.is_active == False

def test_central_transition_validation(test_app):
    with app.app_context():
        reg = EventRegistration(status='REGISTERED')
        assert change_registration_status(reg, 'ATTENDED') == True
        assert reg.status == 'ATTENDED'
        
        assert change_registration_status(reg, 'CANCELLED') == False
        assert reg.status == 'ATTENDED'
        
        reg.status = 'CANCELLED'
        assert change_registration_status(reg, 'ATTENDED') == False
        assert reg.status == 'CANCELLED'
        
        reg.status = 'WAITLISTED'
        assert change_registration_status(reg, 'ATTENDED') == False
        assert reg.status == 'WAITLISTED'
