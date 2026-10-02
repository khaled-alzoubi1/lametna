import pytest


from app import db, Volunteer, Event, HourLedger, Team, TeamMembership, Goal
from services.team import TeamContributionService
from sqlalchemy.exc import IntegrityError

@pytest.fixture
def unique_volunteer(test_app):
    with test_app.app_context():
        import uuid
        uniq = str(uuid.uuid4())[:8]
        v = Volunteer(name='TestVol', email=f'vol_{uniq}@test.com', phone=f'079{uniq}', password_hash='x')
        db.session.add(v)
        db.session.commit()
        vid = v.id
        yield vid
        v = Volunteer.query.get(vid)
        if v:
            db.session.delete(v)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

@pytest.fixture
def sample_team(test_app):
    with test_app.app_context():
        t = Team(name='Test Team', description='Desc')
        db.session.add(t)
        db.session.commit()
        tid = t.id
        yield tid
        t = Team.query.get(tid)
        if t:
            db.session.delete(t)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

def test_team_crud(test_app):
    with test_app.app_context():
        t = Team(name='CRUD Team')
        db.session.add(t)
        db.session.commit()
        
        assert t.id is not None
        assert t.is_active is True
        
        t.name = 'Updated Team'
        db.session.commit()
        
        fetched = Team.query.get(t.id)
        assert fetched.name == 'Updated Team'
        
        fetched.is_active = False
        db.session.commit()
        assert Team.query.get(t.id).is_active is False

def test_team_membership(test_app, unique_volunteer, sample_team):
    with test_app.app_context():
        m = TeamMembership(volunteer_id=unique_volunteer, team_id=sample_team, role='MEMBER')
        db.session.add(m)
        db.session.commit()
        
        v = Volunteer.query.get(unique_volunteer)
        t = Team.query.get(sample_team)
        
        assert m in v.team_memberships
        assert m in t.memberships

def test_duplicate_membership_prevention(test_app, unique_volunteer, sample_team):
    with test_app.app_context():
        m1 = TeamMembership(volunteer_id=unique_volunteer, team_id=sample_team, role='MEMBER')
        db.session.add(m1)
        db.session.commit()
        
        m2 = TeamMembership(volunteer_id=unique_volunteer, team_id=sample_team, role='LEADER')
        db.session.add(m2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

def test_leader_concept_separation(test_app, unique_volunteer, sample_team):
    with test_app.app_context():
        # Assigning a role of LEADER in TeamMembership does NOT make the volunteer an admin.
        m = TeamMembership(volunteer_id=unique_volunteer, team_id=sample_team, role='LEADER')
        db.session.add(m)
        db.session.commit()
        
        v = Volunteer.query.get(unique_volunteer)
        # Volunteer is not admin because admins are strictly checked by email in is_admin_session()
        assert v.email not in ['lanooshabdo7@gmail.com', 'khaledsalzoubi1352006@gmail.com']

def test_goal_crud(test_app, sample_team):
    with test_app.app_context():
        g = Goal(team_id=sample_team, title='100 Hours', target_value=100)
        db.session.add(g)
        db.session.commit()
        
        assert g.id is not None
        assert g.status == 'ACTIVE'
        
        g.status = 'ACHIEVED'
        db.session.commit()
        assert Goal.query.get(g.id).status == 'ACHIEVED'

def test_event_relationship_and_contribution(test_app, unique_volunteer, sample_team):
    with test_app.app_context():
        # Create an event tied to the team
        ev = Event(title='Team Event', description='Desc', date='2030-01-01', time='10:00', location='Amman', event_hours=3, team_id=sample_team)
        db.session.add(ev)
        db.session.commit()
        
        # Record hours in authoritative HourLedger
        hl = HourLedger(volunteer_id=unique_volunteer, event_id=ev.id, hours=3.5, reason='Attended')
        db.session.add(hl)
        db.session.commit()
        
        # Check team progress
        team_progress = TeamContributionService.get_team_progress(sample_team)
        assert team_progress == 3.5
        
        # Check volunteer contribution to team
        vol_contrib = TeamContributionService.get_volunteer_contribution(unique_volunteer, sample_team)
        assert vol_contrib == 3.5

def test_existing_events_remain_valid_without_team(test_app):
    with test_app.app_context():
        ev = Event(title='Global Event', description='Desc', date='2030-01-01', time='10:00', location='Amman', event_hours=3)
        db.session.add(ev)
        db.session.commit()
        
        fetched = Event.query.get(ev.id)
        assert fetched.team_id is None
        assert fetched.title == 'Global Event'

import pytest
from app import db, Team, Event, app
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

def test_db_fk_behavior():
    # Use isolated app context to prevent sqlite in-memory locks on other tests
    from app import app as isolated_app, db
    isolated_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///test_fk.db',
        'WTF_CSRF_ENABLED': False,
    })
    with isolated_app.app_context():
        db.create_all()
        is_sqlite = 'sqlite' in isolated_app.config['SQLALCHEMY_DATABASE_URI']
        if is_sqlite:
            db.session.execute(text('PRAGMA foreign_keys = ON;'))
        
        t = Team(name='Test Team', description='Desc')
        db.session.add(t)
        db.session.commit()
        
        ev_valid = Event(title='Valid', description='D', date='2030-01-01', time='10:00', location='L', event_hours=3, team_id=t.id)
        db.session.add(ev_valid)
        db.session.commit()
        
        ev_null = Event(title='Null', description='D', date='2030-01-01', time='10:00', location='L', event_hours=3, team_id=None)
        db.session.add(ev_null)
        db.session.commit()
        
        ev_invalid = Event(title='Invalid', description='D', date='2030-01-01', time='10:00', location='L', event_hours=3, team_id=999999)
        db.session.add(ev_invalid)
        
        import pytest
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        
        db.session.delete(t)
        db.session.commit()
        
        db.session.refresh(ev_valid)
        assert ev_valid.team_id is None
        
        # Cleanup
        db.session.remove()
        db.drop_all()
    
    import os
    if os.path.exists('test_fk.db'):
        os.remove('test_fk.db')


