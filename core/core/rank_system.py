# Configuration of Ranks
RANKS = [
    {"name": "Aspirante", "threshold": 0, "color": "#94a3b8", "icon": "📁"},
    {"name": "Gestor Junior", "threshold": 500, "color": "#3b82f6", "icon": "📑"},
    {"name": "Auditor Senior", "threshold": 1500, "color": "#a855f7", "icon": "🔍"},
    {"name": "Inspector Jefe", "threshold": 4000, "color": "#f59e0b", "icon": "🎖️"},
    {"name": "Comisionado Elite", "threshold": 10000, "color": "#ef4444", "icon": "👑"}
]

def get_rank_info(points: int):
    """Retorna la info del rango actual basado en los puntos."""
    current_rank = RANKS[0]
    next_rank = RANKS[1]
    
    for i, rank in enumerate(RANKS):
        if points >= rank["threshold"]:
            current_rank = rank
            if i + 1 < len(RANKS):
                next_rank = RANKS[i+1]
            else:
                next_rank = None
    return current_rank, next_rank
