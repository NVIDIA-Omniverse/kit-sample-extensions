"""Runtime registry for the active material validator per USD context."""

from typing import Dict, Optional

from .validator import MaterialValidator

_VALIDATORS_BY_CONTEXT_ID: Dict[int, MaterialValidator] = {}


def set_active_validator(usd_context: Optional[object], validator: Optional[MaterialValidator]) -> None:
    """Associate a validator with a USD context instance."""
    if usd_context is None or validator is None:
        return
    _VALIDATORS_BY_CONTEXT_ID[id(usd_context)] = validator


def clear_active_validator(usd_context: Optional[object]) -> None:
    """Remove validator association for a USD context instance."""
    if usd_context is None:
        return
    _VALIDATORS_BY_CONTEXT_ID.pop(id(usd_context), None)


def get_active_validator(usd_context: Optional[object]) -> Optional[MaterialValidator]:
    """Return the validator currently associated with a USD context."""
    if usd_context is None:
        return None
    return _VALIDATORS_BY_CONTEXT_ID.get(id(usd_context))
