# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["MarkupScene"]
import asyncio
import contextlib
import math
import weakref
from typing import TYPE_CHECKING, cast

import carb.dictionary
import carb.input
import carb.settings
import omni.kit.commands
import omni.kit.undo
import omni.usd
from carb.input import Keyboard, KeyboardInput
from omni import ui
from omni.kit.markup.core import get_instance as get_markup_instance  # type: ignore
from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_window
from omni.ui import scene as sc

from .constant import (
    MARKUP_BLOCK_GESTURES,
    MARKUP_SELECT_CLICK_GESTURE,
    MARKUP_TOOL_CURRENT,
    MARKUP_TOOL_ELEMENT_TYPE,
    MARKUP_TOOL_SUBTOOL_ARROW_ARROW_END,
    MARKUP_TOOL_SUBTOOL_ARROW_STROKE_M,
    MARKUP_TOOL_SUBTOOL_COLOR_RED,
    MARKUP_TOOL_SUBTOOL_COMMENT_TEXT_M,
    MARKUP_TOOL_SUBTOOL_DRAW_STROKE_M,
    MARKUP_TOOL_SUBTOOL_LINE_STROKE_M,
    MARKUP_TOOL_SUBTOOL_SHAPE_STROKE_M,
    MARKUP_TOOL_SUBTOOL_SHAPES_SHAPE_RECT,
    SETTINGS_MARKUP_ACTIVE,
    SETTINGS_MARKUP_EDITING,
    SETTINGS_MARKUP_ROOT,
    SHORTEST_ALLOWED_ELEMENT,
    TOOL_NAME,
    float_rgb_to_hex_bgr,
    hex_bgr_to_float_rgb,
)
from .data import MarkupType
from .markup_state import MarkupState, get_markup_state, set_markup_state
from .markup_transform import DRAG_SIZE

if TYPE_CHECKING:  # pragma: no cover
    from typing import Iterator

    from omni.kit.markup.core import MarkupCore
    from omni.kit.markup.core import get_instance as _get_markup_instance
    from omni.kit.widget.viewport.api import ViewportAPI

    # This is a really dumb hack that convinces pylance that the extension instance won't ever be None - Bob
    def get_markup_instance() -> MarkupCore:  # noqa: E261, F811
        return cast(MarkupCore, _get_markup_instance())


@contextlib.contextmanager
def create_gesture_placer(parent_stack: ui.Stack, *, size: float = 0.001) -> "Iterator[tuple[ui.Placer, ui.Shape]]":
    def constrain_x(pos: ui.Length):
        max_width = (parent_stack.computed_content_width - size) / parent_stack.computed_content_width * 100
        placer.offset_x = ui.Percent(max(0, min(float(pos), max_width)))

    def constrain_y(pos: ui.Length):
        max_height = (parent_stack.computed_content_height - size) / parent_stack.computed_content_height * 100
        placer.offset_y = ui.Percent(max(0, min(float(pos), max_height)))

    with parent_stack:
        placer = ui.Placer(offset_x_changed_fn=constrain_x, offset_y_changed_fn=constrain_y, stable_size=True)

        with placer:
            with ui.ZStack(height=0, width=0):
                shape = ui.Circle(width=size, height=size)
                yield placer, shape


def _convert_ndc_to_markup_canvas(coords: "tuple[float, float]") -> "tuple[float, float]":
    # NDC: is gesture space, which is coming in as [1, -1] values from the markup canvas.
    # We just need to convert those into % of the canvas, normalized.
    # with the slight hitch of needing to flip the y value, because of how the UI draws from left-top
    x, y = coords
    tx, ty = max(0, min((x + 1.0) * 0.5, 1)), max(0, min((-y + 1.0) * 0.5, 1))
    return tx * 100, ty * 100


def get_viewport_frame_size(viewport_window=None):
    if viewport_window is None:
        viewport_window = get_active_viewport_window()

    wx = viewport_window.width - 2 * viewport_window.padding_x
    wy = viewport_window.height - 2 * viewport_window.padding_y - 22 * viewport_window.dock_tab_bar_visible
    return wx, wy


def get_canvas_size(viewport_window=None):
    if viewport_window is None:
        viewport_window = get_active_viewport_window()

    viewport_api = viewport_window.viewport_api
    rx, ry = viewport_api.resolution
    wx, wy = get_viewport_frame_size(viewport_window)

    vp_widget = viewport_window.viewport_widget if viewport_window else None
    fill_viewport = vp_widget.expand_viewport if vp_widget else False

    if fill_viewport:  # pragma: no cover
        new_width = wx
        new_height = wx / 16 * 9
    elif rx / ry < wx / wy:  # pragma: no cover
        new_width = rx / ry * wy
        new_height = wy
    else:  # pragma: no cover
        new_width = wx
        new_height = ry / rx * wx

    return new_width, new_height


