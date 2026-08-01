from dataclasses import dataclass


@dataclass(frozen=True)
class WeeklyProgress:
    completed_days: int
    target_days: int

    @property
    def remaining_days(self) -> int:
        return max(self.target_days - self.completed_days, 0)

    @property
    def is_complete(self) -> bool:
        return self.completed_days >= self.target_days

    @property
    def ratio(self) -> float:
        if self.target_days <= 0:
            return 1.0
        return min(self.completed_days / self.target_days, 1.0)


def build_weekly_progress(completed_days: int, configured_days: int) -> WeeklyProgress:
    """Crea una meta flexible: como máximo cinco sesiones efectivas por semana."""
    target = max(1, min(int(configured_days or 5), 5))
    return WeeklyProgress(max(int(completed_days or 0), 0), target)


def coverage_percent(total_topics: int, studied_topics: int) -> float:
    if total_topics <= 0:
        return 0.0
    return min(max(studied_topics, 0) / total_topics * 100.0, 100.0)


def topic_status(mastery: float, attempts: int) -> tuple[str, str]:
    """Devuelve etiqueta y color semántico para el mapa de cobertura."""
    mastery = float(mastery or 0.0)
    attempts = int(attempts or 0)
    if attempts <= 0:
        return "Pendiente", "⚪"
    if mastery < 50:
        return "Reforzar", "🔴"
    if mastery < 75:
        return "En práctica", "🟡"
    if mastery < 85:
        return "Consolidando", "🔵"
    return "Dominado", "🟢"