from typing import Any

from .core import PREDICATES as CORE_PREDICATES
from .p13 import P13_PREDICATES


PREDICATES = {**CORE_PREDICATES, **P13_PREDICATES}


def evaluate_predicate(predicate_id: str, vector: dict[str, Any]) -> dict[str, Any]:
    try:
        predicate = PREDICATES[predicate_id]
    except KeyError as exc:
        raise ValueError(f"unknown architecture predicate: {predicate_id}") from exc
    return predicate(dict(vector))

__all__ = ["PREDICATES", "evaluate_predicate"]
