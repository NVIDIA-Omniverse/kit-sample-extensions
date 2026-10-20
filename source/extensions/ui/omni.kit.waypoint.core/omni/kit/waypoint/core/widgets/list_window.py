# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import weakref
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Callable, cast

import carb.dictionary
import carb.settings
import omni.kit.app
from omni import ui
from omni.kit.viewport.utility import get_active_viewport_window
from omni.ui import color as cl
from omni.ui import constant as fl

from .. import ViewportWaypoint, WaypointItem
from ..common import CURRENT_TOOL_PATH, SETTINGS_WAYPOINT_ROOT
from ..extension import SETTINGS_WAYPOINT_EDITING, WaypointChangeCallbacks
from ..extension import get_instance as get_waypoint_extension_instance
from ..style import ICON_PATH, LIST_WINDOW_STYLES, POSITIONER_STYLE, UI_STYLES, WAYPOINT_BROWSER_WIDGET_STYLES
from .edit import WaypointItemEditWidget
from .hover import WaypointItemHoverWidget
from .playbar import PlayBar

if TYPE_CHECKING:  # pragma: no cover
    from ..extension import WaypointExtension


MAX_SHOW_WAYPOINTS = 3
SPACING = 5
BORDER_RADIUS = 3
FONT_SIZE = 14.0
COLLAPSABLEFRAME_BORDER_COLOR = 0x0
COLLAPSABLEFRAME_BACKGROUND_COLOR = 0xFF343432
COLLAPSABLEFRAME_GROUPFRAME_BACKGROUND_COLOR = 0xFF23211F
COLLAPSABLEFRAME_SUBFRAME_BACKGROUND_COLOR = 0xFF343432
COLLAPSABLEFRAME_HOVERED_BACKGROUND_COLOR = 0xFF2E2E2B
COLLAPSABLEFRAME_PRESSED_BACKGROUND_COLOR = 0xFF2E2E2B
COLLAPSABLEFRAME_TEXT_COLOR = 0xFFCCCCCC
SETTINGS_LIST_WINDOW_SAVE_POSITION = SETTINGS_WAYPOINT_ROOT + "list_window/save_position"
SETTINGS_LIST_WINDOW_ALLOW_RESIZE = SETTINGS_WAYPOINT_ROOT + "list_window/allow_resize"
APPLICATION_MODE = "/app/application_mode"


WINDOW_STYLE = {
    "CollapsableFrame": {
        "background_color": COLLAPSABLEFRAME_BACKGROUND_COLOR,
        "secondary_color": COLLAPSABLEFRAME_BACKGROUND_COLOR,
        "color": COLLAPSABLEFRAME_TEXT_COLOR,
        "border_radius": BORDER_RADIUS,
        "border_color": 0x0,
        "border_width": 1,
        "font_size": FONT_SIZE,
        "padding": 6,
    },
    "StringField": {
        "color": 0xFFEEEEEE,
        "font_size": FONT_SIZE,
    },
    "MenuBar.Item.Background": {
        "background_color": cl.viewport_menubar_background,
        "border_radius": 6,
        "padding": 1,
        "margin": 2,
    },
    "Menubar.Hover": {
        "background_color": 0,
        "padding": 1,
        "margin": 1,
    },
    "Menubar.Hover:hovered": {
        "background_color": cl.viewport_menubar_selection,
        "border_color": cl.viewport_menubar_selection_border_button,
        "border_width": 1.5,
    },
    "Menubar.Hover:pressed": {
        "background_color": cl.viewport_menubar_selection,
        "border_color": cl.viewport_menubar_selection_border_button,
        "border_width": 1.5,
    },
    "Menu.Button": {
        "color": cl.viewport_menubar_selection_border,
        "background_color": 0,
        "padding": 0,
        "margin_width": fl.viewport_menubar_item_margin,
        "margin_height": fl.viewport_menubar_item_margin_height,
        "stack_direction": ui.Direction.LEFT_TO_RIGHT,
    },
    "Menu.Item.CloseMark": {
        "image_url": "${kit}/resources/icons/CloseMark.svg",
        "margin": 3,
        "color": 0xFFCCCCCC,
    },
    "Button.Close:hovered": {"border_color": 0xFF535354},
    "Button.Close.Image": {"image_url": f"{ICON_PATH}/Close.svg"},
    "Button:hovered": {"background_color": 0x0},
    "Button:pressed": {"background_color": 0x0},
    "Menu.Title:hovered": {
        "background_color": cl.viewport_menubar_selection,
        "border_width": 1,
        "border_color": cl.viewport_menubar_selection_border,
    },
    "Menu.Title:pressed": {"background_color": cl.viewport_menubar_selection},
    "CollapsableFrame.Header": {"debug_color": 0x20FF00FF},
    "CollapsableFrame.Header": {
        "font_size": FONT_SIZE,
        "background_color": COLLAPSABLEFRAME_TEXT_COLOR,
        "color": COLLAPSABLEFRAME_TEXT_COLOR,
    },
    "CollapsableFrame:hovered": {"secondary_color": COLLAPSABLEFRAME_HOVERED_BACKGROUND_COLOR},
    "CollapsableFrame:pressed": {"secondary_color": COLLAPSABLEFRAME_PRESSED_BACKGROUND_COLOR},
    **WAYPOINT_BROWSER_WIDGET_STYLES,
}


