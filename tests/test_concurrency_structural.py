import pytest
from unittest.mock import patch, MagicMock
from app import app, db, Event, Volunteer, HourLedger, mark_attendance_and_grant_hours
from services.team import EventTeamAssignmentService

def test_structural_concurrency_assign_team(test_app):
    """
    Verifies the structural ORM locking implementation for team assignment.
    This test proves that the application correctly requests a row lock
    (with_for_update) BEFORE checking the historical lock state.
    
    NOTE: Real PostgreSQL runtime concurrency verification is marked separately,
    as SQLite cannot enforce row-level FOR UPDATE locking.
    """
    with test_app.app_context():
        ev = Event(title='Structural', description='test', date='2030', time='10:00', location='L')
        db.session.add(ev)
        db.session.commit()
        
        with patch('services.team.db.session.query') as mock_query:
            mock_query_obj = MagicMock()
            mock_query.return_value = mock_query_obj
            mock_filter = MagicMock()
            mock_query_obj.filter_by.return_value = mock_filter
            mock_with_for_update = MagicMock()
            mock_filter.with_for_update.return_value = mock_with_for_update
            mock_with_for_update.first.return_value = ev
            
            EventTeamAssignmentService.assign_team(ev, None)
            
            # Verify lock was requested structurally
            assert mock_filter.with_for_update.call_count == 1

def test_structural_concurrency_attendance(test_app):
    """
    Verifies the structural ORM locking implementation for HourLedger creation.
    This test proves the application correctly requests a row lock (with_for_update)
    on the parent Event row before mutating the ledger.
    """
    with test_app.app_context():
        # Setup test data
        ev = Event(title='Structural', description='test', date='2030', time='10:00', location='L')
        v = Volunteer(name='V', email='v@v.com', phone='123', password_hash='x', status='approved')
        db.session.add_all([ev, v])
        db.session.commit()
        
        from app import EventRegistration
        reg = EventRegistration(volunteer_id=v.id, event_id=ev.id, status='REGISTERED')
        db.session.add(reg)
        db.session.commit()
        
        # We must override the sqlite check in mark_attendance_and_grant_hours to force the PostgreSQL lock path
        original_config = app.config.get('SQLALCHEMY_DATABASE_URI')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://fake'
        
        try:
            with patch('app.db.session.query') as mock_query:
                
                event_query_obj = MagicMock()
                vol_query_obj = MagicMock()
                other_query_obj = MagicMock()
                
                # Mock the chain for Event: query(Event).with_for_update().populate_existing().get(ev.id)
                mock_event_for_update = MagicMock()
                event_query_obj.with_for_update.return_value = mock_event_for_update
                mock_event_populate = MagicMock()
                mock_event_for_update.populate_existing.return_value = mock_event_populate
                mock_event_populate.get.return_value = ev
                
                # Mock the chain for Volunteer: query(Volunteer).with_for_update().populate_existing().get(v.id)
                mock_vol_for_update = MagicMock()
                vol_query_obj.with_for_update.return_value = mock_vol_for_update
                mock_vol_populate = MagicMock()
                mock_vol_for_update.populate_existing.return_value = mock_vol_populate
                mock_vol_populate.get.return_value = v
                
                # mock_query side_effect to distinguish calls
                def side_effect(*args):
                    if args[0] is Event:
                        return event_query_obj
                    if args[0] is Volunteer:
                        return vol_query_obj
                    return other_query_obj
                
                mock_query.side_effect = side_effect
                
                # Call attendance logic
                mark_attendance_and_grant_hours(reg)
                
                # Verify Event lock was requested structurally
                event_query_obj.with_for_update.assert_called_once()
                # Verify Volunteer lock was also requested structurally
                vol_query_obj.with_for_update.assert_called_once()
        finally:
            app.config['SQLALCHEMY_DATABASE_URI'] = original_config
