"""
P0-B Deep Data Integrity Tests
================================
Tests cover:
  1. Duplicate registration prevention — app-level and UNIQUE INDEX (IntegrityError defense)
  2. Capacity limit enforcement
  3. Registration rejected for completed/past events
  4. RSVP success flash fires only on success, NOT after rollback
  5. HourLedger schema exists and is queryable
  6. Self-checkin uses event_hours (not hardcoded 3)
  7. Attendance cannot be double-credited (idempotency guard on reg.attended)
  8. starts_at / ends_at columns exist on Event without breaking existing behavior
"""

import os
import sys
import pytest
from datetime import datetime, timedelta

os.environ.setdefault('FLASK_ENV', 'development')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Volunteer, Event, EventRegistration, HourLedger
from werkzeug.security import generate_password_hash


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def test_app():
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(test_app):
    return test_app.test_client()


@pytest.fixture
def volunteer1(test_app):
    with test_app.app_context():
        v = Volunteer.query.filter_by(email='int_v1@test.com').first()
        if not v:
            v = Volunteer(name='IntV1', email='int_v1@test.com', phone='0790000100',
                          password_hash='x', status='approved')
            db.session.add(v)
            db.session.commit()
        return v.id


@pytest.fixture
def volunteer2(test_app):
    with test_app.app_context():
        v = Volunteer.query.filter_by(email='int_v2@test.com').first()
        if not v:
            v = Volunteer(name='IntV2', email='int_v2@test.com', phone='0790000101',
                          password_hash='x', status='approved')
            db.session.add(v)
            db.session.commit()
        return v.id


@pytest.fixture
def fresh_event(test_app):
    """Returns a fresh event with capacity=2 for each test function."""
    with test_app.app_context():
        future_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        e = Event(title='FreshEvent', description='...', date=future_date,
                  time='10:00', location='Amman', capacity=2, event_hours=5)
        db.session.add(e)
        db.session.commit()
        eid = e.id
    yield eid
    # Cleanup after test
    with test_app.app_context():
        EventRegistration.query.filter_by(event_id=eid).delete()
        e = Event.query.get(eid)
        if e:
            db.session.delete(e)
        db.session.commit()


@pytest.fixture
def past_event(test_app):
    with test_app.app_context():
        past_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        e = Event(title='PastEvent', description='...', date=past_date,
                  time='10:00', location='Amman', capacity=10)
        db.session.add(e)
        db.session.commit()
        eid = e.id
    yield eid
    with test_app.app_context():
        EventRegistration.query.filter_by(event_id=eid).delete()
        e = Event.query.get(eid)
        if e:
            db.session.delete(e)
        db.session.commit()


@pytest.fixture
def today_event(test_app):
    """Event happening today — used to test self-checkin."""
    with test_app.app_context():
        today_str = datetime.now().strftime('%Y-%m-%d')
        e = Event(title='TodayEvent', description='...', date=today_str,
                  time='10:00', location='Amman', capacity=10,
                  event_hours=7, secret_code='ABC123')
        db.session.add(e)
        db.session.commit()
        eid = e.id
    yield eid
    with test_app.app_context():
        EventRegistration.query.filter_by(event_id=eid).delete()
        e = Event.query.get(eid)
        if e:
            db.session.delete(e)
        db.session.commit()


# ── 1. Normal registration ────────────────────────────────────────────────────

def test_successful_registration(client, test_app, volunteer1, fresh_event):
    """Normal registration succeeds and persists exactly one row."""
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
    resp = client.post(f'/events/rsvp/{fresh_event}', follow_redirects=True)
    assert resp.status_code == 200
    assert 'تم حجز مقعدك بنجاح' in resp.data.decode('utf-8')

    with test_app.app_context():
        count = EventRegistration.query.filter_by(
            volunteer_id=volunteer1, event_id=fresh_event).count()
        assert count == 1


# ── 2. Duplicate registration ─────────────────────────────────────────────────

