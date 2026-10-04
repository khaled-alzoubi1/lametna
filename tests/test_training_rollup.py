
def test_course_rollup_0_completed(test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule
    from services.training import TrainingVolunteerService
    with test_app.app_context():
        c = TrainingCourse(title='Rollup1', is_published=True)
        db.session.add(c)
        db.session.commit()
        for i in range(3):
            db.session.add(TrainingModule(course_id=c.id, title=f'Mod {i}', is_published=True))
        db.session.commit()
        
        prog = TrainingVolunteerService.get_course_progress(volunteer1, c.id)
        assert prog['total'] == 3
        assert prog['completed'] == 0
        assert prog['percentage'] == 0
        assert prog['is_completed'] is False

def test_course_rollup_partial_and_full_completion(test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule, TrainingProgress
    from services.training import TrainingVolunteerService
    with test_app.app_context():
        c = TrainingCourse(title='Rollup2', is_published=True)
        db.session.add(c)
        db.session.commit()
        
        m1 = TrainingModule(course_id=c.id, title='Mod 1', is_published=True)
        m2 = TrainingModule(course_id=c.id, title='Mod 2', is_published=True)
        m3 = TrainingModule(course_id=c.id, title='Mod 3', is_published=True)
        db.session.add_all([m1, m2, m3])
        db.session.commit()
        
        # 1/3 completed
        db.session.add(TrainingProgress(volunteer_id=volunteer1, module_id=m1.id, is_completed=True))
        db.session.commit()
        
        prog1 = TrainingVolunteerService.get_course_progress(volunteer1, c.id)
        assert prog1['completed'] == 1
        assert prog1['percentage'] == 33
        assert prog1['is_completed'] is False
        
        # 2/3 completed
        db.session.add(TrainingProgress(volunteer_id=volunteer1, module_id=m2.id, is_completed=True))
        db.session.commit()
        
        prog2 = TrainingVolunteerService.get_course_progress(volunteer1, c.id)
        assert prog2['completed'] == 2
        assert prog2['percentage'] == 66
        assert prog2['is_completed'] is False
        
        # 3/3 completed
        db.session.add(TrainingProgress(volunteer_id=volunteer1, module_id=m3.id, is_completed=True))
        db.session.commit()
        
        prog3 = TrainingVolunteerService.get_course_progress(volunteer1, c.id)
        assert prog3['completed'] == 3
        assert prog3['percentage'] == 100
        assert prog3['is_completed'] is True

def test_course_rollup_ignores_unpublished_modules(test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule, TrainingProgress
    from services.training import TrainingVolunteerService
    with test_app.app_context():
        c = TrainingCourse(title='Rollup3', is_published=True)
        db.session.add(c)
        db.session.commit()
        
        m_pub = TrainingModule(course_id=c.id, title='Pub', is_published=True)
        m_unpub = TrainingModule(course_id=c.id, title='Unpub', is_published=False)
        db.session.add_all([m_pub, m_unpub])
        db.session.commit()
        
        # Complete the published module
        db.session.add(TrainingProgress(volunteer_id=volunteer1, module_id=m_pub.id, is_completed=True))
        db.session.commit()
        
        prog = TrainingVolunteerService.get_course_progress(volunteer1, c.id)
        # Total should only reflect published module (1). Thus 1/1 = 100%.
        assert prog['total'] == 1
        assert prog['completed'] == 1
        assert prog['percentage'] == 100
        assert prog['is_completed'] is True

def test_course_rollup_isolation(test_app, volunteer1, volunteer2):
    from app import db, TrainingCourse, TrainingModule, TrainingProgress
    from services.training import TrainingVolunteerService
    with test_app.app_context():
        c = TrainingCourse(title='Rollup4', is_published=True)
        db.session.add(c)
        db.session.commit()
        
        m = TrainingModule(course_id=c.id, title='Mod', is_published=True)
        db.session.add(m)
        db.session.commit()
        
        # Volunteer1 completes it
        db.session.add(TrainingProgress(volunteer_id=volunteer1, module_id=m.id, is_completed=True))
        db.session.commit()
        
        prog1 = TrainingVolunteerService.get_course_progress(volunteer1, c.id)
        assert prog1['is_completed'] is True
        
        # Volunteer2 should not see Volunteer1's progress
        prog2 = TrainingVolunteerService.get_course_progress(volunteer2, c.id)
        assert prog2['is_completed'] is False
        assert prog2['completed'] == 0

def test_course_rollup_zero_published_modules(test_app, volunteer1):
    from app import db, TrainingCourse
    from services.training import TrainingVolunteerService
    with test_app.app_context():
        c = TrainingCourse(title='Rollup5', is_published=True)
        db.session.add(c)
        db.session.commit()
        
        prog = TrainingVolunteerService.get_course_progress(volunteer1, c.id)
        assert prog['total'] == 0
        assert prog['completed'] == 0
        assert prog['percentage'] == 0
        assert prog['is_completed'] is False

def test_course_rollup_unpublished_course(test_app, volunteer1):
    from app import db, TrainingCourse, TrainingModule, TrainingProgress
    from services.training import TrainingVolunteerService
    with test_app.app_context():
        c = TrainingCourse(title='Rollup_Unpub_Course', is_published=False)
        db.session.add(c)
        db.session.commit()
        
        m = TrainingModule(course_id=c.id, title='Pub Mod', is_published=True)
        db.session.add(m)
        db.session.commit()
        
        # Volunteer completed it
        db.session.add(TrainingProgress(volunteer_id=volunteer1, module_id=m.id, is_completed=True))
        db.session.commit()
        
        # Because the course itself is unpublished, the rollup should return 0 progress
        prog = TrainingVolunteerService.get_course_progress(volunteer1, c.id)
        assert prog['total'] == 0
        assert prog['completed'] == 0
        assert prog['percentage'] == 0
        assert prog['is_completed'] is False

def test_course_rollup_nonexistent_course(test_app, volunteer1):
    from services.training import TrainingVolunteerService
    with test_app.app_context():
        # Nonexistent course ID 99999
        prog = TrainingVolunteerService.get_course_progress(volunteer1, 99999)
        assert prog['total'] == 0
        assert prog['completed'] == 0
        assert prog['percentage'] == 0
        assert prog['is_completed'] is False
