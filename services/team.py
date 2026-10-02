from app import db, HourLedger, Event, Team

class TeamContributionService:
    @staticmethod
    def get_team_progress(team_id):
        """
        Returns total authoritative hours recorded for events belonging to this team.
        """
        hours = db.session.query(db.func.sum(HourLedger.hours))\
            .join(Event, HourLedger.event_id == Event.id)\
            .filter(Event.team_id == team_id)\
            .scalar()
        return hours or 0.0


    @staticmethod
    def get_bulk_team_progress(team_ids):
        """
        Returns a dict mapping team_id to total authoritative hours.
        """
        if not team_ids:
            return {}
        results = db.session.query(Event.team_id, db.func.sum(HourLedger.hours))            .join(HourLedger, HourLedger.event_id == Event.id)            .filter(Event.team_id.in_(team_ids))            .group_by(Event.team_id)            .all()
        return {r[0]: (r[1] or 0.0) for r in results}

    @staticmethod
    def get_volunteer_contribution(volunteer_id, team_id):
        """
        Returns total authoritative hours recorded by a volunteer for events belonging to this team.
        """
        hours = db.session.query(db.func.sum(HourLedger.hours))\
            .join(Event, HourLedger.event_id == Event.id)\
            .filter(HourLedger.volunteer_id == volunteer_id, Event.team_id == team_id)\
            .scalar()
        return hours or 0.0


class EventTeamAssignmentService:
    @staticmethod
    def is_historically_locked(event):
        if getattr(event, 'is_completed', False):
            return True
        has_ledger = db.session.query(HourLedger.query.filter_by(event_id=event.id).exists()).scalar()
        return bool(has_ledger)

    @staticmethod
    def get_bulk_historical_locks(events):
        event_ids = [ev.id for ev in events]
        if not event_ids:
            return {}
            
        # 1 grouped/existence query for HourLedger using EXISTS logic mapped via event_id
        # Actually a distinct query of event_ids that have ledgers is equivalent and perfectly scales
        ledger_event_ids_tuples = db.session.query(HourLedger.event_id).filter(HourLedger.event_id.in_(event_ids)).distinct().all()
        ledger_event_ids = {r[0] for r in ledger_event_ids_tuples}
        
        lock_map = {}
        for ev in events:
            if getattr(ev, 'is_completed', False) or ev.id in ledger_event_ids:
                lock_map[ev.id] = True
            else:
                lock_map[ev.id] = False
        return lock_map
        
    @staticmethod
    def assign_team(event, target_team_id):
        try:
            # 1. Lock the Event row to prevent concurrency race with HourLedger additions
            event_locked = db.session.query(Event).filter_by(id=event.id).with_for_update().first()
            if not event_locked:
                return False, "Event not found."
                
            # 2. Check historical lock against current DB state
            if EventTeamAssignmentService.is_historically_locked(event_locked):
                return False, "Event is historically locked and cannot change teams."
                
            # 3. Validate target Team
            if target_team_id is not None:
                team = db.session.get(Team, target_team_id)
                if not team:
                    return False, "Target team does not exist."
                if not team.is_active:
                    return False, "Cannot assign to an inactive team."
                event_locked.team_id = team.id
            else:
                event_locked.team_id = None
                
            # 4. Commit mutation
            db.session.commit()
            
            # Keep original event object in sync
            event.team_id = event_locked.team_id
            return True, "Team assignment updated."
        except Exception as e:
            db.session.rollback()
            return False, "Database error during assignment."

