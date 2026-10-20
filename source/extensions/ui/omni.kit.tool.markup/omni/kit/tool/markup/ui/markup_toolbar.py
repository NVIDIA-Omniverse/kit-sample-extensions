# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import weakref
from typing import TYPE_CHECKING, cast

import carb.dictionary
import carb.settings
import carb.tokens
import omni.kit.app
import omni.usd
from omni import ui
from omni.kit.async_engine import run_coroutine
from omni.kit.markup.core import get_instance as get_markup_instance

from .constant import (
    CURRENT_TOOL_PATH,
    EXTENSION_NAME,
    MARKUP_BLOCK_GESTURES,
    MARKUP_TOOL_CURRENT,
    MARKUP_TOOL_DEFAULT_CONFIG_SUBTOOL,
    MARKUP_TOOL_HIDE,
    MARKUP_TOOL_SETTINGS_ROOT,
    MARKUP_TOOLBAR_OFFSET,
    SETTINGS_MARKUP_ACTIVE,
    SETTINGS_MARKUP_EDITING,
    SETTINGS_MARKUP_ROOT,
    SETTINGS_PATH_MODAL_TOOL_ACTIVE,
    SETTINGS_UI_HIDE,
    SETTINGS_VIEWPORT_RECT,
    STYLE,
    TOOL_NAME,
    TOOL_PROPERTIES,
    float_rgb_to_hex_bgr,
    hex_abgr_to_float_rgb,
)
from .markup_scene import get_canvas_size, get_viewport_frame_size
from .markup_state import MarkupState, get_markup_state, return_to_previous_state, set_markup_state

if TYPE_CHECKING:  # pragma: no cover
    from omni.kit.markup.core import MarkupCore
    from omni.kit.markup.core import get_instance as _get_markup_instance
    from pxr import Sdf, Usd

    # This is a really dumb hack that convinces pylance that the extension instance won't ever be None - Bob
    def get_markup_instance() -> MarkupCore:  # noqa: E261, F811
        return cast(MarkupCore, _get_markup_instance())


IMAGE_SIZE = 43


class StyleColorComponentItem(ui.AbstractItem):
    def __init__(self, model: ui.SimpleFloatModel) -> None:
        super().__init__()
        self.model = model


class StyleColorModel(ui.AbstractItemModel):
    """define a model for a style color, and enable coversion from int32 etc"""

    def __init__(self, value: int) -> None:
        super().__init__()
        self._value = value

        # Create root model
        self._root_model = ui.SimpleIntModel()
        self._root_model.add_value_changed_fn(lambda a: self._item_changed(cast(ui.AbstractItem, None)))

        # convert Value from int
        red = self._value & 255
        green = (self._value >> 8) & 255
        blue = (self._value >> 16) & 255
        alpha = (self._value >> 24) & 255
        rgba_values = [red / 255, green / 255, blue / 255, alpha / 255]

        # Create three models per component
        self._items: "list[StyleColorComponentItem]" = [
            StyleColorComponentItem(ui.SimpleFloatModel(rgba_values[i])) for i in range(4)
        ]
        for item in self._items:
            item.model.add_value_changed_fn(lambda a, item=item: self._on_value_changed(item))

    def set_value(self, value: int):  # pragma: no cover
        self._value = value

    def get_value_as_int8s(self) -> "list[int]":

        result: "list[int]" = []
        for i in range(4):
            result.append(int(round(self._items[i].model.get_value_as_float() * 255)))

        return result

    def get_value_as_floats(self) -> "list[float]":  # pragma: no cover

        result: "list[float]" = []
        for i in range(4):
            result.append(self._items[i].model.get_value_as_float())

        return result

    def get_value_as_int32(self) -> int:
        red, green, blue, alpha = self.get_value_as_int8s()

        # we store then in AABBGGRR
        result = (alpha << 24) + (blue << 16) + (green << 8) + red
        return result

    def _on_value_changed(self, item):
        self._item_changed(item)

    def get_item_children(self, parentItem: ui.AbstractItem) -> "list[StyleColorComponentItem]":
        return self._items

    def get_item_value_model(self, item: StyleColorComponentItem, column_id: int) -> ui.AbstractValueModel:
        if item is None:  # pragma: no cover
            return self._root_model

        return item.model

    def begin_edit(self, item):
        """
        TODO: if we don't add this override (even without a real implementation) we get crashes
        """
        pass

    def end_edit(self, item):
        """
        TODO: if we don't add this override (even without a real implementation) we get crashes
        """
        pass


