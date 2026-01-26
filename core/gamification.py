import datetime
from sqlalchemy.orm import Session
from db.models import UserStats, Attempt, Achievement
import uuid

from core.rank_system import get_rank_info

def update_user_stats(db: Session, last_session_date: datetime.date, correct_count: int, total_questions: int, eje_breakdown: dict = None, user_id: int = None):
    """
    Actualiza puntos y rachas del usuario aplicando pesos GOA.
    """
    if not user_id: return None
    
    stats = db.query(UserStats).filter_by(user_id=user_id).first()
    if not stats:
        stats = UserStats(user_id=user_id, current_streak=0, max_streak=0, total_points=0, last_activity=datetime.datetime.utcnow())
        db.add(stats)
        db.flush()

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    # Initialize Nulls (Sanity check for migrations)
    if stats.current_streak is None: stats.current_streak = 0
    if stats.max_streak is None: stats.max_streak = 0
    if stats.total_points is None: stats.total_points = 0

    # Lógica de Racha
    last_date = stats.last_activity.date()
    if last_date != today:
        if last_date == yesterday:
            stats.current_streak += 1
        else:
            stats.current_streak = 1
        
    if stats.current_streak > stats.max_streak:
        stats.max_streak = stats.current_streak

    # Ponderación GOA 2667
    # Si no hay desglose, asumimos proporcionalidad simple
    if not eje_breakdown:
        # Fallback para sesiones mixtas sin tags precisos
        score_percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0
        is_passed = score_percentage >= 70
        session_points = correct_count * 10 
    else:
        # Cálculo Realista por Pesos
        # eje_breakdown = {"FUNCIONAL": (correct, total), ...}
        total_weighted = 0.0
        
        # Funcional (60%)
        f_c, f_t = eje_breakdown.get("FUNCIONAL", (0, 0))
        f_score = (f_c / f_t * 60) if f_t > 0 else 0
        is_passed = (f_c / f_t * 100 >= 70) if f_t > 0 else True # Eliminatorio
        
        # Comportamental (20%)
        c_c, c_t = eje_breakdown.get("COMPORTAMENTAL", (0, 0))
        c_score = (c_c / c_t * 20) if c_t > 0 else 0
        
        # Integridad (20%)
        i_c, i_t = eje_breakdown.get("INTEGRIDAD", (0, 0))
        i_score = (i_c / i_t * 20) if i_t > 0 else 0
        
        total_weighted = f_score + c_score + i_score
        session_points = int(total_weighted * 2) # Factor de puntos ajustable

    if stats.current_streak > 1:
        session_points += (stats.current_streak * 5)
        
    old_rank, _ = get_rank_info(stats.total_points)
    stats.total_points += session_points
    new_rank, _ = get_rank_info(stats.total_points)
    
    stats.last_activity = datetime.datetime.utcnow()
    
    # Verificar logros
    new_achievements = check_new_achievements(db, stats, correct_count, total_questions, user_id=user_id)
    
    db.commit()
    
    return stats, session_points, new_achievements, (new_rank['name'] if new_rank['name'] != old_rank['name'] else None), is_passed

def check_new_achievements(db: Session, stats: UserStats, correct_count: int, total_questions: int, user_id: int = None):
    """Verifica y desbloquea nuevos logros."""
    already_unlocked = [a.name for a in db.query(Achievement).filter_by(user_id=user_id).all()]
    new_ones = []

    def unlock(name, desc, icon):
        if name not in already_unlocked:
            ach = Achievement(user_id=user_id, name=name, description=desc, icon=icon)
            db.add(ach)
            new_ones.append(ach)

    # REGLAS DE LOGROS
    unlock("Primer Paso", "Completaste tu primer simulacro.", "🚶")
    
    if stats.current_streak >= 3:
        unlock("Constancia", "Racha de 3 días aprendiendo.", "🔥")
        
    if stats.current_streak >= 7:
        unlock("Imparable", "Racha de una semana completa.", "⚡")

    if total_questions >= 10 and correct_count == total_questions:
        unlock("Perfección", "Simulacro perfecto (mínimo 10 preguntas).", "🎯")

    if stats.total_points >= 1500:
        unlock("Veterano", "Alcanzaste el rango de Auditor Senior.", "🛡️")

    return new_ones
