import os
import sys
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

os.environ.setdefault('FLASK_ENV', 'development')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, Volunteer, TrainingCourse, TrainingModule, TrainingProgress

def test_course_creation_and_persistence(test_app):
    with test_app.app_context():
        course = TrainingCourse(title="Intro to Volunteering", description="Basic principles")
        db.session.add(course)
        db.session.commit()
        
        fetched = TrainingCourse.query.get(course.id)
        assert fetched is not None
        assert fetched.title == "Intro to Volunteering"
        assert not fetched.is_published

def test_module_belongs_to_course(test_app):
    with test_app.app_context():
        course = TrainingCourse(title="Advanced Communication")
        db.session.add(course)
        db.session.commit()
        
        mod1 = TrainingModule(course_id=course.id, title="Active Listening", position=1)
        mod2 = TrainingModule(course_id=course.id, title="Conflict Resolution", position=2)
        db.session.add_all([mod1, mod2])
        db.session.commit()
        
        fetched_course = TrainingCourse.query.get(course.id)
        assert len(fetched_course.modules) == 2
        
        # Test cascade delete
        db.session.delete(fetched_course)
        db.session.commit()
        
        assert TrainingModule.query.filter_by(course_id=course.id).count() == 0

def test_volunteer_progress_relationships(test_app):
    with test_app.app_context():
        v = Volunteer(name="Train Vol", email="train@test.com", phone="0799999991", password_hash="x")
        c = TrainingCourse(title="Safety")
        db.session.add_all([v, c])
        db.session.commit()
        
        m = TrainingModule(course_id=c.id, title="First Aid")
        db.session.add(m)
        db.session.commit()
        
        prog = TrainingProgress(volunteer_id=v.id, module_id=m.id, is_completed=True, completed_at=datetime.utcnow())
        db.session.add(prog)
        db.session.commit()
        
        # Check reverse relationships
        assert len(v.training_progress) == 1
        assert v.training_progress[0].module.title == "First Aid"
        assert m.progress_records[0].volunteer_rel.name == "Train Vol"

def test_invalid_foreign_key_rejected(test_app):
    with test_app.app_context():
        invalid_module = TrainingModule(course_id=99999, title="Nowhere")
        db.session.add(invalid_module)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        
        v = Volunteer(name="FK Vol", email="fk@test.com", phone="0799999992", password_hash="x")
        db.session.add(v)
        db.session.commit()
        
        invalid_prog = TrainingProgress(volunteer_id=v.id, module_id=99999)
        db.session.add(invalid_prog)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

def test_duplicate_progress_prevented(test_app):
    with test_app.app_context():
        v = Volunteer(name="Dup Vol", email="dup@test.com", phone="0799999993", password_hash="x")
        c = TrainingCourse(title="Dup Course")
        db.session.add_all([v, c])
        db.session.commit()
        
        m = TrainingModule(course_id=c.id, title="Dup Mod")
        db.session.add(m)
        db.session.commit()
        
        prog1 = TrainingProgress(volunteer_id=v.id, module_id=m.id)
        db.session.add(prog1)
        db.session.commit()
        
        prog2 = TrainingProgress(volunteer_id=v.id, module_id=m.id)
        db.session.add(prog2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()