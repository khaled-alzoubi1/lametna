import pytest
from app import app, db, Team, Goal, Volunteer, Event, HourLedger


@pytest.fixture
def sample_team(test_app):
    with test_app.app_context():
        t = Team(name='Goal Team')
        db.session.add(t)
        db.session.commit()
        return t.id

def test_admin_create_goal(client, test_app, sample_team):
    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'
    
    resp = client.post('/admin/goals/create', data={
        'team_id': sample_team,
        'title': 'New Goal',
        'description': 'Desc',
        'target_value': '100'
    }, follow_redirects=True)
    assert resp.status_code == 200
    
    with test_app.app_context():
        g = Goal.query.filter_by(title='New Goal').first()
        assert g is not None
        assert g.team_id == sample_team
        assert g.target_value == 100
        assert g.status == 'ACTIVE'

def test_admin_create_goal_validation(client, test_app, sample_team):
    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'

    # Blank title
    client.post('/admin/goals/create', data={'team_id': sample_team, 'title': '   ', 'target_value': '100'})
    # Invalid target
    client.post('/admin/goals/create', data={'team_id': sample_team, 'title': 'Valid', 'target_value': '-10'})
    client.post('/admin/goals/create', data={'team_id': sample_team, 'title': 'Valid', 'target_value': '0'})
    client.post('/admin/goals/create', data={'team_id': sample_team, 'title': 'Valid', 'target_value': 'abc'})
    # Invalid team
    client.post('/admin/goals/create', data={'team_id': 9999, 'title': 'Valid', 'target_value': '100'})

    with test_app.app_context():
        assert Goal.query.count() == 0

def test_admin_edit_goal(client, test_app, sample_team):
    with test_app.app_context():
        g = Goal(team_id=sample_team, title='Old', target_value=10)
        db.session.add(g)
        db.session.commit()
        gid = g.id

    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'
        
    client.post(f'/admin/goals/{gid}/edit', data={
        'title': 'New',
        'description': 'New Desc',
        'target_value': '50'
    })
    
    with test_app.app_context():
        g = Goal.query.get(gid)
        assert g.title == 'New'
        assert g.description == 'New Desc'
        assert g.target_value == 50
        assert g.team_id == sample_team # Team id shouldn't change

def test_admin_status_goal(client, test_app, sample_team):
    with test_app.app_context():
        g = Goal(team_id=sample_team, title='Status', target_value=10, status='ACTIVE')
        db.session.add(g)
        db.session.commit()
        gid = g.id

    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = 'lanooshabdo7@gmail.com'

    client.post(f'/admin/goals/{gid}/status', data={'status': 'ACHIEVED'})
    
    with test_app.app_context():
        assert Goal.query.get(gid).status == 'ACHIEVED'

def test_goal_admin_requires_auth(client, sample_team):
    # Unauthenticated
    resp = client.post('/admin/goals/create', data={'team_id': sample_team, 'title': 'G', 'target_value': '10'})
    assert resp.status_code in (302, 403)
    
    # Volunteer
    with client.session_transaction() as sess:
        sess['user_id'] = 1
    resp = client.post('/admin/goals/create', data={'team_id': sample_team, 'title': 'G', 'target_value': '10'})
    assert resp.status_code in (302, 403)

def test_goal_progress_is_derived_from_ledger(test_app, sample_team):
    with test_app.app_context():
        # Setup team event and hours
        ev = Event(title='Ev', description='Test event for goal progress', date='2030-01-01', time='10:00', location='L', event_hours=5, team_id=sample_team)
        db.session.add(ev)
        db.session.commit()
        
        hl = HourLedger(volunteer_id=1, event_id=ev.id, hours=5.0, reason='attendance')
        db.session.add(hl)
        db.session.commit()
        
        from services.team import TeamContributionService
        prog = TeamContributionService.get_team_progress(sample_team)
        assert prog == 5.0
        
        # Verify goal has no standalone progress
        g = Goal(team_id=sample_team, title='Goal', target_value=100)
        db.session.add(g)
        db.session.commit()
        assert not hasattr(g, 'progress_hours')