class MarkupGestureManager(sc.GestureManager):

    def __init__(self, extension):
        super().__init__()
        self._settings_path = SETTINGS_MARKUP_ROOT
        self._active_tool_path = MARKUP_TOOL_CURRENT
        self._should_block_path = MARKUP_BLOCK_GESTURES
        self._settings = carb.settings.get_settings()
        self._tool_instance = weakref.ref(extension)

    def can_be_prevented(self, gesture: sc.AbstractGesture) -> bool:
        return True

    def should_prevent(self, gesture: sc.AbstractGesture, preventer: sc.AbstractGesture) -> bool:
        # Early out, we don't want these tools working unless we're actively editing an entry.
        if not self._settings.get_as_string(SETTINGS_MARKUP_EDITING):
            return True

        block_count = self._settings.get_as_int(self._should_block_path)
        if block_count > 0:
            return True

        # The Select tool is always active
        if gesture.name == MARKUP_SELECT_CLICK_GESTURE:
            return False

        if get_markup_state() in (MarkupState.EDIT, MarkupState.EDIT_COMMENT):
            return True

        current_tool = self._settings.get_as_string(self._active_tool_path)
        if current_tool and gesture.name.endswith(current_tool):
            return False

        return True

    def acquire_gesture_block(self) -> None:
        block_count = self._settings.get_as_int(self._should_block_path)
        self._settings.set_int(self._should_block_path, block_count + 1)

    def release_gesture_block(self) -> None:
        block_count = self._settings.get_as_int(self._should_block_path)
        self._settings.set_int(self._should_block_path, max(0, block_count - 1))

    @property
    def settings_path(self):
        return self._settings_path

    @property
    def tool_instance(self):
        return self._tool_instance()


class DragHelper:
    def __init__(self):
        self.__drag_pending = False
        self.__x = 0.0
        self.__y = 0.0

    def clear_pending_drag(self):
        self.__drag_pending = False
        self.__x = 0.0
        self.__y = 0.0

    def start_pending_drag(self, x: float, y: float):
        self.__drag_pending = True
        self.__x, self.__y = _convert_ndc_to_markup_canvas((x, y))

    def update_pending_drag(self, begin_drag_fn, x: float, y: float):
        if self.__drag_pending:
            tx, ty = _convert_ndc_to_markup_canvas((x, y))
            dx, dy = tx - self.__x, ty - self.__y
            length_squared = dx * dx + dy * dy
            if length_squared > SHORTEST_ALLOWED_ELEMENT:
                begin_drag_fn(self.__x, self.__y)
                self.clear_pending_drag()


class SelectTool:

    _manager: MarkupGestureManager
    screen: sc.Screen

    def __init__(self, manager: MarkupGestureManager):
        self._manager = manager
        click_gesture = sc.ClickGesture(manager=manager, name=MARKUP_SELECT_CLICK_GESTURE, on_ended_fn=self._on_clicked)
        self.screen = sc.Screen(gestures=[click_gesture])

    def _on_clicked(self, sender: sc.Screen):
        if get_markup_state() == MarkupState.READY:
            x, y = cast("tuple[float, float]", sender.gesture_payload.mouse)
            tx, ty = _convert_ndc_to_markup_canvas((x, y))
            if self._manager.tool_instance:
                element = self._manager.tool_instance.get_element_at(tx, ty)
                if element:
                    self._manager.tool_instance.refresh_elements(selected_element=element)
                    if element.type == MarkupType.TEXT:
                        set_markup_state(MarkupState.EDIT_COMMENT)
                    else:
                        set_markup_state(MarkupState.EDIT)
                else:
                    set_markup_state(MarkupState.READY)


