"""Safe, deterministic permutations of functional-question options."""

from __future__ import annotations

from collections.abc import Mapping


OPTION_KEYS = ("A", "B", "C")


class OptionRotationError(ValueError):
    """The requested permutation would not preserve a valid question."""


def rotate_correct_option(
    options: Mapping[str, object],
    *,
    old_key: str,
    new_key: str,
) -> dict[str, str]:
    """Swap two option positions without losing or duplicating distractors."""

    old_key = str(old_key or "").strip().upper()
    new_key = str(new_key or "").strip().upper()
    if old_key not in OPTION_KEYS or new_key not in OPTION_KEYS:
        raise OptionRotationError("Las claves deben pertenecer a A, B o C.")
    if old_key == new_key:
        raise OptionRotationError("La clave nueva debe ser distinta de la actual.")
    if not isinstance(options, Mapping) or set(options) != set(OPTION_KEYS):
        raise OptionRotationError("La pregunta debe tener exactamente las opciones A, B y C.")

    clean = {key: str(options[key] or "").strip() for key in OPTION_KEYS}
    if any(not value for value in clean.values()):
        raise OptionRotationError("No se puede rotar una pregunta con opciones vacías.")
    if len(set(clean.values())) != len(OPTION_KEYS):
        raise OptionRotationError("No se puede rotar una pregunta con opciones duplicadas.")

    rotated = dict(clean)
    rotated[old_key], rotated[new_key] = clean[new_key], clean[old_key]
    if set(rotated.values()) != set(clean.values()):
        raise OptionRotationError("La rotación no preservó exactamente las opciones originales.")
    return rotated