class MarkupTools:
    def __init__(self):
        self._settings = carb.settings.get_settings()
        self._settings_root = MARKUP_TOOL_SETTINGS_ROOT

        self._panel_stack = ui.ZStack()
        with self._panel_stack:
            self._element_toolbar_frame = ui.Frame()
            self._selected_element_frame = ui.Frame()

        self.build_panel()
        self._panel_stack.visible = False
        self._element_editbar = None

    def __del__(self):
        self._panel_stack.clear()

    def build_panel(self):
        with self._panel_stack:
            self._main_toolbar = MarkupToolbar()

    def on_markup_edit_changed(self, item: carb.dictionary.Item, event_type):
        self._main_toolbar.on_markup_edit_changed(item, event_type)
        self._panel_stack.visible = bool(item.get_dict())

        # When entering edit mode, set to default subtool
        default_subtool = self._settings.get_as_string(MARKUP_TOOL_DEFAULT_CONFIG_SUBTOOL)
        self._settings.set_string(MARKUP_TOOL_CURRENT, default_subtool)
        run_coroutine(self.create_element_toolbar(self._settings.get_as_string(MARKUP_TOOL_CURRENT)))

    def on_markup_active_changed(self, item: carb.dictionary.Item, event_type):
        self._main_toolbar.on_markup_active_changed(item, event_type)
        self._panel_stack.visible = bool(item.get_dict())
        run_coroutine(self.clear_frame(self._element_toolbar_frame))
        run_coroutine(self.clear_frame(self._selected_element_frame))

    def on_visibility_changed(self, item: carb.dictionary.Item, event_type):
        self._main_toolbar.frame.visible = not item.get_dict()

    def create_selected_element_toolbar(self, element):
        with self._selected_element_frame:
            self._element_editbar = ElementEditBar(element)

    async def create_element_toolbar(self, tool):
        if tool:
            with self._element_toolbar_frame:
                ElementToolBar(tool)
        else:
            run_coroutine(self.clear_frame(self._element_toolbar_frame))

    def on_subtool_changed(self, item, event_type):
        self._main_toolbar.on_active_tool_changed(item, event_type)
        run_coroutine(self.create_element_toolbar(item.get_dict()))

    def on_selected_element_changed(self, element):
        if element:
            self.create_selected_element_toolbar(element)
        else:
            if self._element_editbar:
                # I'm calling this wrapup() function here in case the color picker in this edit
                # bar gets destroyed before it's had the chance to call its edit end function and
                # write the color value to the markup primitive.
                self._element_editbar.wrapup()
                self._element_editbar = None
            run_coroutine(self.clear_frame(self._selected_element_frame))

    def on_app_state_sync_changed(self, item, event_type):
        if item.get_dict() == EXTENSION_NAME:
            set_markup_state(MarkupState.READY)
        else:
            self.deactivate_markup_tool()
            set_markup_state(MarkupState.DEACTIVATED)

    def deactivate_markup_tool(self):
        inst = get_markup_instance()
        vm = inst.editing_markup
        if vm:  # pragma: no cover
            inst.end_edit_markup(vm, save=False)
        inst.unlock_camera()
        inst.current_markup = None

    async def clear_frame(self, frame):
        frame.clear()