class ShapeTool(DragHelper):

    _api: "ViewportAPI"
    _drag_start: "tuple[float, float]"
    _input: carb.input.IInput
    _manager: MarkupGestureManager
    _settings_item: carb.dictionary.Item
    _settings: carb.settings.ISettings
    screen: sc.Screen

    def __init__(self, manager: MarkupGestureManager):
        super().__init__()
        self._manager = manager
        self._settings = carb.settings.get_settings()
        self._settings_path = "/".join([manager.settings_path, TOOL_NAME.SHAPES])
        self._settings_item = self._settings.get_settings_dictionary(self._settings_path)
        if self._settings_item is None:  # pragma: no cover
            item = carb.dictionary.get_dictionary().create_item(None, "", carb.dictionary.ItemType.DICTIONARY)
            self._settings.update(self._settings_path, item, "", carb.dictionary.UpdateAction.OVERWRITE)
            self._settings_item = self._settings.get_settings_dictionary(self._settings_path)

        self._input = carb.input.acquire_input_interface()
        self._api = cast("ViewportAPI", get_active_viewport())
        drag_gesture = sc.DragGesture(
            name="markup_shapes",
            manager=manager,
            on_began_fn=self.begin_drag,
            on_changed_fn=self.drag,
            on_ended_fn=self.end_drag,
        )
        self.screen = sc.Screen(gestures=[drag_gesture])
        self._frame = ui.Frame()
        with self._frame:
            with ui.ZStack():
                self._drag_stack = ui.ZStack()
                self._temp_stack = ui.ZStack()

        self._temp_shape = None

    @property
    def shape(self) -> int:
        return cast(int, self._settings_item.get("shape", MARKUP_TOOL_SUBTOOL_SHAPES_SHAPE_RECT))

    @property
    def color(self) -> int:
        return cast(int, self._settings_item.get("color/abgr_color", MARKUP_TOOL_SUBTOOL_COLOR_RED))

    @property
    def stroke(self) -> int:
        return cast(int, self._settings_item.get("stroke", MARKUP_TOOL_SUBTOOL_SHAPE_STROKE_M))

    @property
    def style(self) -> dict:
        return {
            v: {"background_color": 0x0, "border_color": self.color, "border_width": self.stroke}
            for v in ("FreeRectangle", "FreeCircle", "FreeEllipse")
        }

    def begin_drag(self, sender: sc.Screen):
        self.clear_pending_drag()
        if get_markup_state() == MarkupState.READY:
            x, y = cast("tuple[float, float]", sender.gesture_payload.mouse)
            tx, ty = _convert_ndc_to_markup_canvas((x, y))

            if self._manager.tool_instance:
                element = self._manager.tool_instance.get_element_at(tx, ty)
                if element:
                    self.start_pending_drag(x, y)
                    return

            self.initialize_drag(tx, ty)

    def initialize_drag(self, tx: float, ty: float):
        set_markup_state(MarkupState.SHAPE)
        self._drag_start = (tx, ty)
        self._current = (tx, ty)

        with create_gesture_placer(self._drag_stack) as (self.p1, self.c1):
            self.p1.offset_x = ui.Percent(tx)
            self.p1.offset_y = ui.Percent(ty)
        with create_gesture_placer(self._drag_stack) as (self.p2, self.c2):
            self.p2.offset_x = ui.Percent(tx)
            self.p2.offset_y = ui.Percent(ty)

    def drag(self, sender: sc.Screen):
        x, y = cast("tuple[float, float]", sender.gesture_payload.mouse)
        self.update_pending_drag(self.initialize_drag, x, y)

        if get_markup_state() == MarkupState.SHAPE:
            shift = bool(self._input.get_keyboard_value(cast(Keyboard, None), KeyboardInput.LEFT_SHIFT))
            ctrl = bool(self._input.get_keyboard_value(cast(Keyboard, None), KeyboardInput.LEFT_CONTROL))
            ex, ey = _convert_ndc_to_markup_canvas((x, y))
            sx, sy = self._drag_start
            # Shift turns our rectangles into squares, and our ellipses into Circles
            # Need to convert to pixels otherwise we get aspect ratio'd shapes because we use `ui.Percent`
            if shift:
                rx, ry = cast("tuple[float, float]", self._api.resolution)
                dx = ex - sx
                dy = ey - sy
                px = rx * dx / 100
                py = ry * dy / 100
                md = abs(min(px, py))
                ex = sx + math.copysign(md / rx * 100, dx)
                ey = sy + math.copysign(md / ry * 100, dy)

            # Ctrl centers the shape on the initial click, this is done after the
            # `shift` check so that they can work together harmoniously
            if ctrl:
                cx, cy = sx, sy
                sx = cx - (ex - cx)
                sy = cy - (ey - cy)

            self.p1.offset_x = ui.Percent(sx)
            self.p1.offset_y = ui.Percent(sy)

            self.p2.offset_x = ui.Percent(ex)
            self.p2.offset_y = ui.Percent(ey)

            if not self._temp_shape:
                with self._drag_stack:
                    if self.shape:  # pragma: no cover
                        self._temp_shape = ui.FreeEllipse(self.c1, self.c2, style=self.style)
                    else:
                        self._temp_shape = ui.FreeRectangle(self.c1, self.c2, style=self.style)

    def end_drag(self, sender: sc.Screen):
        self.clear_pending_drag()
        if get_markup_state() == MarkupState.SHAPE:
            if self._diagonal_length_sq() > SHORTEST_ALLOWED_ELEMENT:
                # NOTE: in the case of SHAPE elements, the initial refresh_elements that creates a MarkupElement for
                # visualization will trigger additional update commands. We wrap the shape's creation and those
                # subsequent commands in a group so that a single Undo will remove the shape, as would be
                # reasonably expected.
                with omni.kit.undo.group():
                    # Actually create the shape, and clear the tool's layers.
                    # Need to test this better with friends, also the renderer is broken in this branch, so need to fix that.
                    get_markup_instance().add_element(
                        *[float(b) for b in (self.p1.offset_x, self.p1.offset_y, self.p2.offset_x, self.p2.offset_y)],
                        element_type=(
                            MARKUP_TOOL_ELEMENT_TYPE.CIRCLE if self.shape else MARKUP_TOOL_ELEMENT_TYPE.RECTANGLE
                        ),
                        element_style=self.style,
                    )
                    if self._manager.tool_instance:
                        self._manager.tool_instance.refresh_elements()
            self._drag_stack.clear()
            self._temp_stack.clear()
            self._temp_shape = None

            set_markup_state(MarkupState.READY)

    def _diagonal_length_sq(self):
        len_x = self.p2.offset_x - self.p1.offset_x
        len_y = self.p2.offset_y - self.p1.offset_y
        return len_x * len_x + len_y * len_y


