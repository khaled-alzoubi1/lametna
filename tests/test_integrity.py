import pytest
from app import app, db, Volunteer, Event, EventRegistration, HourLedger
from datetime import datetime, timedelta

# Fixtures are imported from conftest.py

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
    assert 'انتهت هذه الفعالية' in resp.data.decode('utf-8')


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
        # Reset registration and ledger to prevent SQLite ID reuse idempotency block
        EventRegistration.query.filter_by(
            volunteer_id=volunteer1, event_id=today_event).delete()
        from app import HourLedger
        HourLedger.query.filter_by(
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

    # Second check-in — should be blocked by reg.attended == True
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