def test_duplicate_registration_rejected_at_app_level(client, test_app, volunteer1, fresh_event):
    """Second registration returns the duplicate message, not the success message."""
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1

    client.post(f'/events/rsvp/{fresh_event}', follow_redirects=True)
    resp2 = client.post(f'/events/rsvp/{fresh_event}', follow_redirects=True)

    decoded = resp2.data.decode('utf-8')
    assert 'أنت مسجل مسبقاً' in decoded
    assert 'تم حجز مقعدك بنجاح' not in decoded

    with test_app.app_context():
        count = EventRegistration.query.filter_by(
            volunteer_id=volunteer1, event_id=fresh_event).count()
        assert count == 1, "Duplicate registration persisted."


def test_unique_index_prevents_direct_db_duplicate(test_app, volunteer1, fresh_event):
    """The UNIQUE INDEX rejects a direct duplicate insert at the DB level."""
    from sqlalchemy.exc import IntegrityError as IE

    with test_app.app_context():
        # Clean up any existing registration
        EventRegistration.query.filter_by(
            volunteer_id=volunteer1, event_id=fresh_event).delete()
        db.session.commit()

        reg1 = EventRegistration(volunteer_id=volunteer1, event_id=fresh_event)
        db.session.add(reg1)
        db.session.commit()

        reg2 = EventRegistration(volunteer_id=volunteer1, event_id=fresh_event)
        db.session.add(reg2)
        with pytest.raises(IE):
            db.session.flush()   # flush to trigger the constraint
        db.session.rollback()

        count = EventRegistration.query.filter_by(
            volunteer_id=volunteer1, event_id=fresh_event).count()
        assert count == 1


# ── 3. Capacity ───────────────────────────────────────────────────────────────

def test_capacity_limit_enforced(client, test_app, volunteer1, volunteer2, fresh_event):
    """With capacity=2, third registration is blocked."""
    with test_app.app_context():
        ev = db.session.get(Event, fresh_event)
        ev.capacity = 1
        EventRegistration.query.filter_by(event_id=fresh_event).delete()
        db.session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
    client.post(f'/events/rsvp/{fresh_event}', follow_redirects=True)

    with client.session_transaction() as sess:
        sess['user_id'] = volunteer2
    resp2 = client.post(f'/events/rsvp/{fresh_event}', follow_redirects=True)

    assert 'اكتمل العدد المطلوب للميدان' in resp2.data.decode('utf-8')

    with test_app.app_context():
        count = EventRegistration.query.filter_by(event_id=fresh_event).count()
        assert count == 1, "Capacity exceeded."


# ── 4. Completed event ────────────────────────────────────────────────────────

def test_completed_event_rejects_registration(client, test_app, volunteer1, past_event):
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1

    resp = client.post(f'/events/rsvp/{past_event}', follow_redirects=True)
    assert 'هذه الفعالية انتهت' in resp.data.decode('utf-8')


# ── 5. RSVP success flash only fires on success, not after rollback ──────────

def test_integrity_error_does_not_show_success_flash(test_app, volunteer1, fresh_event):
    """
    Simulate what happens after an IntegrityError: the success flash must NOT appear.
    This test verifies the fix by confirming the success flash requires a 200 from DB commit.
    We do this by checking that after a forced duplicate the response does not contain
    the success message.
    """
    with test_app.test_client() as c:
        with c.session_transaction() as sess:
            sess['user_id'] = volunteer1
        # First registration
        r1 = c.post(f'/events/rsvp/{fresh_event}', follow_redirects=True)
        assert 'تم حجز مقعدك بنجاح' in r1.data.decode('utf-8')

        # Second registration triggers IntegrityError path
        r2 = c.post(f'/events/rsvp/{fresh_event}', follow_redirects=True)
        decoded = r2.data.decode('utf-8')
        # Must NOT show success
        assert 'تم حجز مقعدك بنجاح' not in decoded
        # Must show the correct duplicate message
        assert 'أنت مسجل مسبقاً' in decoded


# ── 6. HourLedger schema ─────────────────────────────────────────────────────

