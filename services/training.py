from app import db, TrainingCourse, TrainingModule
from sqlalchemy.exc import IntegrityError
import urllib.parse

def is_valid_url(url):
    if not url:
        return True
    parsed = urllib.parse.urlparse(url)
    return bool(parsed.scheme in ['http', 'https'] and parsed.netloc)

class TrainingAdminService:
    @staticmethod
    def create_course(title, description, cover_image_url):
        title = (title or '').strip()
        if not title:
            return False, "Course title is required."
        
        if cover_image_url and not is_valid_url(cover_image_url):
            return False, "Invalid cover image URL."

        try:
            c = TrainingCourse(
                title=title[:200],
                description=(description or '').strip(),
                cover_image_url=(cover_image_url or '').strip()
            )
            db.session.add(c)
            db.session.commit()
            return True, "Course created successfully."
        except Exception as e:
            db.session.rollback()
            return False, "Database error during course creation."

    @staticmethod
    def edit_course(course_id, title, description, cover_image_url):
        try:
            c = db.session.get(TrainingCourse, course_id)
            if not c:
                return False, "Course not found."
                
            title = (title or '').strip()
            if not title:
                return False, "Course title is required."
            
            if cover_image_url and not is_valid_url(cover_image_url):
                return False, "Invalid cover image URL."
                
            c.title = title[:200]
            c.description = (description or '').strip()
            c.cover_image_url = (cover_image_url or '').strip()
            
            db.session.commit()
            return True, "Course updated successfully."
        except Exception as e:
            db.session.rollback()
            return False, "Database error during course update."

    @staticmethod
    def toggle_course_status(course_id):
        try:
            c = db.session.get(TrainingCourse, course_id)
            if not c:
                return False, "Course not found."
            c.is_published = not c.is_published
            db.session.commit()
            return True, "Course status updated."
        except Exception as e:
            db.session.rollback()
            return False, "Database error during toggle."

    @staticmethod
    def delete_course(course_id):
        try:
            c = db.session.get(TrainingCourse, course_id)
            if not c:
                return False, "Course not found."
            db.session.delete(c)
            db.session.commit()
            return True, "Course deleted successfully."
        except Exception as e:
            db.session.rollback()
            return False, "Database error during deletion."

    @staticmethod
    def create_module(course_id, title, description, content_type, content_url, position):
        try:
            c = db.session.get(TrainingCourse, course_id)
            if not c:
                return False, "Course not found."
                
            title = (title or '').strip()
            if not title:
                return False, "Module title is required."
                
            if content_url and not is_valid_url(content_url):
                return False, "Invalid content URL."
                
            # Safely parse position
            try:
                pos = int(position) if position else 0
                if pos < 0: pos = 0
                if pos > 10000: pos = 10000
            except (ValueError, TypeError):
                pos = 0

            m = TrainingModule(
                course_id=c.id,
                title=title[:200],
                description=(description or '').strip(),
                content_type=(content_type or '').strip()[:50],
                content_url=(content_url or '').strip(),
                position=pos
            )
            db.session.add(m)
            db.session.commit()
            return True, "Module created successfully."
        except Exception as e:
            db.session.rollback()
            return False, "Database error during module creation."

    @staticmethod
    def edit_module(module_id, title, description, content_type, content_url, position):
        try:
            m = db.session.get(TrainingModule, module_id)
            if not m:
                return False, "Module not found."
                
            title = (title or '').strip()
            if not title:
                return False, "Module title is required."
                
            if content_url and not is_valid_url(content_url):
                return False, "Invalid content URL."
                
            # Safely parse position
            try:
                pos = int(position) if position else m.position
                if pos < 0: pos = 0
                if pos > 10000: pos = 10000
            except (ValueError, TypeError):
                pos = m.position
                
            m.title = title[:200]
            m.description = (description or '').strip()
            m.content_type = (content_type or '').strip()[:50]
            m.content_url = (content_url or '').strip()
            m.position = pos
            
            db.session.commit()
            return True, "Module updated successfully."
        except Exception as e:
            db.session.rollback()
            return False, "Database error during module update."

    @staticmethod
    def delete_module(module_id):
        try:
            m = db.session.get(TrainingModule, module_id)
            if not m:
                return False, "Module not found."
            db.session.delete(m)
            db.session.commit()
            return True, "Module deleted successfully."
        except Exception as e:
            db.session.rollback()
            return False, "Database error during deletion."