class Toolbar:
    _x: float
    _y: float
    offset: float
    _frame: ui.Frame
    frame: ui.Frame

    def __init__(self, frame_identifier=None):
        self._x = 0
        self._y = 0
        self._parent_stack = ui.ZStack()
        self.__hovered = False
        with self._parent_stack:
            self._placer = ui.Placer(draggable=False, drag_axis=ui.Axis.XY)
        with self._placer:
            if frame_identifier:
                self._frame = ui.Frame(identifier=frame_identifier)
            else:  # pragma: no cover
                self._frame = ui.Frame()
            with self._frame:
                self._stack = ui.ZStack(height=0, width=0)
                with self._stack:
                    # Hacky background.
                    ui.Rectangle(style={"background_color": 0xA0000000})
                    self.frame = ui.Frame(identifier=self._frame.identifier + "_childframe")

        self._settings = carb.settings.get_settings()
        self._parent_stack.set_computed_content_size_changed_fn(self.on_resize)
        self._frame.set_mouse_moved_fn(self._on_moved)
        self._frame.set_mouse_pressed_fn(self._on_pressed)
        self._frame.set_mouse_released_fn(self._on_released)
        self._frame.set_mouse_hovered_fn(self._on_hovered)
        self._resizing = False
        self._sub_id = (self._settings.subscribe_to_node_change_events(SETTINGS_VIEWPORT_RECT, self.on_resize),)
        self.offset = self._settings.get_as_int(MARKUP_TOOLBAR_OFFSET)
        self.on_resize()

    def __del__(self):  # pragma: no cover
        self._on_hovered(False)
        if self.sub_id is not None:
            self._settings.unsubscribe_to_change_events(self._sub_id)
            self._sub_id = None

    def _on_moved(self, x: float, y: float, btn: int, flag: int):
        if not self._frame.dragging:  # pragma: no cover
            return
        x_val = self._placer.offset_x + x - self._x
        x_max = self._parent_stack.computed_width - self._stack.computed_width
        new_x = max(0, min(x_val, x_max))
        y_val = self._placer.offset_y + y - self._y
        y_max = self._parent_stack.computed_height - self._stack.computed_height
        new_y = max(0, min(y_val, y_max))
        self._placer.offset_x = new_x
        self._placer.offset_y = new_y
        self._x, self._y = x, y

    def _on_pressed(self, x: float, y: float, btn: int, flag: int):
        if btn == 0:
            self._x, self._y = x, y
            self._frame.dragging = True

    def _on_released(self, x: float, y: float, btn: int, flag: int):
        if btn == 0:
            self._frame.dragging = False

    def _on_hovered(self, hov: bool):
        if self.__hovered != hov:
            self.__hovered = hov
            block_count = self._settings.get_as_int(MARKUP_BLOCK_GESTURES)
            block_count += 1 if hov else -1
            self._settings.set(MARKUP_BLOCK_GESTURES, block_count)

    def on_resize(self, *args):
        if not self._resizing:
            self._resizing = True
            run_coroutine(self._resize_internal())

    async def _resize_internal(self):
        await omni.kit.app.get_app().next_update_async()
        rect = self._settings.get(SETTINGS_VIEWPORT_RECT)
        if rect[1] < 0.0:  # pragma: no cover
            rect[3] += rect[1]
            rect[1] = 0.0
        if rect is not None and len(rect) == 4:
            self._placer.offset_x = (rect[0] + rect[2] - self._stack.computed_width) / 2
            self._placer.offset_y = rect[3] - self._stack.computed_height - self.offset
        else:  # pragma: no cover
            # if the setting isn't available, this works for 16:9 windows or taller windows, but not wider windows
            self._placer.offset_x = (self._parent_stack.computed_width - self._stack.computed_width) / 2
            self._placer.offset_y = self._parent_stack.computed_height - self._stack.computed_height - self.offset
        self._resizing = False


