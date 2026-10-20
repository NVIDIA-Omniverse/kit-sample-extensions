"""Catalog drop overlay controller that paints accept/reject drop feedback.

When a ``set_background_fn`` callback is wired up the controller changes the
host panel background color directly — matching the graph overlay mechanism so
both areas produce identical visual feedback.  The overlay Rectangle is kept as
a fallback for cases where no callback is provided.
"""

from typing import Callable, Optional

import omni.ui as ui

from ....config.nodes import Nodes
from .base import BaseDropOverlayController


class CatalogDropOverlayController(BaseDropOverlayController):
    """Drop overlay for the catalog panel."""

    def __init__(self) -> None:
        """Initialize overlay widget references for lazy UI construction."""
        super().__init__()
        self._frame = None
        self._overlay = None
        self._set_background_fn: Optional[Callable[[Optional[int]], None]] = None

    @property
    def frame(self) -> ui.Frame:
        """Return the overlay frame."""
        return self._frame

    def set_background_fn(self, fn: Optional[Callable[[Optional[int]], None]]) -> None:
        """Set a callback that replaces the host panel background color.

        When set, ``show``/``hide`` delegate to this callback instead of
        toggling the overlay Rectangle, producing the same visual as the
        graph background drop indicator.
        """
        self._set_background_fn = fn

    def build(self) -> None:
        """Build the overlay UI for the catalog."""
        self._frame = ui.Frame(
            visible=False,
            width=ui.Percent(100),
            height=ui.Percent(100),
        )
        self._frame.horizontal_clipping = False
        self._frame.vertical_clipping = False
        self._frame.enabled = False
        with self._frame:
            self._overlay = ui.Rectangle(
                width=ui.Percent(100),
                height=ui.Percent(100),
            )
            self._overlay.enabled = False
        self.hide()

    def show(self, can_drop: bool) -> None:
        """Show the overlay with accept/reject coloring."""
        color = Nodes.DROP_OVERLAY_ACCEPT_ABGR if can_drop else Nodes.DROP_OVERLAY_REJECT_ABGR
        self._set_color(color)
        if self._set_background_fn:
            self._set_background_fn(color)
            return
        if self._frame:
            self._frame.visible = True
        if self._overlay:
            self._overlay.set_style({"background_color": color})

    def hide(self) -> None:
        """Hide overlay visuals and restore transparent styling for future drags."""
        super().hide()
        if self._set_background_fn:
            self._set_background_fn(None)
            return
        if self._overlay:
            self._overlay.set_style({"background_color": 0x00000000})
        if self._frame:
            self._frame.visible = False

    def destroy(self) -> None:
        """Drop frame/overlay references so UI objects can be garbage-collected."""
        self._set_background_fn = None
        self._frame = None
        self._overlay = None
        super().destroy()
