import pytest
from app import app, db, Notification, notify_volunteer

def test_notification_concurrent_duplicate_prevention(test_app, volunteer1):
    with app.app_context():
        # First notification
        n1 = notify_volunteer(volunteer1, 'SYSTEM', 'First', 'msg', 'concurrent_id')
        db.session.commit()
        
        # Second notification with same reference_id
        n2 = notify_volunteer(volunteer1, 'SYSTEM', 'Second', 'msg', 'concurrent_id')
        db.session.commit()
        
        # Verify only one was created and it's the first one
        count = Notification.query.filter_by(reference_id='concurrent_id').count()
        assert count == 1
        
        n_db = Notification.query.filter_by(reference_id='concurrent_id').first()
        assert n_db.title == 'First'
        assert n_db.id == n2.id # n2 should return the existing one!

def test_notification_null_references_allow_duplicates(test_app, volunteer1):
    with app.app_context():
        # Insert two notifications with reference_id = None
        notify_volunteer(volunteer1, 'SYSTEM', 'Null1', 'msg', None)
        notify_volunteer(volunteer1, 'SYSTEM', 'Null2', 'msg', None)
        db.session.commit()
        
        # Verify both exist
        n1 = Notification.query.filter_by(volunteer_id=volunteer1, title='Null1').first()
        n2 = Notification.query.filter_by(volunteer_id=volunteer1, title='Null2').first()
        
        assert n1 is not None
        assert n2 is not None
        assert n1.id != n2.id
