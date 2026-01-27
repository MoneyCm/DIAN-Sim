import json
from sqlalchemy import or_, and_, func
from db.models import Question, UserOPEC

class QuestionService:
    @staticmethod
    def get_questions_for_user(db, user_id):
        """
        Fetches questions filtered by the user's OPEC profile.
        Returns a list of Question objects.
        """
        # 1. Get User Profile
        user_opec = db.query(UserOPEC).filter_by(user_id=user_id, is_active=True).first()
        
        # Base Query
        query = db.query(Question)
        
        # If no profile, maybe return all? or none? Let's return all for now (Admin view)
        if not user_opec:
            return query.all()

        # 2. Logic for OPEC 236844 (Gestor II - Tributaria/Cobranzas)
        if str(user_opec.opec_number) == "236844":
            print(f"Applying filters for OPEC {user_opec.opec_number} (Cesar Rules)...")
            
            # A. Exclude Customs/Foreign Trade (Negative Filter)
            forbidden_keywords = [
                'Aduan', 'Import', 'Export', 'Tránsito', 'Transito', 
                'Cabotaje', 'Zona Franca', 'Cambiari', 'Transporte', 
                'Arancel'
            ]
            for kw in forbidden_keywords:
                query = query.filter(
                    and_(
                        ~Question.topic.ilike(f'%{kw}%'), 
                        ~Question.competency.ilike(f'%{kw}%')
                    )
                )

            # B. Strict GOA: Functional questions must have 3 options
            # Heuristic: Functional = NOT Behavioral
            # We filter out questions that are FUNCTIONAL (not behavioral) AND have != 3 options
            
            # Using Python filtering for JSON length might be slow in SQL, 
            # but usually we can check string length or just fetch and filter in python for 955 items 
            # (Fetching 1000 items is fast).
            
            all_candidates = query.all()
            final_questions = []
            
            for q in all_candidates:
                # Check 1: Topic match (Double check 'Gestor II')
                # If we want to be strict that it MUST satisfy Gestor II logic
                # For now, the negative filter handles the "Topic" part well enough as verified in previous steps.
                
                # Check 2: GOA Options Format
                is_behavioral = any(x in q.competency.lower() or x in q.topic.lower() for x in ['comportamental', 'conductual', 'integridad', 'valores', 'ética', 'etica'])
                
                try:
                    opts = json.loads(q.options_json)
                    if not is_behavioral and len(opts) != 3:
                        continue # Skip non-compliant functional questions
                except:
                    continue # Skip malformed questions

                # Check 3: Situational (Stem starts with SITUACIÓN)
                if not is_behavioral:
                    if "SITUACIÓN" not in q.stem.upper():
                         continue
                
                final_questions.append(q)
            
            return final_questions

        # Default for other OPECs (Return all for now)
        return query.all()