class ArrowTool(DragHelper):

    _manager: MarkupGestureManager
    _settings: carb.settings.ISettings
    _settings_item: "carb.dictionary.Item"
    screen: sc.Screen

    def __init__(self, manager: MarkupGestureManager):
        super().__init__()
        self._manager = manager
        self._settings = carb.settings.get_settings()
        self._settings_path = "/".join([manager.settings_path, TOOL_NAME.ARROW])
        self._settings_item = self._settings.get_settings_dictionary(self._settings_path)
        if self._settings_item is None:  # pragma: no cover
            item = carb.dictionary.get_dictionary().create_item(None, "", carb.dictionary.ItemType.DICTIONARY)
            self._settings.update(self._settings_path, item, "", carb.dictionary.UpdateAction.OVERWRITE)
            self._settings_item = self._settings.get_settings_dictionary(self._settings_path)

        drag_gesture = sc.DragGesture(
            name="markup_arrow",
            manager=manager,
            on_began_fn=self.on_begin_drag,
            on_changed_fn=self.on_drag,
            on_ended_fn=self.on_end_drag,
        )
        self.screen = sc.Screen(gestures=[drag_gesture])
        self._frame = ui.Frame()
        with self._frame:
            with ui.ZStack():
                self._drag_stack = ui.ZStack()
                self._temp_stack = ui.ZStack()

        self._temp_arrow = None

    def on_begin_drag(self, sender: sc.Screen):
        self.clear_pending_drag()
        if get_markup_state() == MarkupState.READY:
            x, y = cast("tuple[float, float]", sender.gesture_payload.mouse)
            tx, ty = _convert_ndc_to_markup_canvas((x, y))

            if self._manager.tool_instance:
                element = self._manager.tool_instance.get_element_at(tx, ty)
                if element:
                    self.start_pending_drag(x, y)
                    return

            self.initialize_drag(tx, ty)

    def initialize_drag(self, tx: float, ty: float):
        set_markup_state(MarkupState.ARROW)

        with create_gesture_placer(self._drag_stack) as (self._p1, self._c1):
            self._p1.offset_x = tx
            self._p1.offset_y = ty
        with create_gesture_placer(self._drag_stack) as (self._p2, self._c2):
            self._p2.offset_x = tx
            self._p2.offset_y = ty

    def on_drag(self, sender: sc.Screen):
        x, y = cast("tuple[float, float]", sender.gesture_payload.mouse)
        self.update_pending_drag(self.initialize_drag, x, y)

        if get_markup_state() == MarkupState.ARROW:
            tx, ty = _convert_ndc_to_markup_canvas((x, y))
            self._p2.offset_x = tx
            self._p2.offset_y = ty

            if not self._temp_arrow:
                with self._temp_stack:
                    self._temp_arrow = ui.FreeLine(
                        self._c1, self._c2, style=self.style, alignment=ui.Alignment.UNDEFINED
                    )
                    arrow_dir = self.arrow_direction
                    arrow_size: float = self.border_width * 3.0
                    self._temp_arrow.begin_arrow_height = arrow_size  # length
                    self._temp_arrow.begin_arrow_width = arrow_size  # width
                    self._temp_arrow.end_arrow_height = arrow_size  # length
                    self._temp_arrow.end_arrow_width = arrow_size  # width
                    if arrow_dir == 0:
                        self._temp_arrow.begin_arrow_type = ui.ArrowType.ARROW
                        self._temp_arrow.end_arrow_type = ui.ArrowType.NONE
                    elif arrow_dir == 1:
                        self._temp_arrow.begin_arrow_type = ui.ArrowType.NONE
                        self._temp_arrow.end_arrow_type = ui.ArrowType.ARROW
                    elif arrow_dir == 2:
                        self._temp_arrow.begin_arrow_type = ui.ArrowType.ARROW
                        self._temp_arrow.end_arrow_type = ui.ArrowType.ARROW

    def on_end_drag(self, sender: sc.Screen):
        self.clear_pending_drag()
        if get_markup_state() == MarkupState.ARROW:

            # reject if the arrow is too short
            if self._arrow_length_sq() > SHORTEST_ALLOWED_ELEMENT:
                # Actually create the shape, and clear the tool's layers.
                # Need to test this better with friends, also the renderer is broken in this branch, so need to fix that.
                get_markup_instance().add_element(
                    *[float(b) for b in (self._p1.offset_x, self._p1.offset_y, self._p2.offset_x, self._p2.offset_y)],
                    element_type=MARKUP_TOOL_ELEMENT_TYPE.ARROW,
                    element_style=self.style,
                )
                if self._manager.tool_instance:
                    self._manager.tool_instance.refresh_elements()
            self._drag_stack.clear()
            self._temp_stack.clear()
            self._temp_arrow = None

            set_markup_state(MarkupState.READY)

    def _arrow_length_sq(self):
        len_x = self._p2.offset_x - self._p1.offset_x
        len_y = self._p2.offset_y - self._p1.offset_y
        return len_x * len_x + len_y * len_y

    @property
    def style(self):
        return {
            "FreeLine": {
                "background_color": 0x0,
                "color": self.color,
                "border_width": self.border_width,
                "border_radius": 0,
            },
            "Line": {
                "background_color": 0x0,
                "color": self.color,
                "border_width": self.border_width,
                "border_radius": 0,
            },
            "ArrowDirection": self.arrow_direction,
        }

    @property
    def color(self) -> int:
        return cast(int, self._settings_item.get("color/abgr_color", MARKUP_TOOL_SUBTOOL_COLOR_RED))

    @property
    def border_width(self) -> int:
        return cast(int, self._settings_item.get("stroke", MARKUP_TOOL_SUBTOOL_ARROW_STROKE_M))

    @property
    def arrow_direction(self) -> int:
        return cast(int, self._settings_item.get("arrow", MARKUP_TOOL_SUBTOOL_ARROW_ARROW_END))