class TrainingVolunteerService:


    @staticmethod
    def get_all_courses_progress(volunteer_id):
        from app import db, TrainingCourse, TrainingModule, TrainingProgress
        
        # Avoid N+1: fetch all published courses
        courses = TrainingCourse.query.filter_by(is_published=True).order_by(TrainingCourse.id.desc()).all()
        if not courses:
            return []
            
        course_ids = [c.id for c in courses]
        
        # 1. Total published modules per course
        module_counts = db.session.query(
            TrainingModule.course_id, 
            db.func.count(TrainingModule.id)
        ).filter(
            TrainingModule.course_id.in_(course_ids),
            TrainingModule.is_published == True
        ).group_by(TrainingModule.course_id).all()
        
        total_map = {cid: count for cid, count in module_counts}
        
        # 2. Completed published modules per course for this volunteer
        completed_counts = db.session.query(
            TrainingModule.course_id,
            db.func.count(TrainingProgress.id)
        ).join(
            TrainingModule, TrainingProgress.module_id == TrainingModule.id
        ).filter(
            TrainingModule.course_id.in_(course_ids),
            TrainingModule.is_published == True,
            TrainingProgress.volunteer_id == volunteer_id,
            TrainingProgress.is_completed == True
        ).group_by(TrainingModule.course_id).all()
        
        completed_map = {cid: count for cid, count in completed_counts}
        
        result = []
        for c in courses:
            total = total_map.get(c.id, 0)
            completed = completed_map.get(c.id, 0)
            
            if total == 0:
                perc = 0
                is_completed = False
            else:
                perc = int((completed / total) * 100)
                is_completed = (completed == total)
                
            result.append({
                'course': c,
                'progress': {
                    'total': total,
                    'completed': completed,
                    'percentage': perc,
                    'is_completed': is_completed
                }
            })
            
        return result
    @staticmethod
    def get_course_progress(volunteer_id, course_id):
        from app import db, TrainingCourse, TrainingModule, TrainingProgress
        
        # Guard: Check if course exists and is published
        course = TrainingCourse.query.filter_by(id=course_id, is_published=True).first()
        if not course:
            return {
                'total': 0,
                'completed': 0,
                'percentage': 0,
                'is_completed': False
            }
        
        # Total published modules
        total_modules = TrainingModule.query.filter_by(course_id=course_id, is_published=True).count()
        
        if total_modules == 0:
            return {
                'total': 0,
                'completed': 0,
                'percentage': 0,
                'is_completed': False
            }
            
        # Total completed published modules by this volunteer
        completed_modules = db.session.query(db.func.count(TrainingProgress.id)).join(
            TrainingModule, TrainingProgress.module_id == TrainingModule.id
        ).filter(
            TrainingModule.course_id == course_id,
            TrainingModule.is_published == True,
            TrainingProgress.volunteer_id == volunteer_id,
            TrainingProgress.is_completed == True
        ).scalar() or 0
        
        percentage = int((completed_modules / total_modules) * 100)
        is_completed = (completed_modules == total_modules)
        
        return {
            'total': total_modules,
            'completed': completed_modules,
            'percentage': percentage,
            'is_completed': is_completed
        }
    @staticmethod
    def mark_module_completed(volunteer_id, module_id):
        from app import TrainingProgress
        from datetime import datetime
        from flask import current_app
        try:
            progress = TrainingProgress.query.filter_by(volunteer_id=volunteer_id, module_id=module_id).first()
            if not progress:
                progress = TrainingProgress(
                    volunteer_id=volunteer_id,
                    module_id=module_id,
                    is_completed=True,
                    completed_at=datetime.utcnow()
                )
                from app import db
                db.session.add(progress)
            else:
                if not progress.is_completed:
                    progress.is_completed = True
                    progress.completed_at = datetime.utcnow()
            from app import db
            db.session.commit()
            return True, "تم إكمال الوحدة بنجاح."
        except IntegrityError as e:
            from app import db
            db.session.rollback()
            # Concurrency race condition: another concurrent request might have already created the record
            # Verify the target state is actually achieved before declaring success
            check_progress = TrainingProgress.query.filter_by(volunteer_id=volunteer_id, module_id=module_id).first()
            if check_progress and check_progress.is_completed:
                return True, "تم إكمال الوحدة بنجاح."
            
            if current_app:
                current_app.logger.error(f"IntegrityError marking module completed (V:{volunteer_id}, M:{module_id}) without achieving state: {str(e)}")
            return False, "حدث خطأ غير متوقع أثناء حفظ التقدم. يُرجى المحاولة لاحقاً."
        except Exception as e:
            from app import db
            db.session.rollback()
            # Log the raw error internally for debugging
            if current_app:
                current_app.logger.error(f"Error marking module completed (V:{volunteer_id}, M:{module_id}): {str(e)}")
            # Do NOT expose raw exception/database/internal messages to volunteers
            return False, "حدث خطأ غير متوقع أثناء حفظ التقدم. يُرجى المحاولة لاحقاً."
