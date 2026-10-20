"""Background-color drop indicator used when dragging into the graph viewport."""

from typing import Callable, Optional

from ....config.nodes import Nodes
from .base import BaseDropOverlayController


class GraphBackgroundDropIndicatorController(BaseDropOverlayController):
    """Drop indicator that updates the graph background color."""

    def __init__(self, set_background_fn: Callable[[Optional[int]], None]) -> None:
        """Store callback used to set/reset graph background color."""
        super().__init__()
        self._set_background_fn = set_background_fn

    def build(self) -> None:
        """No UI to build for background-based indicator."""

    def show(self, can_drop: bool) -> None:
        """Show indicator by updating the graph background."""
        color = Nodes.DROP_OVERLAY_ACCEPT_ABGR if can_drop else Nodes.DROP_OVERLAY_REJECT_ABGR
        self._set_color(color)
        if self._set_background_fn:
            self._set_background_fn(color)

    def hide(self) -> None:
        """Hide indicator by restoring the graph background."""
        super().hide()
        if self._set_background_fn:
            self._set_background_fn(None)

    def destroy(self) -> None:
        """Clear callback references and restore base controller to inert state."""
        self._set_background_fn = None
        super().destroy()
