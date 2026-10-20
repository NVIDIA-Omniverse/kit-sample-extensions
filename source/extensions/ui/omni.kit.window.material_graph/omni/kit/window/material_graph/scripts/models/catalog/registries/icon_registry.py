"""In-memory registry mapping context/identifier pairs to icon path metadata."""

from typing import Dict, Optional, Tuple

_ICON_BY_CONTEXT_AND_IDENTIFIER: Dict[Tuple[str, str], Tuple[str, int]] = {}


def clear_context(context_name: str) -> None:
    """Remove all registered icon mappings for a context."""
    if not context_name:
        return
    keys = [key for key in _ICON_BY_CONTEXT_AND_IDENTIFIER if key[0] == context_name]
    for key in keys:
        _ICON_BY_CONTEXT_AND_IDENTIFIER.pop(key, None)


def register(context_name: str, identifier: str, icon_path: str, icon_color: int) -> None:
    """Register a catalog icon path for a shader identifier in a context."""
    if not context_name or not identifier or not icon_path:
        return
    _ICON_BY_CONTEXT_AND_IDENTIFIER[(context_name, identifier)] = (icon_path, icon_color)


def get_icon(context_name: str, identifier: str) -> Optional[Tuple[str, int]]:
    """Return the registered icon path for a context+identifier key."""
    if not context_name or not identifier:
        return (None, None)
    return _ICON_BY_CONTEXT_AND_IDENTIFIER.get((context_name, identifier), (None, None))