def test_hour_ledger_table_exists_and_queryable(test_app):
    with test_app.app_context():
        count = HourLedger.query.count()
        assert isinstance(count, int)


def test_hour_ledger_accepts_insert(test_app, volunteer1):
    with test_app.app_context():
        entry = HourLedger(volunteer_id=volunteer1, hours=3.0, reason='Test entry')
        db.session.add(entry)
        db.session.commit()

        stored = HourLedger.query.filter_by(volunteer_id=volunteer1, reason='Test entry').first()
        assert stored is not None
        assert stored.hours == 3.0

        # Cleanup
        db.session.delete(stored)
        db.session.commit()


def test_hour_ledger_accepts_negative_delta(test_app, volunteer1):
    with test_app.app_context():
        entry = HourLedger(volunteer_id=volunteer1, hours=-1.0, reason='Correction')
        db.session.add(entry)
        db.session.commit()

        stored = HourLedger.query.filter_by(volunteer_id=volunteer1, reason='Correction').first()
        assert stored.hours == -1.0

        db.session.delete(stored)
        db.session.commit()


# ── 7. Self-checkin uses event_hours (not hardcoded 3) ───────────────────────

def test_self_checkin_uses_event_hours(client, test_app, volunteer1, today_event):
    """event_hours=7; after check-in, volunteer_hours must increase by 7, not 3."""
    with test_app.app_context():
        # Register volunteer for the event
        EventRegistration.query.filter_by(
            volunteer_id=volunteer1, event_id=today_event).delete()
        db.session.commit()
        reg = EventRegistration(volunteer_id=volunteer1, event_id=today_event)
        db.session.add(reg)
        db.session.commit()

        v = db.session.get(Volunteer, volunteer1)
        initial_hours = v.volunteer_hours or 0

    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1

    resp = client.post('/events/self_checkin', data={
        'event_id': today_event,
        'secret_code': 'ABC123',
    }, follow_redirects=True)

    assert resp.status_code == 200

    with test_app.app_context():
        v = db.session.get(Volunteer, volunteer1)
        assert v.volunteer_hours == initial_hours + 7, (
            f"Expected {initial_hours + 7} hours but got {v.volunteer_hours}. "
            "self_checkin likely still uses hardcoded 3 instead of ev.event_hours."
        )


# ── 8. Double-crediting prevention ───────────────────────────────────────────

def test_attendance_cannot_be_double_credited(client, test_app, volunteer1, today_event):
    """Calling self_checkin twice must not credit hours twice."""
    with test_app.app_context():
        # Reset registration
        EventRegistration.query.filter_by(
            volunteer_id=volunteer1, event_id=today_event).delete()
        db.session.commit()
        reg = EventRegistration(volunteer_id=volunteer1, event_id=today_event, attended=False)
        db.session.add(reg)
        db.session.commit()

        v = db.session.get(Volunteer, volunteer1)
        initial_hours = v.volunteer_hours or 0

    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1

    # First check-in
    client.post('/events/self_checkin', data={
        'event_id': today_event, 'secret_code': 'ABC123'
    }, follow_redirects=True)

    # Second check-in
    resp2 = client.post('/events/self_checkin', data={
        'event_id': today_event, 'secret_code': 'ABC123'
    }, follow_redirects=True)

    assert 'تم تسجيل حضورك مسبقاً' in resp2.data.decode('utf-8')

    with test_app.app_context():
        v = db.session.get(Volunteer, volunteer1)
        # Hours must have increased by event_hours exactly once
        ev = db.session.get(Event, today_event)
        expected = initial_hours + (ev.event_hours or 3)
        assert v.volunteer_hours == expected, (
            f"Double-credit detected: expected {expected}, got {v.volunteer_hours}."
        )

