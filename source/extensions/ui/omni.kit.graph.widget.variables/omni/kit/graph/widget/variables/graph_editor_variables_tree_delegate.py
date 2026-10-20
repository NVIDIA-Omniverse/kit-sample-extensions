# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["GraphEditorVariablesTreeDelegate"]

from functools import partial
from typing import Callable, Optional

import omni.ui as ui
from omni.kit.graph.editor.core.graph_editor_core_tree_delegate import GraphEditorCoreTreeDelegate


class GraphEditorVariablesTreeDelegate(GraphEditorCoreTreeDelegate):
    def __init__(
        self,
        on_drag_variable_read: Optional[Callable[[ui.AbstractItem], str]] = None,
        on_drag_variable_write: Optional[Callable[[ui.AbstractItem], str]] = None,
    ):
        super().__init__(False)
        self._item_size = 18
        self._icon_size = 18
        self._section_height = 22

        self._on_drag_variable_read_fn = on_drag_variable_read
        self._on_drag_variable_write_fn = on_drag_variable_write

    def build_item_widget(self, model, item, column_id, level, expanded):
        """build the widget for the items"""

        with ui.ZStack():
            label_stack = ui.HStack()
            with label_stack:
                ui.Spacer(width=2)
                type_model = model.get_item_value_model(item, 1)
                if type_model:
                    with ui.VStack(width=0):
                        ui.Spacer()
                        with ui.VStack(width=self._item_size - 4, height=self._item_size - 4):
                            self._build_rectangle(3, "Graph.Connection", type_model.as_string)
                        ui.Spacer()
                ui.Spacer(width=2)

                with ui.VStack(spacing=2, height=self._item_size):
                    ui.Spacer()
                    name_model = model.get_item_value_model(item, 0)
                    description_model = model.get_item_value_model(item, 3)
                    description = description_model.as_string if description_model else None

                    def _create_tooltip(text):
                        """Create a tooltip in a fixed style, wrap the tooltip if the text is too long"""
                        width = 350 if len(text) > 175 else 0
                        ui.Label(text, word_wrap=True, width=width, style={"Label": {"color": 0xFF3B494B}})

                    ui.Label(
                        name_model.as_string,
                        height=0,
                        style_type_name_override="TreeView.Item.Title",
                        elided_text=True,
                        tooltip_fn=lambda: _create_tooltip(description) if description else None,
                    )
                    ui.Spacer()

            read_stack = None
            write_stack = None
            with ui.HStack():
                ui.Spacer()
                if self._on_drag_variable_read_fn:
                    read_stack = self._build_drag_handle("READ", partial(self._on_drag_variable_read_fn, item))
                if self._on_drag_variable_write_fn:
                    ui.Spacer(width=4)
                    write_stack = self._build_drag_handle("WRITE", partial(self._on_drag_variable_write_fn, item))

        def on_mouse_hovered(hovered: bool):
            is_visible = hovered and (
                self._on_drag_variable_read_fn is not None or self._on_drag_variable_write_fn is not None
            )
            if read_stack is not None:
                read_stack.visible = is_visible
            if write_stack is not None:
                write_stack.visible = is_visible

        label_stack.set_mouse_hovered_fn(on_mouse_hovered)

    def _build_rectangle(self, radius, type_name, name, style_override=None):
        """
        Build rectangle of the specific design.

        Args:
            radius: The radius of round corers. The corners are top-left and
                    bottom-right.
            type_name: style_type_name_override of each widget
            name: name of each widget
            style_override: the style to apply to the top level node
        """
        stack = ui.VStack(alignment=ui.Alignment.CENTER)
        if style_override:
            stack.set_style(style_override)

        with stack:
            # Top of the rectangle
            with ui.HStack(height=0):
                ui.Circle(
                    radius=radius,
                    width=0,
                    height=0,
                    size_policy=ui.CircleSizePolicy.FIXED,
                    alignment=ui.Alignment.RIGHT_BOTTOM,
                    style_type_name_override=type_name,
                    name=name,
                )
                ui.Rectangle(style_type_name_override=type_name, name=name)

            # Middle of the rectangle
            ui.Rectangle(style_type_name_override=type_name, name=name)

            # Bottom of the rectangle
            with ui.HStack(height=0):
                ui.Rectangle(style_type_name_override=type_name, name=name)
                ui.Circle(
                    radius=radius,
                    width=0,
                    height=0,
                    size_policy=ui.CircleSizePolicy.FIXED,
                    alignment=ui.Alignment.LEFT_TOP,
                    style_type_name_override=type_name,
                    name=name,
                )

    def __build_draggable_button(self, text: str):
        border_width = 1.5
        self._build_rectangle(
            3, "Variable.Drag.Border", "", {"Variable.Drag.Border": {"background_color": ui.color("#526d75")}}
        )
        with ui.VStack():
            ui.Spacer(height=border_width)
            with ui.HStack():
                ui.Spacer(width=border_width)
                with ui.ZStack():
                    self._build_rectangle(
                        3,
                        "Variable.Drag.Background",
                        "",
                        {"Variable.Drag.Background": {"background_color": ui.color("#1e2931")}},
                    )
                    ui.Label(
                        text,
                        alignment=ui.Alignment.CENTER,
                        style={"Label": {"color": ui.color("#526d75"), "margin_width": 2.0}},
                    )
                ui.Spacer(width=border_width)
            ui.Spacer(height=border_width)

    def _build_drag_handle(self, text: str, on_drag_fn: Callable[[], str]) -> ui.ZStack:

        # Separates the button into two separate layouts. One, whose visibility is controlled
        # by the parent hover, and another which is called from the drag callback
        # to make the button appear on the drag, even when the visibility of the parent
        # button is disabled.
        def on_drag_callback(draw_fn: Callable[[], None], drag_fn: Callable[[], str]) -> str:
            z_stack = ui.ZStack(width=40)
            with z_stack:
                draw_fn()
            return drag_fn()

        on_draw_fn = partial(self.__build_draggable_button, text)

        drag_stack = ui.ZStack(width=40)
        drag_stack.set_drag_fn(partial(on_drag_callback, on_draw_fn, on_drag_fn))
        if hasattr(drag_stack, "send_mouse_events_to_back"):
            drag_stack.send_mouse_events_to_back = True

        with drag_stack:
            visibility_stack = ui.ZStack(visible=False)
            with visibility_stack:
                self.__build_draggable_button(text)

        return visibility_stack
