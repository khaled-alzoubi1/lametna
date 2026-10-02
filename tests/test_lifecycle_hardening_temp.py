import pytest
from app import app, db, Event, can_register
from datetime import datetime, timedelta

def test_explicit_status_cannot_override_past_date():
    """An explicit status like REGISTRATION_OPEN or IN_PROGRESS must override a past date fallback."""
    with app.app_context():
        past_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        
        ev_open = Event(title="Past Open", description="-", date=past_date, time="10:00", location="A", status="REGISTRATION_OPEN")
        ev_prog = Event(title="Past Prog", description="-", date=past_date, time="10:00", location="A", status="IN_PROGRESS")
        
        # They should NOT be completed because the explicit status is authoritative
        assert ev_open.is_completed == False
        assert ev_prog.is_completed == False
        
        # Registration must be allowed, explicit status overrides legacy date fallback
        assert can_register(ev_open) == True
        assert can_register(ev_prog) == True

def test_explicit_completed_and_cancelled():
    """COMPLETED and CANCELLED explicitly block registration regardless of date."""
    with app.app_context():
        future_date = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
        
        ev_comp = Event(title="Future Comp", description="-", date=future_date, time="10:00", location="A", status="COMPLETED")
        ev_canc = Event(title="Future Canc", description="-", date=future_date, time="10:00", location="A", status="CANCELLED")
        
        assert ev_comp.is_completed == True
        assert can_register(ev_comp) == False
        
        assert ev_canc.is_cancelled == True
        assert can_register(ev_canc) == False

def test_legacy_null_status():
    """Events with status=None fallback to date safely."""
    with app.app_context():
        future_date = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
        past_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        
        ev_fut = Event(title="Fut Null", description="-", date=future_date, time="10:00", location="A", status=None)
        ev_past = Event(title="Past Null", description="-", date=past_date, time="10:00", location="A", status=None)
        
        assert ev_fut.is_completed == False
        assert can_register(ev_fut) == True
        
        assert ev_past.is_completed == True
        assert can_register(ev_past) == False
