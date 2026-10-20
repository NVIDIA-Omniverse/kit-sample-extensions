# pylint: disable=no-member
"""Implement material graph extension logic for `models/graph/nodes/prim/ui_state.py`."""

from pathlib import Path
from typing import Any, Optional

from pxr import UsdUI


class PrimUiState:
    """Stores UI state derived from USD metadata."""

    def __init__(self, prim: Any, default_size: Any) -> None:
        """Initialize cached UI metadata state for a prim and default sizing fallback."""
        self._prim = prim
        self._default_size = default_size

        self._position = None
        self._size = None
        self._display_color = None
        self._stacking_order = None
        self._preview = None

    @property
    def position(self, item: Optional[Any] = None) -> Any:
        """Return cached node position, or delegate to a proxy item when provided."""
        return item.position if item else self._position

    @position.setter
    def position(self, value: Any) -> None:
        """Update cached node position after graph interactions or USD sync."""
        self._position = value

    @property
    def size(self, item: Optional[Any] = None) -> Any:
        """Return cached node size, delegating to proxy items when requested."""
        return item.size if item else self._size

    @size.setter
    def size(self, value: Any) -> None:
        """Update cached node size after sync or interactive edit operations."""
        self._size = value

    @property
    def display_color(self, item: Optional[Any] = None) -> Any:
        """Return cached display color, using proxy item state when available."""
        if item:
            return item.display_color
        if self._display_color is None or max(self._display_color) < 0.1:
            return None
        return self._display_color

    @display_color.setter
    def display_color(self, value: Any) -> None:
        """Update cached display color authored on the node's UI schema."""
        self._display_color = value

    @property
    def stacking_order(self, item: Optional[Any] = None) -> Any:
        """Return cached stacking order used for backdrop/node draw ordering."""
        return item.stacking_order if item else self._stacking_order

    @property
    def preview(self, item: Optional[Any] = None) -> Optional[str]:
        """Return cached preview-icon path normalized for UI lookup."""
        return item.preview if item else self._preview

    def sync_position(self) -> None:
        """Refresh cached node position from authored UsdUI.NodeGraphNodeAPI metadata."""
        if not self._prim:
            return
        api = UsdUI.NodeGraphNodeAPI(self._prim)
        self._position = api.GetPosAttr().Get() if api else None

    def sync_size(self) -> None:
        """Refresh cached size from USD, falling back to configured default dimensions."""
        if not self._prim:
            return
        api = UsdUI.NodeGraphNodeAPI(self._prim)
        self._size = api.GetSizeAttr().Get() if api else None
        if self._size is None:
            self._size = self._default_size

    def sync_ui(self) -> None:
        """Refresh display-color, stacking-order, and preview icon fields from USD."""
        if not self._prim:
            return
        api = UsdUI.NodeGraphNodeAPI(self._prim)
        if not api:
            return
        self._display_color = api.GetDisplayColorAttr().Get()
        self._stacking_order = api.GetStackingOrderAttr().Get() or 0

        value = api.GetIconAttr().Get()
        if value:
            raw_path = value.resolvedPath or value.path
            self._preview = Path(raw_path.lower()).as_posix() if raw_path else None
        else:
            self._preview = None

    def clear(self) -> None:
        """Release prim reference and clear all cached UI-derived state fields."""
        self._prim = None
        self._position = None
        self._size = None
        self._display_color = None
        self._stacking_order = None
        self._preview = None
