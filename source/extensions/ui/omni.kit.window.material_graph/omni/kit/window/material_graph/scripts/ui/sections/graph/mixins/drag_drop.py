"""Drag-and-drop behavior mixin for GraphWidget."""

from typing import Optional

import carb
import omni.ui

from .....utils.modifiers import clear_active_modifier_flags, set_active_modifier_flags


class GraphWidgetDragDropMixin:
    """Mixin that centralizes graph drag-and-drop behavior shared by graph widgets."""

    def _set_drop_indicator(self, can_drop: bool) -> None:
        """Show drop indicator state for drag hover."""
        if self._graph_drop_overlay:
            self._graph_drop_overlay.show(can_drop)

    def _hide_drop_indicator(self) -> None:
        """Hide the current drop indicator and reset visual feedback for drag sessions."""
        if self._graph_drop_overlay:
            self._graph_drop_overlay.hide()

    def _set_graph_background_override(self, color: Optional[int]) -> None:
        """Override the graph background color for drop indication."""
        style = dict(self.style) if self.style else {}
        graph_style = dict(style.get("Graph", {}))
        if self._graph_background_color is None:
            self._graph_background_color = graph_style.get("background_color")
        if color is None:
            if self._graph_background_color is None:
                graph_style.pop("background_color", None)
            else:
                graph_style["background_color"] = self._graph_background_color
        else:
            graph_style["background_color"] = color
        style["Graph"] = graph_style
        self.style = style

    def on_accept_drop(self, drop_data: str) -> bool:
        """Return whether a drop is accepted."""
        can_drop = self._node_creation_controller.accept_drop(drop_data)
        if self._should_show_input_output_indicator(drop_data):
            self._set_drop_indicator(False)
        elif self._is_catalog_payload(drop_data):
            self._hide_drop_indicator()
        else:
            self._set_drop_indicator(can_drop)
        return can_drop

    def on_drop(self, event: omni.ui.WidgetMouseDropEvent) -> None:
        """Handle a drop event on the graph."""
        self._hide_drop_indicator()
        try:
            return self._node_creation_controller.drop(event)
        finally:
            clear_active_modifier_flags()

    def _on_graph_hovered(self, hovered: bool) -> None:
        """Hide indicator when cursor leaves the graph."""
        if not hovered:
            self._hide_drop_indicator()
            clear_active_modifier_flags()

    def _on_graph_mouse_released(self, _x: float, _y: float, button: int, modifier: int) -> None:
        """Hide graph context menus on background click."""
        set_active_modifier_flags(modifier)
        try:
            if button not in (0, carb.input.MouseInput.LEFT_BUTTON.value):
                return
            if self._interaction_controller:
                self._interaction_controller.hide_context_menu()
            if self._graph_view:
                self._graph_view.hide_port_context_menu()
        finally:
            clear_active_modifier_flags()
