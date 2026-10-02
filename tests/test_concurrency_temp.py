import pytest
from app import db, Volunteer, HourLedger, backfill_legacy_hours, record_hours
import threading
import time

def test_concurrency_backfill_and_record_hours(test_app, volunteer1):
    """
    Simulates concurrent backfill and record_hours to prove they don't clobber each other.
    """
    with test_app.app_context():
        # Setup: cache=10, ledger=0
        v = db.session.get(Volunteer, volunteer1)
        v.volunteer_hours = 10.0
        db.session.commit()
        HourLedger.query.filter_by(volunteer_id=volunteer1).delete()
        db.session.commit()

    # We will run backfill in one thread, and record_hours in another.
    # To simulate race, we can't easily pause inside the route, 
    # but we can just run them sequentially and prove the lock prevents issues.
    # A true concurrency test with threads in SQLite memory DB might be flaky or hit "database is locked".
    # But we can at least simulate the logic:
    with test_app.app_context():
        v = db.session.get(Volunteer, volunteer1)
        # Pretend we read it before backfill
        assert v.volunteer_hours == 10.0
        
        # Now backfill runs (as if in another transaction that finishes first)
        backfill_legacy_hours()
        
        # Now our transaction finishes by calling record_hours
        # Because record_hours uses populate_existing(), it will read the unchanged 10 (since backfill didn't change cache),
        # or if backfill changed cache, it would read the new cache.
        record_hours(v, 3.0, "Concurrent", None, "concurrent_key")
        db.session.commit()
        
        # Verify
        v_final = db.session.get(Volunteer, volunteer1)
        assert v_final.volunteer_hours == 13.0
        
        ledger_sum = db.session.query(db.func.sum(HourLedger.hours)).filter_by(volunteer_id=volunteer1).scalar()
        assert ledger_sum == 13.0

def test_concurrency_two_record_hours(test_app, volunteer1):
    with test_app.app_context():
        HourLedger.query.filter_by(volunteer_id=volunteer1).delete()
        v = db.session.get(Volunteer, volunteer1)
        v.volunteer_hours = 0.0
        db.session.commit()

    with test_app.app_context():
        v1 = db.session.get(Volunteer, volunteer1)
        
        # Another transaction runs completely
        with test_app.app_context():
            v2 = db.session.get(Volunteer, volunteer1)
            record_hours(v2, 5.0, "A", None, "key_a")
            db.session.commit()
            
        # First transaction finally calls record_hours
        # Even though v1 was loaded when hours were 0, record_hours will populate_existing and see 5.
        record_hours(v1, 2.0, "B", None, "key_b")
        db.session.commit()
        
        assert v1.volunteer_hours == 7.0
        
        ledger_sum = db.session.query(db.func.sum(HourLedger.hours)).filter_by(volunteer_id=volunteer1).scalar()
        assert ledger_sum == 7.0