class LineTool(DragHelper):

    _manager: MarkupGestureManager
    _settings: carb.settings.ISettings
    _settings_item: "carb.dictionary.Item"
    screen: sc.Screen

    def __init__(self, manager: MarkupGestureManager):
        super().__init__()
        self._manager = manager
        self._settings = carb.settings.get_settings()
        self._settings_path = "/".join([manager.settings_path, TOOL_NAME.LINE])
        self._settings_item = self._settings.get_settings_dictionary(self._settings_path)
        if self._settings_item is None:  # pragma: no cover
            item = carb.dictionary.get_dictionary().create_item(None, "", carb.dictionary.ItemType.DICTIONARY)
            self._settings.update(self._settings_path, item, "", carb.dictionary.UpdateAction.OVERWRITE)
            self._settings_item = self._settings.get_settings_dictionary(self._settings_path)

        drag_gesture = sc.DragGesture(
            name="markup_line",
            manager=manager,
            on_began_fn=self.on_begin_drag,
            on_changed_fn=self.on_drag,
            on_ended_fn=self.on_end_drag,
        )
        self.screen = sc.Screen(gestures=[drag_gesture])
        self._frame = ui.Frame()
        with self._frame:
            with ui.ZStack():
                self._drag_stack = ui.ZStack()
                self._temp_stack = ui.ZStack()

        self._temp_line = None

    def on_begin_drag(self, sender: sc.Screen):
        self.clear_pending_drag()
        if get_markup_state() == MarkupState.READY:
            x, y = cast("tuple[float, float]", sender.gesture_payload.mouse)
            tx, ty = _convert_ndc_to_markup_canvas((x, y))

            if self._manager.tool_instance:
                element = self._manager.tool_instance.get_element_at(tx, ty)
                if element:
                    self.start_pending_drag(x, y)
                    return

            self.initialize_drag(tx, ty)

    def initialize_drag(self, tx: float, ty: float):
        set_markup_state(MarkupState.LINE)
        with create_gesture_placer(self._drag_stack) as (self._p1, self._c1):
            self._p1.offset_x = tx
            self._p1.offset_y = ty
        with create_gesture_placer(self._drag_stack) as (self._p2, self._c2):
            self._p2.offset_x = tx
            self._p2.offset_y = ty

    def on_drag(self, sender: sc.Screen):
        x, y = cast("tuple[float, float]", sender.gesture_payload.mouse)
        self.update_pending_drag(self.initialize_drag, x, y)

        if get_markup_state() == MarkupState.LINE:
            tx, ty = _convert_ndc_to_markup_canvas((x, y))
            self._p2.offset_x = tx
            self._p2.offset_y = ty

            if not self._temp_line:
                with self._temp_stack:
                    self._temp_line = ui.FreeLine(
                        self._c1, self._c2, style=self.style, alignment=ui.Alignment.UNDEFINED
                    )

    def on_end_drag(self, sender: sc.Screen):
        self.clear_pending_drag()
        if get_markup_state() == MarkupState.LINE:

            # reject if the arrow is too short
            if self._line_length_sq() > SHORTEST_ALLOWED_ELEMENT:
                # Actually create the shape, and clear the tool's layers.
                # Need to test this better with friends, also the renderer is broken in this branch, so need to fix that.
                get_markup_instance().add_element(
                    *[float(b) for b in (self._p1.offset_x, self._p1.offset_y, self._p2.offset_x, self._p2.offset_y)],
                    element_type=MARKUP_TOOL_ELEMENT_TYPE.SEGMENT,
                    element_style=self.style,
                )
                if self._manager.tool_instance:
                    self._manager.tool_instance.refresh_elements()
            self._drag_stack.clear()
            self._temp_stack.clear()
            self._temp_line = None

            set_markup_state(MarkupState.READY)

    def _line_length_sq(self):
        len_x = self._p2.offset_x - self._p1.offset_x
        len_y = self._p2.offset_y - self._p1.offset_y
        return len_x * len_x + len_y * len_y

    @property
    def style(self):
        return {
            "FreeLine": {
                "background_color": 0x0,
                "color": self.color,
                "border_width": self.border_width,
                "border_radius": 0,
            },
            "Line": {
                "background_color": 0x0,
                "color": self.color,
                "border_width": self.border_width,
                "border_radius": 0,
            },
        }

    @property
    def color(self) -> int:
        return cast(int, self._settings_item.get("color/abgr_color", MARKUP_TOOL_SUBTOOL_COLOR_RED))

    @property
    def border_width(self) -> int:
        return cast(int, self._settings_item.get("stroke", MARKUP_TOOL_SUBTOOL_LINE_STROKE_M))


