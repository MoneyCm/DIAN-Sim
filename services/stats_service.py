from datetime import datetime
from sqlalchemy import func
from db.models import Skill, Attempt, Question, UserStats
from db.session import SessionLocal

class StatsService:
    @staticmethod
    def record_attempt(user_id, question_id, chosen_key, is_correct, time_sec=None):
        """Records an attempt and updates skill mastery."""
        db = SessionLocal()
        try:
            # 1. Save Attempt
            attempt = Attempt(
                user_id=user_id,
                question_id=question_id,
                chosen_key=chosen_key,
                is_correct=is_correct,
                time_sec=time_sec
            )
            db.add(attempt)
            
            # 2. Update User Stats (Points & Streak)
            stats = db.query(UserStats).filter_by(user_id=user_id).first()
            if not stats:
                stats = UserStats(user_id=user_id, total_points=0, current_streak=0)
                db.add(stats)
            
            if is_correct:
                stats.total_points += 10 # Base points
            
            # 3. Update Skill Mastery
            q = db.query(Question).get(question_id)
            if q:
                # Find or Create Skill entry for this topic
                skill = db.query(Skill).filter_by(
                    user_id=user_id, 
                    topic=q.topic
                ).first()
                
                if not skill:
                    skill = Skill(
                        user_id=user_id,
                        track=q.track,
                        competency=q.competency,
                        topic=q.topic,
                        macro_dominio=q.macro_dominio,
                        micro_competencia=q.micro_competencia,
                        mastery_score=0.0
                    )
                    db.add(skill)
                
                # Update Moving Average (Simple alpha decay)
                alpha = 0.2
                outcome = 100.0 if is_correct else 0.0
                skill.mastery_score = (skill.mastery_score * (1 - alpha)) + (outcome * alpha)
                skill.updated_at = datetime.now()
                
            db.commit()
            return True
        except Exception as e:
            print(f"Error recording attempt: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    @staticmethod
    def get_weakest_topics(user_id, limit=5):
        """Returns list of skills with mastery < 70"""
        db = SessionLocal()
        skills = db.query(Skill).filter(
            Skill.user_id == user_id,
            Skill.mastery_score < 70
        ).order_by(Skill.mastery_score.asc()).limit(limit).all()
        db.close()
        return skills