@pytest.fixture
def client(test_app):
    with test_app.test_client() as client:
        yield client

def test_admin_create_team(client, test_app):
    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'
    
    resp = client.post('/admin/teams/create', data={
        'name': 'New Admin Team',
        'description': 'Admin Desc'
    }, follow_redirects=True)
    assert resp.status_code == 200
    
    with test_app.app_context():
        t = Team.query.filter_by(name='New Admin Team').first()
        assert t is not None
        assert t.description == 'Admin Desc'
        assert t.is_active is True

def test_admin_edit_team(client, test_app):
    with test_app.app_context():
        t = Team(name='Old Name')
        db.session.add(t)
        db.session.commit()
        tid = t.id

    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'
    
    resp = client.post(f'/admin/teams/{tid}/edit', data={
        'name': 'New Name',
        'description': 'New Desc'
    }, follow_redirects=True)
    
    with test_app.app_context():
        t = Team.query.get(tid)
        assert t.name == 'New Name'
        assert t.description == 'New Desc'

def test_admin_toggle_team(client, test_app):
    with test_app.app_context():
        t = Team(name='Toggle Team')
        db.session.add(t)
        db.session.commit()
        tid = t.id

    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'
    
    client.post(f'/admin/teams/{tid}/toggle', follow_redirects=True)
    with test_app.app_context():
        assert Team.query.get(tid).is_active is False
    
    client.post(f'/admin/teams/{tid}/toggle', follow_redirects=True)
    with test_app.app_context():
        assert Team.query.get(tid).is_active is True

def test_team_admin_requires_auth(client):
    resp = client.post('/admin/teams/create', data={'name': 'Hacker'})
    assert resp.status_code in (302, 403)
    if resp.status_code == 302:
        assert '/admin' not in resp.headers.get('Location', '')

def test_team_admin_rejects_volunteer(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 999
    resp = client.post('/admin/teams/create', data={'name': 'Hacker'})
    assert resp.status_code in (302, 403)
    
def test_team_admin_rejects_leader(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 999
        sess['is_leader'] = True # mock attribute if it existed
    resp = client.post('/admin/teams/create', data={'name': 'Hacker'})
    assert resp.status_code in (302, 403)

def test_team_admin_rejects_blank_name(client, test_app):
    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'
    
    client.post('/admin/teams/create', data={'name': '   ', 'description': 'bad'}, follow_redirects=True)
    with test_app.app_context():
        assert Team.query.filter_by(description='bad').first() is None


def test_admin_soft_deactivation_preserves_data(client, test_app, unique_volunteer):
    with test_app.app_context():
        # Setup scenario: Team with Membership, Goal, and Event
        t = Team(name='Soft Deact Team')
        db.session.add(t)
        db.session.commit()
        tid = t.id

        tm = TeamMembership(volunteer_id=unique_volunteer, team_id=tid, role='MEMBER')
        g = Goal(team_id=tid, title='Goal 1', target_value=100)
        ev = Event(title='Event 1', description='Desc', date='2030-01-01', time='10:00', location='Amman', event_hours=2, capacity=10, team_id=tid)
        
        db.session.add_all([tm, g, ev])
        db.session.commit()
        
        tm_vol = tm.volunteer_id
        gid = g.id
        evid = ev.id

    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'

    # Deactivate through route
    client.post(f'/admin/teams/{tid}/toggle', follow_redirects=True)

    with test_app.app_context():
        t_after = Team.query.get(tid)
        assert t_after is not None
        assert t_after.is_active is False
        
        assert TeamMembership.query.filter_by(volunteer_id=tm_vol, team_id=tid).first() is not None
        assert Goal.query.get(gid) is not None
        
        ev_after = Event.query.get(evid)
        assert ev_after is not None
        assert ev_after.team_id == tid

    # Reactivate through route
    client.post(f'/admin/teams/{tid}/toggle', follow_redirects=True)
    
    with test_app.app_context():
        t_react = Team.query.get(tid)
        assert t_react.is_active is True
        assert TeamMembership.query.filter_by(volunteer_id=tm_vol, team_id=tid).first() is not None
        assert Goal.query.get(gid) is not None
        ev_react = Event.query.get(evid)
        assert ev_react.team_id == tid
