"""Implement material graph extension logic for `models/graph/core/state.py`."""

from enum import Enum


class ModelState(Enum):
    """Lifecycle states for graph models."""

    ACTIVE = "active"
    CLEARED = "cleared"
    DESTROYED = "destroyed"


__all__ = ["ModelState"]