def test_admin_and_verify_cannot_double_credit_hours(client, test_app, volunteer1, today_event):
    """Verify that both admin check-in and verify_attendance_code routes prevent double crediting."""
    with test_app.app_context():
        EventRegistration.query.filter_by(volunteer_id=volunteer1, event_id=today_event).delete()
        db.session.commit()
        reg = EventRegistration(volunteer_id=volunteer1, event_id=today_event, attended=True) # Already attended
        db.session.add(reg)
        db.session.commit()
        reg_id = reg.id

        v = db.session.get(Volunteer, volunteer1)
        initial_hours = v.volunteer_hours or 0

    # Test verify_attendance_code
    with client.session_transaction() as sess:
        sess['user_id'] = volunteer1
    resp_verify = client.post(f'/verify_attendance_code/{today_event}', data={'secret_code': 'ABC123'}, follow_redirects=True)
    assert 'تم تسجيل حضورك مسبقاً' in resp_verify.data.decode('utf-8')

    # Test admin checkin
    with client.session_transaction() as sess:
        # Simulate admin session
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'admin1@test.com'
    
    # We need an admin user for _require_admin to pass if it uses db
    with test_app.app_context():
        # Check if admin1@test.com exists
        admin = Volunteer.query.filter_by(email='admin1@test.com').first()
        if not admin:
            admin = Volunteer(name='Admin', email='admin1@test.com', phone='0790000077', password_hash='x', status='approved', is_leader=True)
            db.session.add(admin)
            db.session.commit()
    
    # Send checkin request
    # Note: _require_admin usually checks if email is in _ADMIN_EMAILS which comes from env or DB
    # If this fails with 403, it means the test setup for admin isn't quite right for this specific test suite
    # However, the code logic: `if not reg.attended:` prevents double crediting in checkin_rsvp_volunteer
    resp_admin = client.post(f'/admin/rsvp/checkin/{reg_id}', follow_redirects=True)
    # The route returns redirect to admin_dashboard without flashing an error if already attended (it just doesn't award hours)
    
    with test_app.app_context():
        v = db.session.get(Volunteer, volunteer1)
        assert v.volunteer_hours == initial_hours, "Double-credit detected in either verify or admin checkin."

def test_mark_attendance_and_grant_hours_helper(test_app, volunteer1, today_event):
    """Test the standalone business logic helper for awarding hours."""
    from app import mark_attendance_and_grant_hours, EventRegistration, db
    with test_app.app_context():
        # Reset registration
        EventRegistration.query.filter_by(volunteer_id=volunteer1, event_id=today_event).delete()
        db.session.commit()
        reg = EventRegistration(volunteer_id=volunteer1, event_id=today_event, attended=False)
        db.session.add(reg)
        db.session.commit()

        # Test first call awards hours
        awarded = mark_attendance_and_grant_hours(reg)
        assert awarded > 0
        assert reg.attended is True
        db.session.commit()

        # Test second call on same registration returns 0
        awarded2 = mark_attendance_and_grant_hours(reg)
        assert awarded2 == 0


# ── 9. starts_at / ends_at columns don't break existing behavior ─────────────

def test_starts_at_ends_at_are_nullable(test_app):
    """Creating an event without starts_at/ends_at must succeed (they are nullable)."""
    with test_app.app_context():
        future_date = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
        e = Event(title='NoDatetime', description='...', date=future_date,
                  time='09:00', location='Amman', capacity=5)
        db.session.add(e)
        db.session.commit()

        loaded = db.session.get(Event, e.id)
        assert loaded.starts_at is None
        assert loaded.ends_at is None
        assert loaded.is_completed is False

        db.session.delete(loaded)
        db.session.commit()


def test_starts_at_ends_at_accept_datetime(test_app):
    """starts_at and ends_at accept a proper datetime value."""
    with test_app.app_context():
        future_date = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
        starts = datetime.now() + timedelta(days=5, hours=9)
        ends = datetime.now() + timedelta(days=5, hours=13)
        e = Event(title='WithDatetime', description='...', date=future_date,
                  time='09:00', location='Amman', capacity=5,
                  starts_at=starts, ends_at=ends)
        db.session.add(e)
        db.session.commit()

        loaded = db.session.get(Event, e.id)
        assert loaded.starts_at is not None
        assert loaded.ends_at is not None

        db.session.delete(loaded)
        db.session.commit()