class DrawTool(DragHelper):

    _manager: MarkupGestureManager
    _settings: carb.settings.ISettings
    _settings_item: "carb.dictionary.Item"
    screen: sc.Screen

    def __init__(self, manager: MarkupGestureManager):
        super().__init__()
        self._manager = manager
        self._settings = carb.settings.get_settings()
        self._settings_path = "/".join([manager.settings_path, TOOL_NAME.DRAW])
        self._settings_item = self._settings.get_settings_dictionary(self._settings_path)
        if self._settings_item is None:  # pragma: no cover
            item = carb.dictionary.get_dictionary().create_item(None, "", carb.dictionary.ItemType.DICTIONARY)
            self._settings.update(self._settings_path, item, "", carb.dictionary.UpdateAction.OVERWRITE)
            self._settings_item = self._settings.get_settings_dictionary(self._settings_path)

        self._name = "markup_draw"
        drag_gesture = sc.DragGesture(
            name=self._name,
            manager=manager,
            on_began_fn=self.on_begin_drag,
            on_changed_fn=self.on_drag,
            on_ended_fn=self.on_end_drag,
        )
        self.screen = sc.Screen(gestures=[drag_gesture])
        self._frame = ui.Frame()
        with self._frame:
            with ui.ZStack():
                self._drag_stack = ui.ZStack()
                self._temp_stack = ui.ZStack()
        self._points = []
        self._prev_c1 = None
        self._prev_c2 = None

    def on_begin_drag(self, sender: sc.Screen):
        self.clear_pending_drag()
        if get_markup_state() == MarkupState.READY:
            x, y = cast("tuple[float, float]", sender.gesture_payload.mouse)
            tx, ty = _convert_ndc_to_markup_canvas((x, y))

            if self._manager.tool_instance:
                element = self._manager.tool_instance.get_element_at(tx, ty)
                if element:
                    self.start_pending_drag(x, y)
                    return

            self.initialize_drag(tx, ty)

    def initialize_drag(self, tx: float, ty: float):
        set_markup_state(MarkupState.DRAW)

        self._points.clear()
        self._points.append((tx, ty))

        self._prev_c1 = None
        self._prev_c2 = None

    def on_drag(self, sender: sc.Screen):
        x, y = cast("tuple[float, float]", sender.gesture_payload.mouse)
        self.update_pending_drag(self.initialize_drag, x, y)

        if get_markup_state() == MarkupState.DRAW:
            if not self._points:  # pragma: no cover
                return
            if len(self._points) == 1:
                # place initial vertex
                with create_gesture_placer(self._drag_stack, size=self.border_width) as (self._p1, self._c1):
                    self._p1.draggable = False
                    self._p1.offset_x = self._points[0][0]
                    self._p1.offset_y = self._points[0][1]

            # get the next vertex
            tx, ty = _convert_ndc_to_markup_canvas((x, y))
            self._points.append((tx, ty))

            # Next placer
            with create_gesture_placer(self._drag_stack, size=self.border_width) as (self._p2, self._c2):
                self._p2.draggable = False
                self._p2.offset_x = tx
                self._p2.offset_y = ty

            self._c1.style = self._c2.style = self.style

            # draw the line segment, delayed by a frame so that circle widgets are in the correct place
            with self._temp_stack:
                if self._prev_c1 and self._prev_c2:
                    ui.FreeLine(self._prev_c1, self._prev_c2, style=self.style, alignment=ui.Alignment.UNDEFINED)

            self._prev_c1 = self._c1
            self._prev_c2 = self._c2

            # next becomes prev
            self._p1, self._c1 = self._p2, self._c2

    def on_end_drag(self, sender: sc.Screen):
        self.clear_pending_drag()
        if get_markup_state() == MarkupState.DRAW:
            set_markup_state(MarkupState.READY)
            MIN_POINT_FOR_VALID_DRAWING = 3
            if len(self._points) < MIN_POINT_FOR_VALID_DRAWING or not self._name.endswith(
                self._settings.get_as_string(MARKUP_TOOL_CURRENT)
            ):
                self._drag_stack.clear()
                self._temp_stack.clear()
                self._points.clear()
                return
            self._temp_stack.clear()
            with self._drag_stack:
                ui.FreeLine(self._c1, self._c2, style=self.style, alignment=ui.Alignment.UNDEFINED)

            # Get the bounds
            if len(self._points) == 1:  # pragma: no cover
                x_min, y_min = self._points[0]
                x_max, y_max = self._points[0]
            else:
                xs, ys = zip(*self._points)
                x_min, *_, x_max = sorted(xs)
                y_min, *_, y_max = sorted(ys)

            def tweak_coordinate(x, y, min_value=0.001, max_value=0.999):
                delta = max_value - min_value
                return (min_value + x * delta, min_value + y * delta)

            # Transform points to rectangle local
            size_x = x_max - x_min
            size_y = y_max - y_min
            for i in range(len(self._points)):
                local_x = (self._points[i][0] - x_min) / size_x if size_x > 0.0 else 0.0
                local_y = (self._points[i][1] - y_min) / size_y if size_y > 0.0 else 0.0
                self._points[i] = tweak_coordinate(local_x, local_y)

            get_markup_instance().add_element(
                x_min,
                y_min,
                x_max,
                y_max,
                element_type=MARKUP_TOOL_ELEMENT_TYPE.LINE,
                element_style=self.style,
                points=self._points,
            )

            self._drag_stack.clear()
            self._temp_stack.clear()
            self._points.clear()
            self._temp_line = None
            if self._manager.tool_instance:
                self._manager.tool_instance.refresh_elements()

    @property
    def color(self) -> int:
        return cast(int, self._settings_item.get("color/abgr_color", MARKUP_TOOL_SUBTOOL_COLOR_RED))

    @property
    def border_width(self) -> int:
        return cast(int, self._settings_item.get("stroke", MARKUP_TOOL_SUBTOOL_DRAW_STROKE_M))

    @property
    def style(self):
        return {
            "FreeLine": {
                "background_color": 0x0,
                "color": self.color,
                "border_width": self.border_width,
                "border_radius": 0,
            },
            "FreeBezierCurve": {
                "background_color": 0x0,
                "color": self.color,
                "border_width": self.border_width,
                "border_radius": 0,
            },
            "Line": {
                "background_color": 0x0,
                "color": self.color,
                "border_width": self.border_width,
                "border_radius": 0,
            },
            "Circle": {
                "background_color": self.color,
                "color": self.color,
                "border_width": self.border_width,
                "border_radius": 0,
            },
            "Circle::line_control": {
                "background_color": self.color,
                "color": self.color,
                "border_width": self.border_width,
                "border_radius": 0,
            },
        }


