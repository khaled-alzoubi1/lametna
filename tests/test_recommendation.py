import os
import sys
import pytest

os.environ.setdefault('FLASK_ENV', 'development')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Event, Volunteer, EventRegistration, Interest, Skill
from services.recommendation import RecommendationService
import uuid


@pytest.fixture
def unique_volunteer(test_app):
    with test_app.app_context():
        uniq = str(uuid.uuid4())[:8]
        v = Volunteer(name='IntV', email=f'rec_v_{uniq}@test.com', phone=f'079{uniq}',
                      password_hash='x', status='approved')
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

def test_recommendation_excludes_completed_cancelled(test_app, unique_volunteer):
    with test_app.app_context():
        Event.query.delete()
        db.session.commit()

        ev1 = Event(title='Valid Event', description='desc', date='2030-01-01', time='10:00', location='Amman', event_hours=1, status='REGISTRATION_OPEN')
        ev2 = Event(title='Completed Event', description='desc', date='2030-01-01', time='10:00', location='Amman', event_hours=1, status='COMPLETED')
        ev3 = Event(title='Cancelled Event', description='desc', date='2030-01-01', time='10:00', location='Amman', event_hours=1, status='CANCELLED')
        
        db.session.add_all([ev1, ev2, ev3])
        db.session.commit()
        
        v = Volunteer.query.get(unique_volunteer)
        recs = RecommendationService.get_recommendations_for_volunteer(v)
        
        assert len(recs) == 1
        assert recs[0].event.title == 'Valid Event'

def test_recommendation_excludes_registered_waitlisted(test_app, unique_volunteer):
    with test_app.app_context():
        Event.query.delete()
        db.session.commit()

        ev1 = Event(title='Event 1', description='desc', date='2030-01-01', time='10:00', location='Amman', event_hours=1, status='REGISTRATION_OPEN')
        ev2 = Event(title='Event 2', description='desc', date='2030-01-01', time='10:00', location='Amman', event_hours=1, status='REGISTRATION_OPEN')
        db.session.add_all([ev1, ev2])
        db.session.commit()
        
        reg1 = EventRegistration(volunteer_id=unique_volunteer, event_id=ev1.id, status='REGISTERED')
        db.session.add(reg1)
        db.session.commit()
        
        v = Volunteer.query.get(unique_volunteer)
        recs = RecommendationService.get_recommendations_for_volunteer(v)
        
        assert len(recs) == 1
        assert recs[0].event.title == 'Event 2'

def test_recommendation_scoring_geographic_and_ordering(test_app, unique_volunteer):
    with test_app.app_context():
        Event.query.delete()
        
        v = Volunteer.query.get(unique_volunteer)
        v.city = 'Zarqa'
        db.session.commit()
        
        ev1 = Event(title='Amman Event', description='desc', date='2030-01-01', time='10:00', location='Amman', event_hours=1, capacity=10)
        ev2 = Event(title='Zarqa Event', description='desc', date='2030-01-01', time='10:00', location='Zarqa Center', event_hours=1, capacity=10)
        db.session.add_all([ev1, ev2])
        db.session.commit()
        
        recs = RecommendationService.get_recommendations_for_volunteer(v)
        
        assert len(recs) == 2
        assert recs[0].event.title == 'Zarqa Event'
        assert recs[0].score > recs[1].score
        assert recs[0].explanation == "نشاط في مدينتك"

def test_recommendation_fallback_insufficient_data(test_app, unique_volunteer):
    with test_app.app_context():
        Event.query.delete()
        
        v = Volunteer.query.get(unique_volunteer)
        v.city = 'Irbid'
        v.attended_events_count = 5
        db.session.commit()
        
        ev1 = Event(title='Amman Event Full', description='desc', date='2030-01-01', time='10:00', location='Amman', event_hours=1, capacity=0)
        db.session.add(ev1)
        db.session.commit()
        
        recs = RecommendationService.get_recommendations_for_volunteer(v)
        
        assert len(recs) == 1
        assert recs[0].score == 0
        assert recs[0].explanation is None

def test_recommendation_interest_match(test_app, unique_volunteer):
    with test_app.app_context():
        Event.query.delete()
        
        i_edu = Interest(name="Education")
        i_health = Interest(name="Health")
        db.session.add_all([i_edu, i_health])
        db.session.commit()
        
        v = Volunteer.query.get(unique_volunteer)
        v.interests_rel.append(i_edu)
        db.session.commit()
        
        ev1 = Event(title='Edu Event', description='desc', date='2030-01-01', time='10:00', location='Amman', event_hours=1, capacity=10)
        ev1.interests_rel.append(i_edu)
        
        ev2 = Event(title='Health Event', description='desc', date='2030-01-01', time='10:00', location='Amman', event_hours=1, capacity=10)
        ev2.interests_rel.append(i_health)
        
        db.session.add_all([ev1, ev2])
        db.session.commit()
        
        recs = RecommendationService.get_recommendations_for_volunteer(v)
        
        assert len(recs) == 2
        assert recs[0].event.title == 'Edu Event'
        assert "يناسب اهتماماتك" in recs[0].explanation
        # Score check: +20 for interest, +5 for availability, +3 for new volunteer (attended=0)
        assert recs[0].score >= 20

def test_recommendation_skill_match(test_app, unique_volunteer):
    with test_app.app_context():
        Event.query.delete()
        
        s_prog = Skill(name="Programming")
        db.session.add(s_prog)
        db.session.commit()
        
        v = Volunteer.query.get(unique_volunteer)
        v.structured_skills.append(s_prog)
        db.session.commit()
        
        ev1 = Event(title='Tech Event', description='desc', date='2030-01-01', time='10:00', location='Amman', event_hours=1, capacity=10)
        ev1.structured_skills.append(s_prog)
        
        db.session.add(ev1)
        db.session.commit()
        
        recs = RecommendationService.get_recommendations_for_volunteer(v)
        assert len(recs) == 1
        assert "مرتبط بمهارة اخترتها" in recs[0].explanation
        assert recs[0].score >= 15
