import os
import sys
import pytest

os.environ.setdefault('FLASK_ENV', 'development')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, Volunteer, Interest, Skill

@pytest.fixture
def test_volunteer(test_app):
    with test_app.app_context():
        v = Volunteer(name='Test Vol', email='test_vol_signals@test.com', phone='0790000999', password_hash='x', status='approved')
        db.session.add(v)
        db.session.commit()
        return v.id

def test_interest_create_read_update_remove(test_app, test_volunteer):
    with test_app.app_context():
        i1 = Interest(name="Education")
        i2 = Interest(name="Health")
        db.session.add_all([i1, i2])
        db.session.commit()

        v = Volunteer.query.get(test_volunteer)
        v.interests_rel.append(i1)
        v.interests_rel.append(i2)
        db.session.commit()

        # Read
        v_check = Volunteer.query.get(test_volunteer)
        assert len(v_check.interests_rel) == 2
        names = {i.name for i in v_check.interests_rel}
        assert "Education" in names
        assert "Health" in names

        # Update / Remove
        v_check.interests_rel.remove(i1)
        db.session.commit()

        v_check2 = Volunteer.query.get(test_volunteer)
        assert len(v_check2.interests_rel) == 1
        assert v_check2.interests_rel[0].name == "Health"

def test_skill_create_read_update_remove(test_app, test_volunteer):
    with test_app.app_context():
        s1 = Skill(name="Programming")
        s2 = Skill(name="First Aid")
        db.session.add_all([s1, s2])
        db.session.commit()

        v = Volunteer.query.get(test_volunteer)
        v.structured_skills.append(s1)
        db.session.commit()

        v_check = Volunteer.query.get(test_volunteer)
        assert len(v_check.structured_skills) == 1
        assert v_check.structured_skills[0].name == "Programming"

        # unique constraint test
        from sqlalchemy.exc import IntegrityError
        s_dup = Skill(name="Programming")
        db.session.add(s_dup)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

def test_no_duplicate_relationships(test_app, test_volunteer):
    with test_app.app_context():
        # Clean up existing relationships
        v = Volunteer.query.get(test_volunteer)
        v.interests_rel.clear()
        v.structured_skills.clear()
        db.session.commit()

        i = Interest(name="Environment")
        db.session.add(i)
        db.session.commit()

        v.interests_rel.append(i)
        db.session.commit()

        # Try appending same interest again
        # In SQLAlchemy lists, appending again might work in-memory but unique constraint on relationship should prevent insert, 
        # or we should manually prevent it. Wait, the association table has (volunteer_id, interest_id) as composite primary key.
        # This prevents duplicate relationships at the database level!
        from sqlalchemy.exc import IntegrityError
        try:
            v.interests_rel.append(i)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        
        # Reload and check
        v_check = Volunteer.query.get(test_volunteer)
        assert len(v_check.interests_rel) == 1
