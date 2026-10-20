"""Shared helpers for context-visibility custom metadata."""

from typing import List, Optional

from pxr import Usd

from ..config.logging import logger


def get_context_visibility(prim: Usd.Prim) -> Optional[List[str]]:
    """Return normalized context visibility metadata, or None for unrestricted visibility."""
    ui_data = prim.GetCustomDataByKey("omni:ui") if prim.HasAuthoredCustomDataKey("omni:ui") else None
    visibility = ui_data.get("contextVisibility") if isinstance(ui_data, dict) else None
    if visibility is None and prim.HasAuthoredCustomDataKey("omni:ui:contextVisibility"):
        visibility = prim.GetCustomDataByKey("omni:ui:contextVisibility")
    if visibility is None:
        return None
    if isinstance(visibility, str):
        return [visibility]
    try:
        return [str(item) for item in visibility if item]
    except TypeError:
        logger.warning("invalid context visibility metadata: %r", visibility, exc_info=True)
    return []


def is_context_visible(prim: Usd.Prim, context_name: str) -> bool:
    """Return whether prim is visible in context_name."""
    visibility = get_context_visibility(prim)
    if not visibility:
        return True
    return context_name in visibility
