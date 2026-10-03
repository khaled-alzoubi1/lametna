"""
Shared pytest fixtures for P1/P2/P3 tests.

These fixtures are used by test_notifications.py, test_qr_attendance.py,
test_notifications_p1d.py, and other tests that do not define their own fixtures.

The Volunteer.email addresses are distinct from those in test_integrity.py
to avoid cross-contamination between session-scoped and module-scoped fixtures.
"""

import os
import pytest
from datetime import datetime, timedelta

os.environ.setdefault('FLASK_ENV', 'development')
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app import app as _app, db, Volunteer, Event, EventRegistration, HourLedger


@pytest.fixture(scope='function', autouse=True)
def test_app():
    """
    Function-scoped test application with in-memory SQLite.
    """
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
    })

    with _app.app_context():
        db.create_all()
        yield _app
        db.session.remove()
        try:
            db.drop_all()
        except Exception:
            pass



@pytest.fixture
def client(test_app):
    """Test client for the test application."""
    return test_app.test_client()


@pytest.fixture(autouse=True)
def volunteer1(test_app):
    """Create or return volunteer 1 (approved, standard)."""
    with test_app.app_context():
        v = Volunteer.query.filter_by(email='conf_v1@test.com').first()
        if not v:
            v = Volunteer(
                name='ConfV1',
                email='conf_v1@test.com',
                phone='0790001100',
                password_hash='x',
                status='approved',
            )
            db.session.add(v)
            db.session.commit()
        return v.id


@pytest.fixture
def volunteer2(test_app):
    """Create or return volunteer 2 (approved, standard)."""
    with test_app.app_context():
        v = Volunteer.query.filter_by(email='conf_v2@test.com').first()
        if not v:
            v = Volunteer(
                name='ConfV2',
                email='conf_v2@test.com',
                phone='0790001101',
                password_hash='x',
                status='approved',
            )
            db.session.add(v)
            db.session.commit()
        return v.id


@pytest.fixture
def today_event(test_app):
    """Event happening today with a known secret_code for QR/attendance tests."""
    with test_app.app_context():
        today_str = datetime.now().strftime('%Y-%m-%d')
        e = Event(
            title='ConfTodayEvent',
            description='Shared conftest fixture event for today.',
            date=today_str,
            time='10:00',
            location='Amman',
            capacity=10,
            event_hours=7,
            secret_code='ABC123',
        )
        db.session.add(e)
        db.session.commit()
        eid = e.id
    yield eid
    with test_app.app_context():
        EventRegistration.query.filter_by(event_id=eid).delete()
        HourLedger.query.filter_by(event_id=eid).delete()
        ev = db.session.get(Event, eid)
        if ev:
            db.session.delete(ev)
        db.session.commit()


@pytest.fixture
def past_event(test_app):
    """Event in the past (is_completed==True)."""
    with test_app.app_context():
        past_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        e = Event(
            title='ConfPastEvent',
            description='Past event fixture.',
            date=past_date,
            time='10:00',
            location='Amman',
            capacity=10,
            secret_code='XYZ987',
        )
        db.session.add(e)
        db.session.commit()
        eid = e.id
    yield eid
    with test_app.app_context():
        EventRegistration.query.filter_by(event_id=eid).delete()
        HourLedger.query.filter_by(event_id=eid).delete()
        ev = db.session.get(Event, eid)
        if ev:
            db.session.delete(ev)
        db.session.commit()


@pytest.fixture
def fresh_event(test_app):
    """Future event with capacity=2."""
    with test_app.app_context():
        future_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        e = Event(
            title='ConfFreshEvent',
            description='Fresh event fixture.',
            date=future_date,
            time='10:00',
            location='Amman',
            capacity=2,
            event_hours=5,
        )
        db.session.add(e)
        db.session.commit()
        eid = e.id
    yield eid
    with test_app.app_context():
        EventRegistration.query.filter_by(event_id=eid).delete()
        ev = db.session.get(Event, eid)
        if ev:
            db.session.delete(ev)
        db.session.commit()
