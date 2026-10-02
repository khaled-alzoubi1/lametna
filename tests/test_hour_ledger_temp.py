
import pytest
from app import db, Volunteer, HourLedger

def test_backfill_legacy_hours_creates_baseline(test_app, volunteer1):
    from app import backfill_legacy_hours
    with test_app.app_context():
        v = db.session.get(Volunteer, volunteer1)
        v.volunteer_hours = (v.volunteer_hours or 0) + 10.0
        db.session.commit()
        
        # we don't know the exact baseline delta since it depends on previous tests, 
        # but we know it should create a ledger entry.
        existing_ledger_sum = db.session.query(db.func.sum(HourLedger.hours)).filter(HourLedger.volunteer_id == volunteer1).scalar() or 0
        expected_delta = v.volunteer_hours - existing_ledger_sum
        
        backfill_legacy_hours()
        
        # Verify ledger has the baseline
        ledger = HourLedger.query.filter_by(volunteer_id=volunteer1, idempotency_key=f"baseline_migration:{volunteer1}").first()
        assert ledger is not None
        assert ledger.hours == expected_delta
        assert ledger.reason == "رصيد الساعات السابق (Legacy Baseline)"

def test_backfill_legacy_hours_idempotent(test_app, volunteer1):
    from app import backfill_legacy_hours
    with test_app.app_context():
        v = db.session.get(Volunteer, volunteer1)
        v.volunteer_hours = (v.volunteer_hours or 0) + 5.0
        db.session.commit()
        
        backfill_legacy_hours()
        backfill_legacy_hours() # Call twice
        
        ledgers = HourLedger.query.filter_by(volunteer_id=volunteer1, idempotency_key=f"baseline_migration:{volunteer1}").all()
        # Should only be 1 baseline entry per volunteer
        assert len(ledgers) == 1

def test_record_hours_updates_compatibility_and_ledger(test_app, volunteer1):
    from app import record_hours
    with test_app.app_context():
        v = db.session.get(Volunteer, volunteer1)
        initial_hours = v.volunteer_hours or 0
        
        applied = record_hours(v, 4.0, "Testing Service", None, "test_record_1")
        assert applied is True
        db.session.commit()
        assert v.volunteer_hours == initial_hours + 4.0
        
        ledger = HourLedger.query.filter_by(idempotency_key="test_record_1").first()
        assert ledger is not None
        assert ledger.hours == 4.0

def test_record_hours_respects_idempotency(test_app, volunteer1):
    from app import record_hours
    with test_app.app_context():
        v = db.session.get(Volunteer, volunteer1)
        initial_hours = v.volunteer_hours or 0
        
        # First call succeeds
        applied1 = record_hours(v, 2.0, "Idempotency Test", None, "test_idem_key")
        assert applied1 is True
        db.session.commit()
        
        # Second call with same key fails safely
        applied2 = record_hours(v, 2.0, "Idempotency Test", None, "test_idem_key")
        assert applied2 is False
        db.session.commit()
        
        assert v.volunteer_hours == initial_hours + 2.0
        assert HourLedger.query.filter_by(idempotency_key="test_idem_key").count() == 1
