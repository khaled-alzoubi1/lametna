import pytest
from app import db, Event, Team, HourLedger, Volunteer, EventRegistration
from services.team import EventTeamAssignmentService, TeamContributionService

import os



@pytest.fixture
def sample_teams(test_app):
    with test_app.app_context():
        t1 = Team(name='Team A', description='Active', is_active=True)
        t2 = Team(name='Team B', description='Active', is_active=True)
        t3 = Team(name='Team C', description='Inactive', is_active=False)
        db.session.add_all([t1, t2, t3])
        db.session.commit()
        return t1.id, t2.id, t3.id

def test_event_team_lock_before_ledger(test_app, sample_teams):
    t1_id, t2_id, t3_id = sample_teams
    with test_app.app_context():
        ev = Event(title='Unassigned', description='D', date='D', time='T', location='L', secret_code='1234')
        db.session.add(ev)
        db.session.commit()
        
        # 1. Unassigned to Active
        success, msg = EventTeamAssignmentService.assign_team(ev, t1_id)
        assert success
        assert ev.team_id == t1_id
        
        # 2. Reassign to another active
        success, msg = EventTeamAssignmentService.assign_team(ev, t2_id)
        assert success
        assert ev.team_id == t2_id
        
        # 3. Unassign
        success, msg = EventTeamAssignmentService.assign_team(ev, None)
        assert success
        assert ev.team_id is None
        
        # 4. Try assign inactive
        success, msg = EventTeamAssignmentService.assign_team(ev, t3_id)
        assert not success
        assert ev.team_id is None

def test_event_team_lock_after_ledger(test_app, sample_teams, volunteer1):
    t1_id, t2_id, t3_id = sample_teams
    with test_app.app_context():
        ev = Event(title='Locked', description='D', date='D', time='T', location='L', secret_code='1234', team_id=t1_id)
        db.session.add(ev)
        db.session.commit()
        
        hl = HourLedger(volunteer_id=volunteer1, event_id=ev.id, hours=5.0, reason='attendance')
        db.session.add(hl)
        db.session.commit()
        
        # Try reassign
        success, msg = EventTeamAssignmentService.assign_team(ev, t2_id)
        assert not success
        assert ev.team_id == t1_id
        assert 'historically locked' in msg
        
        # Try unassign
        success, msg = EventTeamAssignmentService.assign_team(ev, None)
        assert not success
        assert ev.team_id == t1_id

def test_event_team_lock_when_completed(test_app, sample_teams):
    t1_id, t2_id, t3_id = sample_teams
    with test_app.app_context():
        ev = Event(title='Completed', description='D', date='D', time='T', location='L', secret_code='1234', team_id=t1_id, status='COMPLETED')
        db.session.add(ev)
        db.session.commit()
        
        # Try reassign
        success, msg = EventTeamAssignmentService.assign_team(ev, t2_id)
        assert not success
        assert ev.team_id == t1_id

def test_event_team_contribution_stable(test_app, sample_teams, volunteer1):
    t1_id, t2_id, t3_id = sample_teams
    with test_app.app_context():
        ev = Event(title='Contributed', description='D', date='D', time='T', location='L', secret_code='1234', team_id=t1_id)
        db.session.add(ev)
        db.session.commit()
        
        hl = HourLedger(volunteer_id=volunteer1, event_id=ev.id, hours=10.0, reason='attendance')
        db.session.add(hl)
        db.session.commit()
        
        progress = TeamContributionService.get_team_progress(t1_id)
        assert progress == 10.0
        
        progress_b = TeamContributionService.get_team_progress(t2_id)
        assert progress_b == 0.0

def test_admin_route_authorization(client, test_app, sample_teams):
    t1_id, t2_id, t3_id = sample_teams
    with test_app.app_context():
        ev = Event(title='Auth', description='D', date='D', time='T', location='L', secret_code='1234', team_id=t1_id)
        db.session.add(ev)
        db.session.commit()
        ev_id = ev.id

    # Unauth
    resp = client.post(f'/admin/events/{ev_id}/team', data={'team_id': t2_id}, follow_redirects=True)
    assert resp.status_code == 200 # usually redirects to index with "Access Denied" or something
    
    with test_app.app_context():
        ev = db.session.get(Event, ev_id)
        assert ev.team_id == t1_id
        
    # Vol auth
    with client.session_transaction() as sess:
        sess['volunteer_id'] = 1
        sess['email'] = 'test@example.com'
    resp = client.post(f'/admin/events/{ev_id}/team', data={'team_id': t2_id}, follow_redirects=True)
    with test_app.app_context():
        assert db.session.get(Event, ev_id).team_id == t1_id
        
    # Admin auth
    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'
    resp = client.post(f'/admin/events/{ev_id}/team', data={'team_id': t2_id}, follow_redirects=True)
    with test_app.app_context():
        assert db.session.get(Event, ev_id).team_id == t2_id