class MarkupToolbar(Toolbar):
    def __init__(self):
        super().__init__(frame_identifier="_markup_toolbar_frame")
        self._buttons = []
        self._btn_map = {}
        self._stack = None
        self._sub_id = self._settings.subscribe_to_node_change_events(SETTINGS_UI_HIDE, self.__on_tool_hide)

        self._build_ui()

    def __del__(self):  # pragma: no cover
        self._settings.unsubscribe_to_change_events(self._sub_id)
        self._buttons.clear()
        self._btn_map.clear()
        self._stack = None
        self._sub_id = None
        super().__del__()

    def __on_tool_hide(self, *_):
        if self._stack:
            self._stack.visible = True if not self._settings.get(SETTINGS_UI_HIDE) else False

    def _build_ui(self):
        btn_data: "tuple[tuple[str, str], ...]" = (
            # ("select", "Select markup elements"),
            (TOOL_NAME.COMMENT, "Create a text element"),
            (TOOL_NAME.DRAW, "Create a line element"),
            (TOOL_NAME.ARROW, "Create an arrow element"),
            (TOOL_NAME.LINE, "Create a line element"),
            (TOOL_NAME.SHAPES, "Create a circle or a rectangle element"),
            ("", ""),
            ("markup_apply", "Save the current markup data to the scene and quit the Markup tool"),
            ("markup_cancel", "Discard the current markup data and quit the Markup tool"),
            ("", ""),
            ("markup_unlock", "Unlock the selected markup element so it can be edited"),
            ("markup_exit", "Exit current Markup"),
        )
        with self.frame:
            self._stack = ui.HStack()
            with self._stack:
                for btn_name, tooltip in btn_data:
                    self._build_button(btn_name, tooltip)

        # Hiding these to get the size where we actually want it
        for btn in self._buttons[-3:]:
            btn.enabled = False
            btn.visible = False

    def _build_button(self, btn_name: str, tooltip: str):
        style = STYLE.copy()
        style["Image"]["image_url"] = f"${{omni.kit.tool.markup}}/data/icons/{btn_name.lower()}_tint.svg"
        btn_frame = ui.Frame(style=style, identifier=f"_markup_{btn_name}_btn", content_clipping=1, name=btn_name)
        self._buttons.append(btn_frame)
        self._btn_map[btn_name] = btn_frame
        btn_frame.checked = self._settings.get_as_string(MARKUP_TOOL_CURRENT) == btn_name
        _btn_name, _, label = btn_name.partition("_")
        if not label:
            label = _btn_name
        with btn_frame:
            with ui.ZStack(height=0, width=0):
                if not btn_name:
                    with ui.VStack(width=1):
                        ui.Spacer(height=10)
                        ui.Line(width=1, height=IMAGE_SIZE - 15, alignment=ui.Alignment.H_CENTER)
                        ui.Spacer(height=5)
                        return

                with ui.VStack():
                    with ui.HStack():
                        ui.Spacer()
                        with ui.ZStack(height=0, width=0):
                            ui.Rectangle(name="nv_button")
                            ui.Image(
                                name=btn_name,
                                width=IMAGE_SIZE,
                                height=IMAGE_SIZE,
                                tooltip=str(tooltip),
                                mouse_pressed_fn=lambda *x, btn_name=btn_name: self.on_mouse_pressed(btn_name),
                                identifier="toolbar_btn_" + btn_name,
                            )
                        ui.Spacer()
                    if label:
                        ui.Spacer(height=3)
                        with ui.HStack():
                            ui.Spacer()
                            ui.Label(label.title(), height=18, width=0)
                            ui.Spacer()

    def on_mouse_pressed(self, btn_name: str):
        if not self._btn_map[btn_name].enabled:  # pragma: no cover
            return

        # OMFP-3995 Override the existing markup state to prevent the tool from appearing locked
        # (e.g., if a user is drawing a markup, we are in the Draw state. If the user then mouses up
        # on the toolbar, they may enter a different tool, but the lingering Draw state will prevent
        # that tool from being usable).
        # Coming from EDIT/EDIT_COMMENT this also drops the current selection, so we never leave an
        # element's transform controls up while a drawing tool owns the canvas.
        set_markup_state(MarkupState.READY)

        valid = (TOOL_NAME.COMMENT, TOOL_NAME.DRAW, TOOL_NAME.ARROW, TOOL_NAME.SHAPES, TOOL_NAME.LINE)
        current = self._settings.get_as_string(MARKUP_TOOL_CURRENT)
        if btn_name == current:
            btn_name = self._settings.get_as_string(MARKUP_TOOL_DEFAULT_CONFIG_SUBTOOL)
        if btn_name in valid:
            self._settings.set_string(MARKUP_TOOL_CURRENT, btn_name)
            return

        inst = get_markup_instance()

        def on_edit_exit(*args, **kwargs):
            inst.unlock_camera()
            inst.current_markup = None
            inst.select_markup_in_list_window(None)
            self._settings.set(CURRENT_TOOL_PATH, "navigation")

        if btn_name == "markup_apply":
            vm = inst.editing_markup
            if vm:
                inst.end_edit_markup(vm, save=True, callback=lambda: on_edit_exit())
            return

        if btn_name == "markup_cancel":
            vm = inst.editing_markup
            if vm:
                # We only call the callback when saving.
                # So we need to do it manually.
                inst.end_edit_markup(vm, save=False)
                on_edit_exit(vm)
            return

        if btn_name == "markup_unlock":
            vm = inst.current_markup
            if vm and inst.can_edit_markup(vm):
                set_markup_state(MarkupState.READY)
                inst.begin_edit_markup(vm)
            return

        if btn_name == "markup_exit":
            on_edit_exit()
            set_markup_state(MarkupState.DEACTIVATED)
            return

    def on_active_tool_changed(self, item: carb.dictionary.Item, event_type):
        for button in self._buttons:
            button.checked = button.name == item.get_dict()

    def on_markup_edit_changed(self, item: carb.dictionary.Item, event_type):
        if item.get_dict():
            self._frame.visible = True
            for btn in self._buttons:
                btn.visible = True
                btn.enabled = True
            for btn in self._buttons[-3:]:
                btn.enabled = False
                btn.visible = False
        else:
            self._frame.visible = False
        self.on_resize()

    def on_markup_active_changed(self, item: carb.dictionary.Item, event_type):
        if item.get_dict():
            if not self._settings.get_as_string(SETTINGS_MARKUP_EDITING):
                self._frame.visible = True
                for btn in self._buttons:
                    btn.enabled = False
                    btn.visible = True
                for btn in self._buttons[-3:]:
                    btn.visible = True
                    btn.enabled = True
                for btn in self._buttons[-6:-3]:
                    btn.visible = False
                    btn.enabled = False
                self._settings.set_bool(SETTINGS_PATH_MODAL_TOOL_ACTIVE, True)
        else:
            self._frame.visible = False
            self._settings.set_bool(SETTINGS_PATH_MODAL_TOOL_ACTIVE, False)
        self.on_resize()


