"""Material graph splitter with explicit panel visibility control."""

from functools import partial
from typing import Callable

import omni.ui as ui
from omni.kit.graph.editor.core.graph_editor_core_splitter import GraphEditorCoreSplitter


class MaterialGraphSplitter(GraphEditorCoreSplitter):
    """Graph splitter that exposes catalog panel visibility state."""

    def __init__(self, build_left_fn: Callable[[], None], build_right_fn: Callable[[], None]) -> None:
        # Build this splitter from an explicit full-size frame so the layout
        # is always realized inside the parent graph container.
        self._build_left_fn = build_left_fn
        self._build_right_fn = build_right_fn
        self._panel_visible = True
        self._panel = None
        self._right_frame = None
        self._placer = None
        self._button = None
        self._splitter_highlight = None

    def destroy(self) -> None:
        """Release references used by splitter controls."""
        self._build_right_fn = None
        self._build_left_fn = None
        self._panel = None
        self._placer = None
        self._button = None
        self._splitter_highlight = None

    def is_panel_visible(self) -> bool:
        """Return True when the left panel is visible."""
        return bool(self._panel and self._panel.visible)

    def set_panel_visible(self, visible: bool) -> None:
        """Show or hide the left panel programmatically."""
        self._panel_visible = bool(visible)
        self._apply_panel_state(visible)

    def _apply_panel_state(self, visible: bool) -> None:
        if not self._panel or not self._placer or not self._button or not self._splitter_highlight:
            return
        if visible:
            self._panel.visible = True
            self._splitter_highlight.visible = True
            self._placer.offset_x = 250.0
            self._placer.draggable = True
            self._button.text = "<"
        else:
            self._panel.visible = False
            self._splitter_highlight.visible = False
            self._placer.offset_x = 0.0
            self._placer.draggable = False
            self._button.text = ">"

    def _toggle_panel(self, *args) -> None:
        self._apply_panel_state(not self.is_panel_visible())

    def on_build(self) -> None:
        """Build splitter UI with tracked widgets for external visibility control."""
        with ui.HStack(height=ui.Fraction(1)):
            with ui.ZStack(width=0, height=ui.Fraction(1)):
                self._placer = ui.Placer(drag_axis=ui.Axis.X)
                with self._placer:
                    with ui.ZStack(width=10):
                        self._splitter_highlight = ui.Rectangle(name="Splitter")
                        with ui.VStack():
                            ui.Spacer()
                            self._button = ui.Button(
                                ">",
                                height=50,
                                style={"Button": {"margin": 0}, "Button.Label": {"font_size": 10}},
                            )
                            ui.Spacer()

                self._panel = ui.Frame(visible=False, height=ui.Fraction(1))
                with self._panel:
                    self._build_left_fn()

            self._right_frame = ui.Frame(height=ui.Fraction(1))
            with self._right_frame:
                self._build_right_fn()

        def _on_offset_changed(offset):
            val = offset if isinstance(offset, (int, float)) else offset.value
            if self.is_panel_visible() and val < 175.0:
                self._apply_panel_state(False)

        self._placer.set_offset_x_changed_fn(_on_offset_changed)
        self._button.set_clicked_fn(partial(self._toggle_panel))
        self._apply_panel_state(self._panel_visible)