class CommentTool:

    _manager: MarkupGestureManager
    _settings: carb.settings.ISettings
    _settings_item: "carb.dictionary.Item"
    screen: sc.Screen

    def __init__(self, manager: MarkupGestureManager):
        self._manager = manager
        self._settings = carb.settings.get_settings()
        self._settings_path = "/".join([manager.settings_path, "comment"])
        self._settings_item = self._settings.get_settings_dictionary(self._settings_path)
        if self._settings_item is None:  # pragma: no cover
            item = carb.dictionary.get_dictionary().create_item(None, "", carb.dictionary.ItemType.DICTIONARY)
            self._settings.update(self._settings_path, item, "", carb.dictionary.UpdateAction.OVERWRITE)
            self._settings_item = self._settings.get_settings_dictionary(self._settings_path)

        click_gesture = sc.ClickGesture(name="markup_comment", manager=manager, on_ended_fn=self.on_click)
        drag_gesture = sc.DragGesture(name="markup_drag_comment", manager=manager, on_began_fn=self.on_begin_drag)
        self.screen = sc.Screen(gestures=[click_gesture, drag_gesture])

    def on_click(self, sender: sc.Screen):
        if get_markup_state() == MarkupState.READY:
            x, y = cast("tuple[float, float]", sender.gesture_payload.mouse)
            if x < -1.0 or x > 1.0 or y < -1.0 or y > 1.0:
                return

            tx, ty = _convert_ndc_to_markup_canvas((x, y))

            if self._manager.tool_instance:
                element = self._manager.tool_instance.get_element_at(tx, ty)
                if element:
                    return

            viewport_window = get_active_viewport_window()
            canvas_width, canvas_height = get_canvas_size(viewport_window)

            pixel_width_percent = 16
            pixel_height_percent = 9
            pixel_height = pixel_height_percent / 100 * canvas_height

            # If mouse click is very close to the right/bottom border,
            # shift tx/ty to have enough space for transform rect
            min_pixel_width_percent = 8
            if tx + pixel_width_percent > 100:
                tx = 100 - min_pixel_width_percent
                pixel_width_percent = min_pixel_width_percent

            # Compare in pixel because there may not be enough pixel for label widget
            # when compare in percentage and screen size is small
            max_height = canvas_height - DRAG_SIZE
            min_pixel_height = max(30, pixel_height)
            ty_pixel = ty / 100 * canvas_height
            if ty_pixel + min_pixel_height > max_height:
                ty = (max_height - min_pixel_height) / canvas_height * 100
                pixel_height_percent = min_pixel_height / canvas_height * 100

            pixel_size = (canvas_width * pixel_width_percent / 100.0, canvas_height * pixel_height_percent / 100.0)

            # w, h defines the bottom right corner of transform rect
            w = tx + pixel_width_percent
            h = ty + pixel_height_percent
            _, element_path = get_markup_instance().add_element(
                tx,
                ty,
                w,
                h,
                element_type=MARKUP_TOOL_ELEMENT_TYPE.TEXT,
                element_style=self.style,
                pixel_size=pixel_size,
            )

            if self._manager.tool_instance:
                self._manager.tool_instance.refresh_elements()
                element = self._manager.tool_instance.get_element_at_path(element_path)
                if element:
                    self._manager.tool_instance.set_selected_element(element)
                    element.focus_keyboard()
                    set_markup_state(MarkupState.EDIT_COMMENT)

    def on_begin_drag(self, sender: sc.Screen):
        self.on_click(sender)

    @property
    def color(self) -> int:
        return cast(int, self._settings_item.get("color/abgr_color", MARKUP_TOOL_SUBTOOL_COLOR_RED))

    @property
    def size(self) -> int:
        return cast(int, self._settings_item.get("text", MARKUP_TOOL_SUBTOOL_COMMENT_TEXT_M))

    @property
    def style(self):
        return {
            "FreeRectangle": {
                "background_color": 0x0,
                "border_color": self.color,
                "border_width": 0,
                "border_radius": 0,
            },
            "Label": {
                "background_color": 0x0,
                "color": self.color,
                "border_width": 0,
                "border_radius": 0,
                "alignment": int(ui.Alignment.LEFT),
                "font_size": self.size,
            },
            "StringField": {
                "background_color": 0x0,
                "color": self.color,
                "secondary_color": self.color,
                "border_width": 0,
                "border_radius": 0,
                "alignment": int(ui.Alignment.LEFT),
                "font_size": self.size,
            },
            "Field": {
                "background_color": 0x0,
                "color": self.color,
                "border_width": 0,
                "border_radius": 0,
            },
            "ScrollingField": {
                "background_color": 0x0,
                "color": self.color,
                "secondary_color": self.color,
                "border_width": 0,
                "border_radius": 0,
            },
        }


class MarkupScene:
    """The window with the manupulator"""

    def __init__(self, extension):
        self.markup_gesture_manager = MarkupGestureManager(extension)
        self.tools = [
            ShapeTool(self.markup_gesture_manager),
            SelectTool(self.markup_gesture_manager),
            ArrowTool(self.markup_gesture_manager),
            LineTool(self.markup_gesture_manager),
            DrawTool(self.markup_gesture_manager),
            CommentTool(self.markup_gesture_manager),
        ]

    def destroy(self):
        self.tools.clear()
