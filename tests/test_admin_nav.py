"""
Regression tests for Admin navigation tabs and Encoding fixes.

Verifies that every Admin tab section receives its required template context,
renders without blank/empty content, and contains correct Arabic text instead
of mojibake/corrupted encodings.
"""
import pytest
from app import app, db, Volunteer, Team, Goal, SystemSettings
from werkzeug.security import generate_password_hash


ADMIN_EMAIL = "lanooshabdo7@gmail.com"
ADMIN_PASSWORD = "AdminPass!123"

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

@pytest.fixture
def admin_client(client):
    """Authenticated admin test client with a seeded admin volunteer."""
    with app.app_context():
        admin = Volunteer(
            name="Test Admin Nav",
            email=ADMIN_EMAIL,
            phone="0799999999",
            password_hash=generate_password_hash(ADMIN_PASSWORD),
            status='approved'
        )
        db.session.add(admin)
        db.session.commit()

    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_email'] = ADMIN_EMAIL

    return client


def test_admin_dashboard_renders_200(admin_client):
    """Admin dashboard should return 200 and not crash."""
    resp = admin_client.get('/admin')
    assert resp.status_code == 200


def test_admin_dashboard_goals_tab_present(admin_client):
    """goalsTab div must be present - confirms goals context was passed."""
    resp = admin_client.get('/admin')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'id="goalsTab"' in html, "goalsTab section missing from rendered admin page"


def test_admin_dashboard_goals_data_rendered(admin_client):
    """When goals exist they should appear in the goalsTab section with correct encoding."""
    with app.app_context():
        team = Team(name="فريق الاختبار", is_active=True)
        db.session.add(team)
        db.session.flush()
        goal = Goal(team_id=team.id, title="هدف تجريبي", target_value=100)
        db.session.add(goal)
        db.session.commit()

    resp = admin_client.get('/admin')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert "هدف تجريبي" in html, "Goal title not rendered correctly in admin goalsTab"


def test_admin_dashboard_teams_tab_present(admin_client):
    """teamsTab div must be present."""
    resp = admin_client.get('/admin')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'id="teamsTab"' in html, "teamsTab section missing from rendered admin page"


def test_admin_dashboard_active_teams_in_events_tab(admin_client):
    """active_teams should populate the team dropdown in the events creation form."""
    with app.app_context():
        team = Team(name="الفريق النشط", is_active=True)
        db.session.add(team)
        db.session.commit()

    resp = admin_client.get('/admin')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert "الفريق النشط" in html, "Active team not appearing in events tab team dropdown"


def test_admin_dashboard_sys_settings_banner_rendered(admin_client):
    """sys_settings must be passed so banner section renders without UndefinedError."""
    with app.app_context():
        sys_s = SystemSettings(banner_text="إعلان اختباري", is_banner_active=False)
        db.session.add(sys_s)
        db.session.commit()

    resp = admin_client.get('/admin')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert "إعلان اختباري" in html, "sys_settings banner_text not rendered in admin page"


def test_admin_dashboard_training_tab_present(admin_client):
    """trainingTab div must be present."""
    resp = admin_client.get('/admin')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'id="trainingTab"' in html, "trainingTab section missing from rendered admin page"


def test_admin_dashboard_excuses_tab_present(admin_client):
    """excusesTab div must be present."""
    resp = admin_client.get('/admin')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'id="excusesTab"' in html, "excusesTab section missing from rendered admin page"


def test_admin_dashboard_non_admin_denied(client):
    """Non-admin should not be able to access /admin."""
    resp = client.get('/admin', follow_redirects=True)
    html = resp.data.decode('utf-8')
    assert 'id="goalsTab"' not in html, "Non-admin should not see admin goals tab"

def test_admin_dashboard_teams_tab_encoding_is_clean(admin_client):
    """Verify teamsTab text has correct Arabic and no mojibake/corrupted encodings."""
    resp = admin_client.get('/admin')
    html = resp.data.decode('utf-8')
    
    # Check for correct arabic string
    assert "إدارة الفرق" in html, "Correct Arabic text 'إدارة الفرق' missing from teamsTab"
    
    # Check that known mojibake from before is gone
    assert "OOOO1O" not in html, "Garbled text OOOO1O found in HTML"
    assert "U,U?O1U," not in html, "Garbled text U,U?O1U, found in HTML"

def test_admin_dashboard_goals_tab_encoding_is_clean(admin_client):
    """Verify goalsTab text has correct Arabic and no mojibake/corrupted encodings."""
    resp = admin_client.get('/admin')
    html = resp.data.decode('utf-8')
    
    # Check for correct arabic string
    assert "أهداف الفريق" in html, "Correct Arabic text 'أهداف الفريق' missing from goalsTab"
    
    # Check that known mojibake from before is gone
    assert "O_O O" not in html, "Garbled text O_O O found in HTML"
