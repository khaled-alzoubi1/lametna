import pytest
from app import db, Volunteer, HourLedger, backfill_legacy_hours, record_hours
from sqlalchemy.exc import IntegrityError

def test_record_hours_rollback_consistency(test_app, volunteer1):
    with test_app.app_context():
        v = db.session.get(Volunteer, volunteer1)
        initial_hours = v.volunteer_hours or 0
        
        applied = record_hours(v, 4.0, "Test Rollback", None, "rb_key")
        assert applied is True
        
        # Route encounters an error and rolls back
        db.session.rollback()
        
        v2 = db.session.get(Volunteer, volunteer1)
        assert v2.volunteer_hours == initial_hours
        assert HourLedger.query.filter_by(idempotency_key="rb_key").count() == 0

def test_record_hours_integrity_error_recovery(test_app, volunteer1):
    with test_app.app_context():
        v = db.session.get(Volunteer, volunteer1)
        
        # Insert a ledger directly to bypass record_hours app-level check
        ledger1 = HourLedger(volunteer_id=v.id, hours=1.0, reason="1", idempotency_key="db_idem_key")
        db.session.add(ledger1)
        db.session.commit()
        
        # Now try to insert another one with the same key DIRECTLY 
        # (simulating a race condition bypassing the app-level check)
        ledger2 = HourLedger(volunteer_id=v.id, hours=2.0, reason="2", idempotency_key="db_idem_key")
        db.session.add(ledger2)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
            
        # Session must be recoverable after rollback
        db.session.rollback()
        
        # Normal operations should now work
        applied = record_hours(v, 1.0, "Recovery", None, "new_key")
        assert applied is True
        db.session.commit()
        assert HourLedger.query.filter_by(idempotency_key="new_key").count() == 1

def test_backfill_legacy_hours_skips_inconsistent_data(test_app, volunteer1):
    with test_app.app_context():
        v = db.session.get(Volunteer, volunteer1)
        
        # Setup inconsistent state: Cache is 5, but Ledger has 10
        v.volunteer_hours = 5.0
        db.session.commit()
        
        HourLedger.query.filter_by(volunteer_id=v.id).delete()
        ledger = HourLedger(volunteer_id=v.id, hours=10.0, reason="Existing", idempotency_key="existing")
        db.session.add(ledger)
        db.session.commit()
        
        # Run backfill
        backfill_legacy_hours()
        
        # The backfill must SKIP this volunteer and NOT create a baseline, 
        # and leave the cache alone
        v2 = db.session.get(Volunteer, volunteer1)
        assert v2.volunteer_hours == 5.0
        
        # There should be no baseline entry
        baseline = HourLedger.query.filter_by(volunteer_id=v.id, idempotency_key=f"baseline_migration:{v.id}").first()
        assert baseline is None
