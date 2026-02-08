from datetime import datetime, timedelta
import random
from typing import List
from db.models import Question, Skill

def calculate_mastery_update(is_correct: bool, current_mastery: float) -> float:
    """
    Simple delta update for mastery.
    """
    if is_correct:
        # Growth slows down as you approach 100
        delta = 5.0 * ((100 - current_mastery) / 100.0)
        return min(100.0, current_mastery + delta)
    else:
        # Penalty is stronger
        delta = 10.0
        return max(0.0, current_mastery - delta)

def update_priority(current_priority: float, is_correct: bool) -> float:
    if not is_correct:
        # Increase priority significantly on error
        return current_priority + 2.0
    else:
        # Decrease priority on success, but keep min 1.0
        return max(1.0, current_priority - 0.5)

def select_questions_for_simulation(
    all_questions: List[Question], 
    skills_map: dict, 
    n: int = 20
) -> List[Question]:
    """
    Adaptive sampling algorithm.
    skills_map: {(track, competency, topic): Skill}
    """
    # Categorize questions by user strength
    weak_questions = []
    medium_questions = []
    strong_questions = []

    for q in all_questions:
        key = (q.track, q.competency, q.topic)
        skill = skills_map.get(key)
        
        mastery = skill.mastery_score if skill else 0.0
        # Priority implicitly handled by having low mastery usually? 
        # Or we can use priority_weight explicitly.
        
        if mastery < 50:
            weak_questions.append(q)
        elif mastery < 80:
            medium_questions.append(q)
        else:
            strong_questions.append(q)
            
    # Target distribution
    n_weak = int(n * 0.60)
    n_medium = int(n * 0.25)
    n_strong = n - n_weak - n_medium
    
    selected = []
    
    # Helper to sample without replacement safely
    def sample_safe(pool, k):
        return random.sample(pool, min(len(pool), k))
    
    selected.extend(sample_safe(weak_questions, n_weak))
    
    # Fallback if not enough weak questions: fill with medium
    remaining_weak_slots = n_weak - len(selected)
    
    selected.extend(sample_safe(medium_questions, n_medium + remaining_weak_slots))
    
    remaining_slots = n - len(selected)
    selected.extend(sample_safe(strong_questions, remaining_slots))
    
    # Final fallback if strict pools were exhausted
    if len(selected) < n:
        remaining_all = [q for q in all_questions if q not in selected]
        selected.extend(sample_safe(remaining_all, n - len(selected)))
        
    random.shuffle(selected)
    return selected
