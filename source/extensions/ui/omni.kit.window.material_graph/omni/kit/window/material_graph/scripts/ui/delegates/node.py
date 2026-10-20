"""Minimal node delegate providing style and menu coordination hooks.

The C++ GraphCanvasWidget handles all node rendering natively. This delegate
exists only to satisfy the GraphEditorCoreWidget constructor (which requires
a delegate for get_style()) and to provide no-op menu coordination methods.
"""

from omni.kit.graph.delegate.modern import GraphNodeDelegate


class MaterialGraphNodeDelegate(GraphNodeDelegate):
    """Lightweight delegate that provides get_style() for widget styling."""

    def __init__(self) -> None:
        super().__init__()

    def hide_node_context_menu(self) -> None:
        """No-op: context menus are managed by GraphCanvasView."""

    def should_ignore_background_click(self) -> bool:
        """No-op: click gating is handled by GraphCanvasView."""
        return False