def build_frame_header(waypoint: ViewportWaypoint, collapsed: bool, text: str, id: str = ""):
    """Custom header for CollapsibleFrame"""
    if not id:
        id = text

    if collapsed:
        alignment = ui.Alignment.RIGHT_CENTER
        width = 5
        height = 7
    else:
        alignment = ui.Alignment.CENTER_BOTTOM
        width = 7
        height = 5

    waypoint_inst = get_waypoint_extension_instance()

    def on_rename(x: int, y: int):
        def on_rename_ended(_item):
            new_name = model.as_string.replace(" ", "_")
            if new_name == waypoint.name or not new_name:
                return
            if waypoint_inst:
                waypoint_inst.rename_waypoint(waypoint, new_name)

                async def cleanup():
                    win.destroy()

                asyncio.ensure_future(cleanup())

        flags = (
            ui.WINDOW_FLAGS_POPUP
            | ui.WINDOW_FLAGS_NO_TITLE_BAR
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_DOCKING
            | ui.WINDOW_FLAGS_NO_CLOSE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
        )
        win = ui.Window(
            "Rename Waypoint",
            position_x=x,
            position_y=y,
            visible=True,
            padding_x=0,
            padding_y=0,
            style=WINDOW_STYLE,
            flags=flags,
            width=160,
            height=0,
            raster_policy=ui.RasterPolicy.NEVER,
        )
        with win.frame:
            model = ui.SimpleStringModel()
            model.add_end_edit_fn(on_rename_ended)
            field = ui.StringField(model, multiline=False)
            field.focus_keyboard()

    ctx_menu = None

    def on_mouse_pressed(x, y, btn, flag):
        nonlocal ctx_menu
        if btn == 1:  # mouse right click
            if ctx_menu is None:
                ctx_menu = ui.Menu(menu_compatibility=False, tearable=False)
                with ctx_menu:
                    ui.MenuItem("Rename Waypoint", triggered_fn=lambda x=x, y=y: on_rename(x, y))
            ctx_menu.show_at(x, y)

    header_stack = ui.ZStack(spacing=8, mouse_pressed_fn=on_mouse_pressed)
    with header_stack:
        with ui.HStack():
            with ui.VStack(width=0):
                ui.Spacer()
                ui.Triangle(
                    style_type_name_override="CollapsableFrame.Header", width=width, height=height, alignment=alignment
                )
                ui.Spacer()
            ui.Spacer()
        with ui.HStack():
            ui.Spacer()
            ui.Label(text, width=0, style_type_name_override="CollapsableFrame.Header")
            ui.Spacer()


@dataclass
class WaypointEntryWidget:
    waypoint: ViewportWaypoint
    outer_stack: ui.ZStack
    hover_widget: WaypointItemHoverWidget
    collapse_frame: ui.CollapsableFrame
    field_stack: ui.ZStack
    notes_field: ui.StringField
    edit_widget: WaypointItemEditWidget


