"""Top-level material graph window wrapper and extension-facing UI entrypoint."""

# pylint: disable=no-member,attribute-defined-outside-init
import asyncio
from typing import Any, Callable, Optional

import carb
import omni.kit.app
import omni.ui
from pxr import Sdf, Usd

from ..config.logging import LogContext, context_suffix, get_logger
from ..context_manager import ContextManager
from .sections.graph.widget import GraphWidget

logger = get_logger()


class GraphWindow(omni.ui.Window):
    """Window wrapper for the material graph UI."""

    def __init__(self, title: str, ext_name: str, show_startup_buttons: bool = True, **kwargs: Any) -> None:
        """Initialize the graph window and its main widget."""
        flags = kwargs.pop("flags", 0) | omni.ui.WINDOW_FLAGS_NO_SCROLLBAR

        if hasattr(omni.ui, "WINDOW_FLAGS_NO_SCROLL_WITH_MOUSE"):
            flags = flags | omni.ui.WINDOW_FLAGS_NO_SCROLL_WITH_MOUSE

        super().__init__(title, flags=flags, **kwargs)
        logger.debug("graph window init%s", context_suffix(LogContext(action="init"), file_path=title))

        self._visibility_changed_listener = None
        self.set_visibility_changed_fn(self._visibility_changed_fn)

        self._context_manager = ContextManager(omni.usd.get_context())
        self._main_widget = None

        def _visible(_arg):
            """Show frame once docking callback fires to avoid startup flicker."""
            self.frame.visible = True

        # hide frame until docked to prevent flickering
        self.frame.visible = False
        with self.frame:
            self._main_widget = GraphWidget(self._context_manager, title, ext_name, show_startup_buttons)
            self.set_docked_changed_fn(_visible)
            self.deferred_dock_in("Content", omni.ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)

    def destroy(self) -> None:
        """Destroy the window and child controllers."""
        logger.debug("graph window destroy%s", context_suffix(LogContext(action="destroy")))
        if self._main_widget:
            self._main_widget.destroy()
            self._main_widget = None

        if self._context_manager:
            self._context_manager.destroy()
            self._context_manager = None

        self._visibility_changed_listener = None
        super().destroy()

    @property
    def graph_widget(self) -> Optional[GraphWidget]:
        """Return the main graph widget."""
        return self._main_widget

    def open_graph(self, prim: Optional[Usd.Prim] = None, focus_graph_path: Optional[Sdf.Path] = None) -> None:
        """Open a graph for a prim and focus an optional graph path."""
        if self._main_widget:
            logger.debug(
                "graph window open_graph%s",
                context_suffix(
                    LogContext(action="open_graph", prim_path=str(prim.GetPath()) if prim else None),
                    file_path=str(focus_graph_path) if focus_graph_path else None,
                ),
            )
            self._main_widget.open_graph(prim, focus_graph_path)

    def _visibility_changed_fn(self, visible: bool) -> None:
        """Forward visibility changes to the graph widget."""
        logger.debug(
            "graph window visibility%s",
            context_suffix(LogContext(action="visibility"), file_path=f"visible={visible}"),
        )
        if self._main_widget:
            self._main_widget.set_visibility(visible)

        if self._visibility_changed_listener:
            self._visibility_changed_listener(visible)

    def set_visibility_changed_listener(self, listener: Optional[Callable[[bool], None]]) -> None:
        """Register a callback for visibility changes."""
        self._visibility_changed_listener = listener