class ElementToolBar(Toolbar):
    def __init__(self, tool_name: str):
        super().__init__(frame_identifier="_markup_element_toolbar_frame")
        self._tool_name = tool_name
        self._button_groups = {}
        self._build_ui()
        self.offset = self._settings.get_as_int(MARKUP_TOOLBAR_OFFSET) + 75

    def _build_ui(self):
        with self.frame:
            self._stack = ui.HStack()
            with self._stack:
                for group, data in TOOL_PROPERTIES[self._tool_name].items():
                    self._button_groups[group] = []
                    for btn_name, value in data:
                        pth = f"{SETTINGS_MARKUP_ROOT}/{self._tool_name}/{group}"
                        style = STYLE.copy()
                        style["Image"][
                            "image_url"
                        ] = f"${{omni.kit.tool.markup}}/data/icons/{btn_name.lower()}_tint.svg"
                        btn = ui.Frame(
                            style=style,
                            identifier=f"_markup_{self._tool_name}_{group}_{btn_name}_btn",
                            name=btn_name,
                            content_clipping=1,
                        )
                        self._button_groups[group].append(btn)
                        btn.checked = self._settings.get_as_int(pth) == value
                        with btn:
                            if btn_name == "color":
                                self._build_color_widget(btn_name, pth)
                            else:
                                self._build_button(btn_name, value, group)

    def _build_button(self, btn_name: str, value: int, group: str):
        pth = f"{SETTINGS_MARKUP_ROOT}/{self._tool_name}/{group}"
        btn_group = self._button_groups[group]

        def mouse_pressed_fn(x, y, _btn, flag, pth=pth, value=value, btn_group=btn_group, btn_name=btn_name):
            self._settings.set_int(pth, value)
            for btn in btn_group:
                btn.checked = btn.name == btn_name

        with ui.HStack():
            ui.Spacer()
            with ui.ZStack(height=0, width=0):
                ui.Rectangle(name="nv_button")
                ui.Image(
                    name=btn_name,
                    height=30,
                    width=30,
                    mouse_pressed_fn=mouse_pressed_fn,
                    identifier="elementtool_btn_" + btn_name,
                )
            ui.Spacer()

    def _build_color_widget(self, btn_name: str, pth: str):
        def on_color_pressed(*_):
            # We can get caught in a dead state if we try to cache MarkupState.COLOR_PICKER
            if get_markup_state() == MarkupState.COLOR_PICKER:  # pragma: no cover
                return_to_previous_state()
            set_markup_state(MarkupState.COLOR_PICKER)

        def on_color_changed(*_):
            # OMFP-2485 if a user presses the mouse elsewhere in the viewport, then moves over the color widget
            # and releases the mouse, on_color_changed will be called without a prior call to on_color_pressed.
            # In this case, we'd ideally want the color widget to open its popup only when a mouse-down / mouse-up
            # pair of actions is invoked... but our workaround for now will be to not change the markup state
            # in this situation.
            return_to_previous_state()

        clr = ui.ColorWidget(height=30, width=30, mouse_pressed_fn=on_color_pressed, identifier="elementtool_btn_color")
        clr.model.add_end_edit_fn(on_color_changed)
        for idx, item in enumerate(clr.model.get_item_children()):
            clr_path = f"{pth}/{btn_name}"
            idx_path = f"{pth}/{btn_name}/{idx}"
            int_path = f"{pth}/abgr_color"

            def value_changed(model: ui.AbstractValueModel, clr_path=clr_path, idx_path=idx_path, int_path=int_path):
                self._settings.set_float(idx_path, model.as_float)
                color_val = cast("tuple[float,...]", self._settings.get(clr_path)) or (1, 1, 1, 1)
                if len(color_val) == 3:
                    color_val += (1,)
                hex_color = float_rgb_to_hex_bgr(color_val)
                self._settings.set_int(int_path, hex_color)

            value_model = clr.model.get_item_value_model(item)
            value_model.add_value_changed_fn(value_changed)
            # The fourth item alpha is not stored in the settings. Explicitly test against None,
            # set it to 1.0 without flipping other zero values.
            idx_value = self._settings.get(idx_path)
            if idx_value is None:
                value_model.as_float = 1.0
            else:
                value_model.as_float = idx_value