class WaypointListWindow(ui.Window):
    """A window for managing and interacting with waypoints.

    This window displays a list of waypoints, providing functionality to add, select, and edit them. It dynamically adjusts its size based on the active viewport and offers interactive elements such as clickable thumbnails, editable comments, and context menus for renaming.

    Args:
        on_edit_waypoint_fn (Callable[[WaypointItem, float, float], None]): Callback function invoked when a waypoint edit operation is triggered.
    """

    WINDOW_WIDTH = 180
    """int: window width in pixels"""
    VIEWPORT_MAIN_MENUBAR_HEIGHT = 32
    """int: height of the viewport menubar in pixels"""
    SPACING = 9
    """int: spacing used for window positioning relative to viewport"""

    def __init__(self, on_edit_waypoint_fn: Callable[[WaypointItem, float, float], None] = lambda *x: None):
        self._settings = carb.settings.get_settings()
        self._editing_waypoint_setting_changed_sub = self._settings.subscribe_to_node_change_events(
            SETTINGS_WAYPOINT_EDITING, self._on_waypoint_editing_changed
        )
        self._current_tool_setting_changed_sub = self._settings.subscribe_to_node_change_events(
            CURRENT_TOOL_PATH,
            self._on_current_tool_changed,
        )
        self._on_edit_waypoint_fn = on_edit_waypoint_fn
        self._waypoint_instance = cast("WaypointExtension ", get_waypoint_extension_instance())
        self._waypoint_count = 0
        self._widgets: "list[WaypointEntryWidget]" = []
        self._widgets_map: "dict[ViewportWaypoint, WaypointEntryWidget]" = {}
        self._waypoint_callback = WaypointChangeCallbacks(
            self._on_waypoints_changed,
            self._on_waypoints_changed,
            self._on_waypoint_changed,
            self._on_waypoints_changed,
        )
        self._waypoint_instance.register_callback(self._waypoint_callback)

        flags = (
            ui.WINDOW_FLAGS_NO_TITLE_BAR
            # | ui.WINDOW_FLAGS_POPUP
            | ui.WINDOW_FLAGS_NO_DOCKING
            | ui.WINDOW_FLAGS_NO_CLOSE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_COLLAPSE
        )

        if not self._settings.get(SETTINGS_LIST_WINDOW_ALLOW_RESIZE):
            flags |= ui.WINDOW_FLAGS_NO_RESIZE

        super().__init__(
            "Waypoints",
            width=WaypointListWindow.WINDOW_WIDTH,
            flags=flags,
            padding_x=2,
            padding_y=2,
            visible=False,
            raster_policy=ui.RasterPolicy.NEVER,
        )
        self.frame.set_style(LIST_WINDOW_STYLES)
        self.set_visibility_changed_fn(self._on_visibility_changed)
        self.set_focused_changed_fn(self._on_focused_changed)
        self._hotkey_context = None
        self._build_ui()

        def on_vp_width_changed(width: float, _self=weakref.ref(self)):
            if self := _self():
                self._list_window_updated = False
                self._on_viewport_size_changed()

        def on_vp_height_changed(height: float, _self=weakref.ref(self)):
            if self := _self():
                self._list_window_updated = False
                self._on_viewport_size_changed()

        # Set using the viewport_widget in the case where the viewport is a widget instead of a window
        self._viewport_handle = self._waypoint_instance.viewport_widget
        if not self._viewport_handle:
            self._viewport_handle = get_active_viewport_window()
            if self._viewport_handle:
                self._viewport_handle.set_height_changed_fn(on_vp_height_changed)
                self._viewport_handle.set_width_changed_fn(on_vp_width_changed)
                self._viewport_handle.set_position_x_changed_fn(self._on_viewport_size_changed)
                self._viewport_handle.set_position_y_changed_fn(self._on_viewport_size_changed)

        self._list_window_save_position = self._settings.get(SETTINGS_LIST_WINDOW_SAVE_POSITION)
        self._list_window_updated = False

        def application_mode_changed(*args, _self=weakref.ref(self)):  # pragma: no cover
            self = _self()
            if self:
                self._list_window_updated = False

        self._settings.subscribe_to_node_change_events(APPLICATION_MODE, application_mode_changed)

    @property
    def selected_index(self) -> "int|None":
        """Gets the index of selected waypoint from the list.

        Returns:
            int|None: The index of the selected waypoint, or None if no selection is made.
        """
        for idx, widget in enumerate(self._widgets):
            if widget.outer_stack.selected:
                return idx

    @selected_index.setter
    def selected_index(self, value: "int|None"):
        """Sets the selected index for the waypoint list.

        Args:
            value (int|None): The new index to select in the widget list. If None, no waypoint is recalled.
        """
        for idx, widget in enumerate(self._widgets):
            widget.outer_stack.selected = idx == value
            if widget.outer_stack.selected:
                self._waypoint_instance.recall_waypoint(widget.waypoint)
        if value is None:
            self._waypoint_instance.recall_waypoint(None)

    @property
    def widgets(self) -> "list[WaypointEntryWidget]":
        """Gets a copy of the list of waypoint entry widgets.

        Returns:
            list[WaypointEntryWidget]: A shallow copy of the widget list.
        """
        return self._widgets[:]

    def destroy(self):  # pragma: no cover
        """Destroys the WaypointListWindow by clearing the hotkey context, frame, widget lists, and deregistering the waypoint callback."""
        if self._hotkey_context:
            from ..extension import WAYPOINT_WINDOW_FOCUS_CONTEXT

            self._clear_hotkey_context(WAYPOINT_WINDOW_FOCUS_CONTEXT)
        self._hotkey_context = None
        self.frame.clear()
        self._widgets.clear()
        self._widgets_map.clear()
        self._waypoint_instance.deregister_callback(self._waypoint_callback)
        del self._waypoint_callback
        self._waypoint_instance = cast("WaypointExtension", None)
        self.visible = False
        if self._current_tool_setting_changed_sub is not None:
            self._settings.unsubscribe_to_change_events(self._current_tool_setting_changed_sub)
            self._current_tool_setting_changed_sub = None

    def _on_viewport_size_changed(self, *_):
        if not self.visible or self._viewport_handle is None:
            return

        first_update = not self._list_window_updated
        if first_update:
            self._list_window_updated = True

        try:
            vp = ui.Workspace.get_window(self._viewport_handle.title)
        except AttributeError:
            vp = ui.Workspace.get_window(self._waypoint_instance.main_window_name)

        right = vp.position_x + vp.width

        x = right - WaypointListWindow.WINDOW_WIDTH - WaypointListWindow.SPACING
        y = vp.position_y + WaypointListWindow.VIEWPORT_MAIN_MENUBAR_HEIGHT + WaypointListWindow.SPACING

        if vp.docked:
            if vp.dock_tab_bar_visible:
                y += 18

        if first_update or not self._list_window_save_position:
            self.setPosition(x, y)

        self._update_window_height(vp.height)

    def _update_window_height(self, vp_height):
        cy = vp_height - WaypointListWindow.VIEWPORT_MAIN_MENUBAR_HEIGHT - WaypointListWindow.SPACING

        show_count = max(self._waypoint_count, 1)
        if show_count == 0:
            show_count = 1
        elif show_count > MAX_SHOW_WAYPOINTS:
            show_count = MAX_SHOW_WAYPOINTS
        # 90 is thumbnail height
        # 30 is label height
        # 2 is spacer between thumbnail and label
        # 4 is scrolling frame padding
        height = min(
            self._container.computed_height + show_count * (90 + 30 + 2) + 4,
            cy - WaypointListWindow.VIEWPORT_MAIN_MENUBAR_HEIGHT,
        )

        if self.height < height:
            self.height = height

    def _on_visibility_changed(self, visible: bool):
        from ..extension import WAYPOINT_WINDOW_FOCUS_CONTEXT

        if visible:

            async def __delay_re_position(panel):
                await omni.kit.app.get_app().next_update_async()
                await omni.kit.app.get_app().next_update_async()
                panel._on_viewport_size_changed()
                if self._hotkey_context:
                    self._hotkey_context.push(WAYPOINT_WINDOW_FOCUS_CONTEXT)
                self.focus()

            asyncio.ensure_future(__delay_re_position(self))
        else:
            self._clear_hotkey_context(WAYPOINT_WINDOW_FOCUS_CONTEXT)

    def _on_focused_changed(self, focused: bool):
        if self._hotkey_context is None:
            try:
                import omni.kit.hotkeys.core

                self._hotkey_context = omni.kit.hotkeys.core.get_hotkey_context()
            except ImportError:  # pragma: no cover
                return
        from ..extension import WAYPOINT_WINDOW_FOCUS_CONTEXT

        if focused and self._hotkey_context.get() != WAYPOINT_WINDOW_FOCUS_CONTEXT:
            self._hotkey_context.push(WAYPOINT_WINDOW_FOCUS_CONTEXT)
        else:
            self._clear_hotkey_context(WAYPOINT_WINDOW_FOCUS_CONTEXT)

    def _clear_hotkey_context(self, context: str):
        if self._hotkey_context is not None:
            all_contexts = []
            while (top_context := self._hotkey_context.get()) is not None:
                all_contexts.append(top_context)
                self._hotkey_context.pop()
            for c in reversed(all_contexts):
                if c != context:
                    self._hotkey_context.push(c)

    def _add_new_waypoint(self):
        waypt_instance = self._waypoint_instance
        if waypt_instance:
            editing_waypt = waypt_instance.editing_waypoint
            if editing_waypt:
                return waypt_instance.end_edit_waypoint(editing_waypt, False, create=True)
            else:
                return waypt_instance.create_waypoint()

    def _build_ui(self):
        with self.frame:
            with ui.VStack(style=WINDOW_STYLE.copy()):
                self._container = ui.VStack(height=0)
                with self._container:
                    self._build_title()
                    ui.Spacer(height=8)
                    with ui.HStack(height=36):
                        ui.Spacer()
                        btn = ui.Button(
                            "Add Waypoint",
                            name="add_waypoint",
                            height=36,
                            width=36,
                            image_width=28,
                            image_height=28,
                            style=UI_STYLES,
                            style_type_name_override="Add.Button",
                            clicked_fn=lambda: self._add_new_waypoint(),
                        )
                        btn.spacing = 4
                        ui.Spacer(width=4)
                        ui.Button(
                            " ",
                            name="show_preference",
                            height=36,
                            width=36,
                            style=UI_STYLES,
                            style_type_name_override="Settings.Button",
                            clicked_fn=lambda: self._show_waypoint_settings(),
                        )
                        ui.Spacer()
                    ui.Spacer(height=2)
                    play_bar = PlayBar()
                    play_bar.bind_widget(self)
                    ui.Separator(height=5, menu_compatibility=False)
                self.__scroll_field = ui.ScrollingFrame(
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED
                )
                self._build_widget()

    def _build_widget(self):
        self._widgets.clear()
        self._widgets_map.clear()
        with self.__scroll_field:
            with ui.VStack(spacing=3):
                for waypoint in self._waypoint_instance.get_waypoints():
                    # If something is wrong with the primtive, skip it and wait for the next refresh.
                    if None in (waypoint.usd_prim, waypoint.comment, waypoint.thumbnail_data):
                        continue

                    outer_stack = ui.ZStack(
                        style={"GridView.Image:selected": {"debug_color": 0x0}},
                        content_clipping=1,
                        height=0,
                    )
                    with outer_stack:
                        with ui.VStack():
                            with ui.HStack():
                                ui.Spacer()
                                with ui.ZStack(width=0):
                                    thumbnail_provider = ui.ByteImageProvider()
                                    byte_data, width, height = waypoint.thumbnail_data or (b"", 0, 0)
                                    thumbnail_provider.set_bytes_data(bytearray(byte_data), [width, height])
                                    image = ui.ImageWithProvider(
                                        thumbnail_provider,
                                        alignment=ui.Alignment.CENTER,
                                        fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                                        height=90,
                                        width=160,
                                        style_type_name_override="GridView.Image",
                                        opaque_for_mouse_events=1,
                                        name=waypoint.name + " Thumbnail",
                                    )
                                    wp_item = WaypointItem(waypoint)
                                    hover = WaypointItemHoverWidget(
                                        wp_item,
                                        on_edit_begin_fn=lambda *x, wp=waypoint: self._waypoint_instance.begin_edit_waypoint(
                                            wp
                                        ),
                                    )
                                    hover.visible = False
                                    edit = WaypointItemEditWidget(wp_item)
                                    edit.visible = False
                                    ui.Rectangle(style_type_name_override="GridView.Item.Selection")
                                ui.Spacer()

                            collapse_frame = ui.CollapsableFrame(
                                waypoint.name,
                                collapsed=True,
                                build_header_fn=lambda col, txt, wp=waypoint: build_frame_header(wp, col, txt),
                            )
                            with collapse_frame:
                                field_stack = ui.ZStack()
                                with field_stack:
                                    model = ui.SimpleStringModel(waypoint.comment)
                                    field = ui.StringField(model, multiline=True, name=waypoint.name + " Comment")
                                    field.read_only = not self._waypoint_instance.can_edit_waypoint(
                                        waypoint, show_messages=False
                                    )
                                    field.enabled = self._waypoint_instance.can_edit_waypoint(
                                        waypoint, show_messages=False
                                    )

                            def on_collapse(collapsed: bool, wp=waypoint, stk=field_stack, fld=field):
                                if not collapsed:
                                    fld.model.as_string = wp.comment
                                    stk.height = ui.Pixel((fld.model.as_string.count("\n") + 2.6) * FONT_SIZE)
                                    fld.enabled = self._waypoint_instance.can_edit_waypoint(wp, show_messages=False)

                            collapse_frame.set_collapsed_changed_fn(on_collapse)

                            def value_changed(
                                mdl: ui.AbstractValueModel, stk=field_stack, wp: ViewportWaypoint = waypoint
                            ):
                                stk.height = ui.Pixel((mdl.as_string.count("\n") + 2.6) * FONT_SIZE)
                                wp.comment = mdl.as_string

                            model.add_end_edit_fn(value_changed)

                    image.set_mouse_pressed_fn(partial(self._on_click, wp=waypoint))
                    image.set_mouse_double_clicked_fn(partial(self._on_double_click, wp=waypoint))
                    image.set_mouse_hovered_fn(partial(self._on_hover, wp=waypoint))
                    entry_widget = WaypointEntryWidget(
                        waypoint, outer_stack, hover, collapse_frame, field_stack, field, edit
                    )
                    self._widgets.append(entry_widget)
                    self._widgets_map[waypoint] = entry_widget

        self._waypoint_count = len(self._widgets)

    def _on_click(self, x, y, btn, flag, wp=None):
        if self._widgets_map[wp].hover_widget.button_hovered:
            return
        if self._waypoint_instance.editing_waypoint and self._waypoint_instance.editing_waypoint != wp:
            return

        if btn == 0:
            self._waypoint_instance.recall_waypoint(wp)
            if self._widgets_map[wp].outer_stack.selected:
                return

            for wpoint, widget in self._widgets_map.items():
                widget.outer_stack.selected = wp == wpoint
                widget.collapse_frame.collapsed = bool(wp != wpoint or not widget.notes_field.model.as_string)
                if not widget.collapse_frame.collapsed:
                    widget.field_stack.height = ui.Pixel(
                        (widget.notes_field.model.as_string.count("\n") + 2.6) * FONT_SIZE
                    )

    def _on_double_click(self, x, y, btn, flag, wp=None):
        if self._widgets_map[wp].hover_widget.button_hovered:
            return
        if self._waypoint_instance.editing_waypoint and self._waypoint_instance.editing_waypoint != wp:
            return

        if btn == 0:
            self._waypoint_instance.recall_waypoint(wp)
            for wpoint, widget in self._widgets_map.items():
                widget.outer_stack.selected = wp == wpoint
                widget.collapse_frame.collapsed = bool(wp != wpoint or not widget.notes_field.model.as_string)
                if not widget.collapse_frame.collapsed:
                    widget.field_stack.height = ui.Pixel(
                        (widget.notes_field.model.as_string.count("\n") + 2.6) * FONT_SIZE
                    )

    def _on_hover(self, hov, wp=None):
        self._widgets_map[wp].hover_widget.visible = hov

    def _build_title(self):
        # Same as tear-off menubar
        with ui.ZStack(height=14):
            ui.Rectangle(style_type_name_override="Menu.Title")
            with ui.HStack():
                ui.Spacer(width=14)
                ui.Line(style_type_name_override="Menu.Title.Line")
                with ui.Frame(width=14):
                    ui.Image(
                        style_type_name_override="Menu.Item.CloseMark",
                        mouse_pressed_fn=lambda x, y, b, a: self._on_close_window(),
                    )

    def _on_close_window(self):
        self.visible = False

    def _show_waypoint_settings(self):
        self._waypoint_instance.show_preference(self.position_x + self.width, self.position_y)

    def _on_waypoints_changed(self, *args) -> None:
        self._waypoint_count = len(self._waypoint_instance.get_waypoints())
        try:
            vp = ui.Workspace.get_window(self._viewport_handle.title)
            self._update_window_height(vp.height)
        except AttributeError:
            pass
        self._build_widget()

    def _on_waypoint_changed(self, waypoint: "ViewportWaypoint|None"):
        self._build_widget()

    def _on_waypoint_editing_changed(self, item, event_type):
        waypoint_name = item.get_dict()
        for idx, (waypoint, entry_widget) in enumerate(self._widgets_map.items()):
            entry_widget.edit_widget.visible = False
            entry_widget.outer_stack.checked = False
            if waypoint_name == waypoint.name:
                self.selected_index = idx
                entry_widget.edit_widget.visible = True
                entry_widget.outer_stack.checked = True

    def _on_current_tool_changed(self, item, event_type):
        current_tool = self._settings.get_as_string(CURRENT_TOOL_PATH)
        if current_tool is None or current_tool.lower() == "none":
            self.visible = False
