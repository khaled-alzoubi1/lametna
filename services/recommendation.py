from app import Event, EventRegistration, Volunteer, can_register

class RecommendationResult:
    def __init__(self, event, score, explanation=None):
        self.event = event
        self.score = score
        self.explanation = explanation

class RecommendationService:
    @staticmethod
    def get_recommendations_for_volunteer(volunteer, limit=3):
        """
        Deterministic recommendation engine for a volunteer based on available signals.
        Returns a list of RecommendationResult.
        """
        # Fetch only events that are definitely not CANCELLED or COMPLETED to minimize payload
        # This is an optimization; the true business logic is enforced via can_register() below.
        potential_events = Event.query.filter(
            Event.status.notin_(['CANCELLED', 'COMPLETED']) | Event.status.is_(None)
        ).all()
        
        # Fetch user's existing registrations in one query (O(1) query)
        existing_regs = EventRegistration.query.filter_by(volunteer_id=volunteer.id).all()
        excluded_event_ids = {
            reg.event_id for reg in existing_regs 
            if reg.status in ['REGISTERED', 'WAITLISTED', 'ATTENDED']
        }
        
        # Pre-compute volunteer sets for fast in-memory matching
        vol_interest_ids = {i.id for i in volunteer.interests_rel}
        vol_skill_ids = {s.id for s in volunteer.structured_skills}
        vol_city = volunteer.city.strip().lower() if volunteer.city else ""
        
        recommendations = []
        
        for event in potential_events:
            # P1 compliance: Use authoritative eligibility logic
            if not can_register(event):
                continue
                
            # Exclude already registered/waitlisted/attended
            if event.id in excluded_event_ids:
                continue
                
            score = 0
            explanation = None
            
            ev_interest_ids = {i.id for i in event.interests_rel}
            ev_skill_ids = {s.id for s in event.structured_skills}
            
            # Signal 1: Interest Match (Highest Priority)
            if vol_interest_ids & ev_interest_ids:
                score += 20
                if not explanation:
                    explanation = "يناسب اهتماماتك" # Matches your interests
                    
            # Signal 2: Skill Match
            if vol_skill_ids & ev_skill_ids:
                score += 15
                if not explanation:
                    explanation = "مرتبط بمهارة اخترتها" # Related to a skill you selected
            
            # Signal 3: Geographic Relevance
            ev_location = event.location.strip().lower() if event.location else ""
            if vol_city and len(vol_city) > 2 and (vol_city in ev_location or ev_location in vol_city):
                score += 10
                if not explanation:
                    explanation = "نشاط في مدينتك" # Activity in your city
                
            # Signal 4: Availability (Weak discovery signal)
            if event.remaining_seats > 0:
                score += 5
                if not explanation:
                    explanation = "مقاعد متاحة للتسجيل" # Seats available
                    
            # Signal 5: New Volunteer Push
            if volunteer.attended_events_count == 0 and not explanation:
                score += 3
                explanation = "نشاط مقترح لتبدأ تطوعك" # Suggested activity to start volunteering
                
            recommendations.append(RecommendationResult(event, score, explanation))
            
        # Sort deterministically: highest score first, tie-break by event.id descending
        recommendations.sort(key=lambda r: (r.score, r.event.id), reverse=True)
        
        return recommendations[:limit]