class ElementEditBar(Toolbar):
    def __init__(self, element):
        self._element = element
        self._prim_path = element.prim_path
        self._prim: "Usd.Prim" = element.prim
        super().__init__(frame_identifier="_markup_element_editbar_frame")
        self._element = element
        self._button_groups = {}
        self._btn_map = {}
        self._build_ui()
        self._element._transform_rect.changed_continuous += self.sync_bar
        self._editing_color = None

    def wrapup(self):

        # gets called when the element edit bar gets blown away. If we happen
        # to have set a color in the color picker, but the edit bar gets destroyed
        # before the end_edit function gets called, this will make sure the color data
        # gets written to the primitive:

        self._on_hovered(False)
        if self._editing_color is not None:  # pragma: no cover
            return_to_previous_state()
            self._element.update_style(color=self._editing_color, update_prim=True)
            self._editing_color = None

    def _build_ui(self):
        elem_type_map = {
            "Line": TOOL_NAME.DRAW,
            "Rectangle": TOOL_NAME.SHAPES,
            "Circle": TOOL_NAME.SHAPES,
            "Arrow": TOOL_NAME.ARROW,
            "Label": TOOL_NAME.COMMENT,
            "LineSegment": TOOL_NAME.LINE,
            "Shape": TOOL_NAME.SHAPES,
        }
        element = elem_type_map[self._element.type]

        with self.frame:
            self._stack = ui.HStack()
            with self._stack:
                for group, data in TOOL_PROPERTIES[element].items():
                    self._button_groups[group] = []
                    for btn_name, value in data:
                        style = STYLE.copy()
                        style["Image"][
                            "image_url"
                        ] = f"${{omni.kit.tool.markup}}/data/icons/{btn_name.lower()}_tint.svg"
                        btn = ui.Frame(
                            style=style,
                            identifier=f"_markup_edit_{self._element.prim_path}_{group}_{btn_name}_btn",
                            name=btn_name,
                            content_clipping=1,
                        )
                        self._button_groups[group].append(btn)
                        self._btn_map[btn_name] = btn
                        with btn:
                            if btn_name == "color":
                                self._build_color_widget()
                            else:
                                self._build_button(btn_name, value, group)
                btn_name = group = "remove"
                style = STYLE.copy()
                style["Image"]["image_url"] = "${omni.kit.tool.markup}/data/icons/remove_tint.svg"
                btn = ui.Frame(
                    style=style,
                    identifier=f"_markup_edit_{self._element.prim_path}_{group}_{btn_name}_btn",
                    name=btn_name,
                    content_clipping=1,
                )
                with btn:
                    self._build_remove_button(btn_name)

    def _build_button(self, btn_name: str, value: int, group: str):
        key_map = {"shape": "shape", "stroke": "stroke", "text": "font_size", "arrow": "direction"}

        def mouse_pressed_fn(x, y, _btn, flag, value=value, group=group, btn_name=btn_name):
            btn_group = self._button_groups[group]
            for btn in btn_group:
                btn.checked = btn.name == btn_name

            self._element.update_style(**{key_map[group]: value, "update_prim": True})

            # Keep it in Edit mode
            set_markup_state(MarkupState.STYLE_CHANGE)

        with ui.HStack():
            ui.Spacer()
            with ui.ZStack(height=0, width=0):
                ui.Rectangle(name="nv_button")
                ui.Image(
                    name=btn_name,
                    height=30,
                    width=30,
                    mouse_pressed_fn=mouse_pressed_fn,
                    identifier="elementbar_btn_" + btn_name,
                )
            ui.Spacer()
        self._btn_map[btn_name].checked = getattr(self._element._element, key_map[group], -1) == value

    def _build_color_widget(self):
        def on_color_pressed(*_):
            # We can get caught in a dead state if we try to cache MarkupState.COLOR_PICKER
            if get_markup_state() == MarkupState.COLOR_PICKER:  # pragma: no cover
                return_to_previous_state()
            set_markup_state(MarkupState.COLOR_PICKER)

        def item_changed(model, item):
            self._editing_color = model.get_value_as_int32()
            self._element.update_style(color=self._editing_color)

        def end_edit(model, index):
            return_to_previous_state()
            self._element.update_style(color=model.get_value_as_int32(), update_prim=True)
            self._editing_color = None

        model = StyleColorModel(self._element._element.color)
        model.add_item_changed_fn(item_changed)
        model.add_end_edit_fn(end_edit)
        ui.ColorWidget(model, height=30, width=30, mouse_pressed_fn=on_color_pressed, identifier="elementbar_btn_color")

    def _build_remove_button(self, btn_name):
        def mouse_pressed_fn(x, y, btn, flag):
            if btn == 0:
                self._element.remove_element()
                set_markup_state(MarkupState.READY)

        with ui.HStack():
            ui.Spacer()
            with ui.ZStack(height=0, width=0):
                ui.Rectangle(name="nv_button")
                ui.Image(
                    name=btn_name,
                    height=30,
                    width=30,
                    mouse_pressed_fn=mouse_pressed_fn,
                    identifier="elementbar_btn_remove",
                )
            ui.Spacer()

    async def _resize_internal(self):
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        self.sync_bar()

    def sync_bar(self, rect=None):
        if rect is None:
            x1, y1, x2, y2 = self._element.rect.flat
        else:
            x1, y1, x2, y2 = rect.flat

        midpoint_x = (x1 + x2) / 2.0
        midpoint_y = (y1 + y2) / 2.0

        canvas_width, canvas_height = get_canvas_size()

        margin_offset = 24
        bar_height = self._stack.computed_content_height
        bar_width = self._stack.computed_content_width

        wx, wy = get_viewport_frame_size()

        # left or right corner?
        canvas_width_offset = (wx - canvas_width) / 2
        if midpoint_x > 50.0:
            screen_x = min(x1, x2) / 100 * canvas_width + canvas_width_offset
        else:
            screen_x = max(x1, x2) / 100 * canvas_width + canvas_width_offset - bar_width + 1

        # top or bottom?
        canvas_height_offset = (wy - canvas_height) / 2
        if midpoint_y < 50.0:
            screen_y = max(y1, y2) / 100 * canvas_height + canvas_height_offset + margin_offset
        else:
            screen_y = min(y1, y2) / 100 * canvas_height + canvas_height_offset - bar_height - margin_offset

        # Clamping against edge of the viewport because we really don't want to draw outside of it.
        self._placer.offset_x = max(
            canvas_width_offset, min(screen_x, canvas_width + canvas_width_offset - self._stack.computed_width)
        )
        self._placer.offset_y = max(
            canvas_height_offset, min(screen_y, canvas_height + canvas_height_offset - self._stack.computed_height)
        )
