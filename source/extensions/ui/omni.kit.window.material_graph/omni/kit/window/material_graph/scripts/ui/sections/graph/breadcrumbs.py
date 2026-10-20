"""Breadcrumb widget for navigating nested nodegraph context paths in the graph UI.

Rendering is delegated to the C++ GraphCanvasWidget draw pass so the
breadcrumb bar always paints on top of nodes and connections.  This
module manages the data (segment names, overflow collapse) and polls
the C++ side for click results each frame.
"""

import logging
from collections import namedtuple
from typing import Any, Callable, List, Optional

import omni.kit.app
import omni.ui as ui

from ....config.logging import log_exception, logger
from ....utils.async_utils import ensure_future_logged

# pylint: disable=no-member


class MaterialGraphBreadcrumbs:
    """Breadcrumbs driven by Python data, rendered by the C++ canvas widget."""

    _Item = namedtuple("_Item", "id name")

    def __init__(
        self,
        frame: ui.Frame,
        selected_fn: Callable[["_Item"], None],
        navigation: Optional[List[str]] = None,
        canvas_widget: Optional[Any] = None,
        **kwargs,
    ) -> None:
        self._selected_fn = selected_fn
        self._navigation = navigation or []
        self._canvas_widget = canvas_widget
        self._kwargs = kwargs
        self._poll_task = None

        self._push_to_native()

    def destroy(self) -> None:
        self._selected_fn = None
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None
        if self._canvas_widget:
            try:
                self._canvas_widget.set_breadcrumb([])
            except Exception:
                pass
        self._canvas_widget = None

    # ------------------------------------------------------------------

    def _push_to_native(self) -> None:
        """Send the segment list to the C++ widget for rendering."""
        if not self._canvas_widget or not self._navigation:
            return
        try:
            self._canvas_widget.set_breadcrumb(list(self._navigation))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(
                logger,
                "breadcrumb update failed",
                level=logging.WARNING,
                action="set_breadcrumb",
                exc=exc,
            )
        self._start_polling()

    def _start_polling(self) -> None:
        if self._poll_task:
            self._poll_task.cancel()
        self._poll_task = ensure_future_logged(self._poll_loop(), "breadcrumb polling")

    async def _poll_loop(self) -> None:
        """Poll the C++ widget for breadcrumb clicks each frame."""
        app = omni.kit.app.get_app()
        while self._canvas_widget and self._selected_fn:
            await app.next_update_async()
            if not self._canvas_widget:
                break
            try:
                idx = self._canvas_widget.breadcrumb_clicked_index
            except Exception as exc:  # pylint: disable=broad-exception-caught
                log_exception(
                    logger,
                    "breadcrumb polling failed",
                    level=logging.WARNING,
                    action="breadcrumb_poll",
                    exc=exc,
                )
                break
            if idx >= 0:
                self._canvas_widget.clear_breadcrumb_clicked()
                name = self._navigation[idx] if idx < len(self._navigation) else ""
                if self._selected_fn:
                    self._selected_fn(self._Item(idx, name))
