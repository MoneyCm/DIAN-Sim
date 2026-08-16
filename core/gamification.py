import datetime
from sqlalchemy.orm import Session
from db.models import UserStats, Attempt, Achievement
import uuid

from core.rank_system import get_rank_info

PRACTICE_TRACK_WEIGHTS = {
    "FUNCIONAL": 60,
    "COMPORTAMENTAL": 20,
    "INTEGRIDAD": 20,
}
PRACTICE_FUNCTIONAL_TARGET = 70.0
PRACTICE_SCORING_STATUS = "provisional_editable_not_official_exam_weighting"
PRACTICE_SCORING_DISCLOSURE = (
    "Índice interno de entrenamiento con pesos editables 60/20/20. "
    "No equivale a la calificación oficial del concurso ni asigna una "
    "ponderación a la OPEC 236769 sin confirmar primero su modalidad en SIMO."
)


def calculate_practice_index(eje_breakdown: dict | None) -> tuple[float, bool]:
    """Return the internal training index and functional practice-goal state.

    This deliberately does not model an official competition score. DIAN 2676
    publishes different weights by modality and employment characteristics,
    while the modality of an individual OPEC must come from SIMO evidence.
    """
    breakdown = eje_breakdown or {}
    total_weighted = 0.0
    for track, weight in PRACTICE_TRACK_WEIGHTS.items():
        correct, total = breakdown.get(track, (0, 0))
        if total > 0:
            total_weighted += correct / total * weight

    functional_correct, functional_total = breakdown.get("FUNCIONAL", (0, 0))
    meets_functional_goal = (
        functional_correct / functional_total * 100 >= PRACTICE_FUNCTIONAL_TARGET
        if functional_total > 0
        else True
    )
    return total_weighted, meets_functional_goal


def update_user_stats(db: Session, last_session_date: datetime.date, correct_count: int, total_questions: int, eje_breakdown: dict = None, user_id: int = None):
    """
    Actualiza puntos y rachas con un índice interno de práctica.

    Los pesos de gamificación son provisionales y editables; no son los pesos
    oficiales de una OPEC ni se atribuyen a una GOA aún no publicada.
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

    # Índice interno de práctica. Si no hay desglose, usamos precisión simple.
    if not eje_breakdown:
        # Fallback para sesiones mixtas sin etiquetas precisas.
        score_percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0
        is_passed = score_percentage >= PRACTICE_FUNCTIONAL_TARGET
        session_points = correct_count * 10 
    else:
        total_weighted, is_passed = calculate_practice_index(eje_breakdown)
        session_points = int(total_weighted * 2)  # Factor interno ajustable.

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
