# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from math import sqrt
from typing import List, Tuple
from weakref import ref

import carb.dictionary
import carb.settings
from omni import ui
from omni.kit.app import SettingChangeSubscription
from omni.kit.markup.core import SETTINGS_MARKUP_ACTIVE
from omni.kit.markup.core import get_instance as get_markup_instance

from ..common.settings import MARKUP_SELECTION_TOLERANCE
from ..ui.constant import SETTINGS_VIEWPORT_RECT
from .constant import MARKUP_TOOL_ELEMENT_TYPE
from .data import MarkupElement, MarkupType
from .events import MarkupEvent
from .markup_state import MarkupState, get_markup_state
from .markup_transform import Rect, TransformRect

MAP = {
    MARKUP_TOOL_ELEMENT_TYPE.LINE: ("Line", "FreeLine", "FreeBezierCurve", "Circle"),
    MARKUP_TOOL_ELEMENT_TYPE.SEGMENT: (
        "Line",
        "FreeLine",
    ),
    MARKUP_TOOL_ELEMENT_TYPE.ARROW: (
        "Line",
        "FreeLine",
    ),
    MARKUP_TOOL_ELEMENT_TYPE.TEXT: ("Label", "StringField", "Field", "Circle"),
    MARKUP_TOOL_ELEMENT_TYPE.RECTANGLE: (
        "Rectangle",
        "Circle",
        "Ellipse",
        "FreeRectangle",
        "FreeCircle",
        "FreeEllipse",
    ),
    MARKUP_TOOL_ELEMENT_TYPE.CIRCLE: ("Rectangle", "Circle", "Ellipse", "FreeRectangle", "FreeCircle", "FreeEllipse"),
}


def create_markup_render_element(prim, gesture_manager):
    element_type_to_render_class = {
        MARKUP_TOOL_ELEMENT_TYPE.ARROW: ArrowMarkupRenderElement,
        MARKUP_TOOL_ELEMENT_TYPE.SEGMENT: SegmentMarkupRenderElement,
        MARKUP_TOOL_ELEMENT_TYPE.SHAPE: ShapeMarkupRenderElement,
        MARKUP_TOOL_ELEMENT_TYPE.TEXT: TextMarkupRenderElement,
        MARKUP_TOOL_ELEMENT_TYPE.LINE: LineMarkupRenderElement,
    }
    element = MarkupElement(prim)
    return element_type_to_render_class[element.type](element, gesture_manager)


class MarkupRenderElement:
    def __init__(self, element, gesture_manager):
        self._element = element
        self._settings = carb.settings.get_settings()
        self._sub = None
        self.on_element_destroyed = MarkupEvent()
        x1, y1, x2, y2 = self._element.rect if self._element.rect else (0, 0, 0, 0)
        _rect = Rect((x1, y1), (x2, y2))
        self._transform_rect = TransformRect(_rect, show_controls=True, gesture_manager=gesture_manager)
        self._transform_rect.changed += self.on_transform_changed
        self._element.style_changed += self.on_style_changed
        self._element.element_destroyed += self.on_element_destroyed

    def draw_element(self, style=None):
        if self._sub:
            self._settings.unsubscribe_to_change_events(self._sub)
            self._sub = None
        element_style = self._element.style if style is None else style
        element_style = {**element_style, "ZStack::debug_highlight": {"debug_color": 0x30FF00FF}}
        self._transform_rect.element_stack.style = element_style
        self._transform_rect.element_stack.clear()

    def __del__(self):
        self.destroy()

    def destroy(self):
        if self._settings and self._sub:
            self._settings.unsubscribe_to_change_events(self._sub)
        self._transform_rect.destroy()
        self._transform_rect.frame.clear()
        self._sub = None

    def can_select(self, x, y, tolerance: int):
        # broad phase check
        return self.__point_inside_rectangle_border(
            x, y, self.rect.min_x, self.rect.min_y, self.rect.max_x, self.rect.max_y, tolerance
        )

    def __point_inside_rectangle_border(
        self, x: float, y: float, min_x: float, min_y: float, max_x: float, max_y: float, tolerance: float
    ) -> bool:
        padded_min = (min_x - tolerance, min_y - tolerance)
        padded_max = (max_x + tolerance, max_y + tolerance)
        return padded_min[0] <= x <= padded_max[0] and padded_min[1] <= y <= padded_max[1]

    @staticmethod
    def point_close_to_seg(x: float, y: float, x1: float, y1: float, x2: float, y2: float, tolerance: float) -> bool:
        return MarkupRenderElement.__square_distance_point_to_segment(x, y, x1, y1, x2, y2) < tolerance**2

    @staticmethod
    def __square_distance_point_to_segment(x, y, x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:  # pragma: no cover
            # The segment is just a point; calculate the distance to that point.
            return (x - x1) ** 2 + (y - y1) ** 2

        t = ((x - x1) * dx + (y - y1) * dy) / (dx**2 + dy**2)

        if t <= 0:  # pragma: no cover
            # Closest point is x1, y1
            return (x - x1) ** 2 + (y - y1) ** 2
        elif t >= 1:  # pragma: no cover
            # Closest point is x2, y2
            return (x - x2) ** 2 + (y - y2) ** 2
        else:
            # Closest point is along the segment
            closest_x = x1 + t * dx
            closest_y = y1 + t * dy
            return (x - closest_x) ** 2 + (y - closest_y) ** 2

    @property
    def selected(self):  # pragma: no cover
        return self._transform_rect.visible

    @selected.setter
    def selected(self, value: bool):
        self._transform_rect.active = value
        self._transform_rect.visible = value

    @property
    def prim_path(self):
        return self._element.path

    @property
    def prim(self):
        return self._element.prim

    @property
    def name(self):  # pragma: no cover
        return self._element.style_name

    @property
    def rect(self):
        return self._transform_rect.rect

    @property
    def type(self):
        return self._element.prim_type

    def update_style(self, **kwargs):
        self._element.update_style(None, **kwargs)

    def on_style_changed(self, style):
        self.draw_element(style)

    def on_transform_changed(self, rect: Rect):
        self._element.update_rect(rect.flat)

    def remove_element(self):
        self._element.destroy()


class ArrowMarkupRenderElement(MarkupRenderElement):
    def __init__(self, element, gesture_manager):
        super().__init__(element, gesture_manager)

    def draw_element(self, style=None):
        super().draw_element(style)

        with self._transform_rect.element_stack:
            with ui.ZStack():
                arrow = ui.FreeLine(
                    self._transform_rect.controls["cp1"],
                    self._transform_rect.controls["cp4"],
                    alignment=ui.Alignment.UNDEFINED,
                    style_type_name_override=self._element.style_name,
                )
                arrow_direction = self._element.direction
                arrow_size = self._element.stroke * 3
                arrow.begin_arrow_height = arrow_size
                arrow.begin_arrow_width = arrow_size
                arrow.end_arrow_height = arrow_size
                arrow.end_arrow_width = arrow_size
                if arrow_direction == 0:
                    arrow.begin_arrow_type = ui.ArrowType.ARROW
                    arrow.end_arrow_type = ui.ArrowType.NONE
                elif arrow_direction == 1:
                    arrow.begin_arrow_type = ui.ArrowType.NONE
                    arrow.end_arrow_type = ui.ArrowType.ARROW
                else:
                    arrow.begin_arrow_type = ui.ArrowType.ARROW
                    arrow.end_arrow_type = ui.ArrowType.ARROW

    def can_select(self, x, y, tolerance: int):
        if super().can_select(x, y, tolerance):
            return MarkupRenderElement.point_close_to_seg(
                x,
                y,
                float(self._transform_rect.placers["cp1"].offset_x),
                float(self._transform_rect.placers["cp1"].offset_y),
                float(self._transform_rect.placers["cp4"].offset_x),
                float(self._transform_rect.placers["cp4"].offset_y),
                tolerance,
            )
        else:  # pragma: no cover
            return False


class SegmentMarkupRenderElement(MarkupRenderElement):
    def __init__(self, element, gesture_manager):
        super().__init__(element, gesture_manager)

    def draw_element(self, style=None):
        super().draw_element(style)

        with self._transform_rect.element_stack:
            with ui.ZStack():
                ui.FreeLine(
                    self._transform_rect.controls["cp1"],
                    self._transform_rect.controls["cp4"],
                    alignment=ui.Alignment.UNDEFINED,
                    style_type_name_override=self._element.style_name,
                )

    def can_select(self, x, y, tolerance: int):
        if super().can_select(x, y, tolerance):
            return MarkupRenderElement.point_close_to_seg(
                x,
                y,
                float(self._transform_rect.placers["cp1"].offset_x),
                float(self._transform_rect.placers["cp1"].offset_y),
                float(self._transform_rect.placers["cp4"].offset_x),
                float(self._transform_rect.placers["cp4"].offset_y),
                tolerance,
            )
        return False


class ShapeMarkupRenderElement(MarkupRenderElement):
    def __init__(self, element, gesture_manager):
        super().__init__(element, gesture_manager)

    def draw_element(self, style=None):
        super().draw_element(style)

        with self._transform_rect.element_stack:
            with ui.ZStack():
                if self._element.shape_type == MarkupType.RECTANGLE:
                    ui.FreeRectangle(
                        self._transform_rect.controls["cp1"],
                        self._transform_rect.controls["cp4"],
                        alignment=ui.Alignment.UNDEFINED,
                        style_type_name_override=self._element.style_name,
                    )
                elif self._element.shape_type == MarkupType.CIRCLE:
                    ui.FreeEllipse(
                        self._transform_rect.controls["cp1"],
                        self._transform_rect.controls["cp4"],
                        alignment=ui.Alignment.UNDEFINED,
                        style_type_name_override=self._element.style_name,
                    )

    def can_select(self, x, y, tolerance: int):
        if super().can_select(x, y, tolerance):
            if self._element.shape_type == MarkupType.RECTANGLE:
                return ShapeMarkupRenderElement.__point_close_to_rectangle_border(
                    x, y, self.rect.min_x, self.rect.min_y, self.rect.max_x, self.rect.max_y, tolerance
                )
            elif self._element.shape_type == MarkupType.CIRCLE:
                return ShapeMarkupRenderElement.__point_close_to_circle_border(
                    x, y, self.rect.min_x, self.rect.min_y, self.rect.max_x, self.rect.max_y, tolerance
                )
        return False

    @staticmethod
    def __point_close_to_rectangle_border(
        x: float, y: float, min_x: float, min_y: float, max_x: float, max_y: float, tolerance: float
    ) -> bool:
        return (
            MarkupRenderElement.point_close_to_seg(x, y, min_x, min_y, min_x, max_y, tolerance)
            or MarkupRenderElement.point_close_to_seg(x, y, min_x, min_y, max_x, min_y, tolerance)
            or MarkupRenderElement.point_close_to_seg(x, y, max_x, max_y, max_x, min_y, tolerance)
            or MarkupRenderElement.point_close_to_seg(x, y, max_x, max_y, min_x, max_y, tolerance)
        )

    @staticmethod
    def __point_close_to_circle_border(
        x: float, y: float, min_x: float, min_y: float, max_x: float, max_y: float, tolerance: float
    ) -> bool:
        # find the closest point on the squashed circle given the aabb
        radius = ((max_x - min_x) / 2.0, (max_y - min_y) / 2.0)
        if radius[0] > 0.0 and radius[1] > 0.0:
            center = ((max_x + min_x) / 2.0, (max_y + min_y) / 2.0)
            normalized_hit = ((x - center[0]) / radius[0], (y - center[1]) / radius[1])
            normalized_length = sqrt(normalized_hit[0] * normalized_hit[0] + normalized_hit[1] * normalized_hit[1])
            closest_normalized_point = (normalized_hit[0] / normalized_length, normalized_hit[1] / normalized_length)
            closest_point = (
                closest_normalized_point[0] * radius[0] + center[0],
                closest_normalized_point[1] * radius[1] + center[1],
            )

            to_circle = (x - closest_point[0], y - closest_point[1])
            squared_world_distance = to_circle[0] * to_circle[0] + to_circle[1] + to_circle[1]
            return squared_world_distance < tolerance**2
        else:  # pragma: no cover
            return False


class TextMarkupRenderElement(MarkupRenderElement):
    def __init__(self, element, gesture_manager):
        super().__init__(element, gesture_manager)
        self._edit_field: "ui.AbstractField|None" = None
        self._edit_field_stack: "ui.ZStack|None" = None
        self._focused = False

    def focus_keyboard(self, focus=True):
        self._focused = focus
        if self._edit_field:
            self._edit_field.focus_keyboard(focus)

    def draw_element(self, style=None):
        super().draw_element(style)

        self._sub = self._settings.subscribe_to_node_change_events(SETTINGS_VIEWPORT_RECT, self.__refresh_edit_field)
        self._transform_rect.element_stack.set_computed_content_size_changed_fn(self.__refresh_edit_field)
        self.__refresh_edit_field()

    @MarkupRenderElement.selected.setter
    def selected(self, value: bool):
        self._transform_rect.active = value
        self._transform_rect.visible = value
        self.focus_keyboard(value)
        if self._edit_field:
            self._edit_field.enabled = value
            if value:
                self._edit_field.focus_keyboard()

    def on_transform_changed(self, rect: Rect):
        super().on_transform_changed(rect)
        self.__refresh_edit_field()

    def __refresh_edit_field(self, *_):
        viewport_rect = self._settings.get(SETTINGS_VIEWPORT_RECT)
        if viewport_rect is not None:
            edit_field_enabled = False
            if self._edit_field:
                edit_field_enabled = self._edit_field.enabled
                self._edit_field.name = "INVALID_text_input_field"
                self._edit_field.destroy()
                self._edit_field = None
            if self._edit_field_stack:
                self._edit_field_stack.clear()
                self._edit_field_stack.destroy()
                self._edit_field_stack = None
            viewport_size = (viewport_rect[2] - viewport_rect[0], viewport_rect[3] - viewport_rect[1])
            rect_min = (self.rect.min_x / 100.0, self.rect.min_y / 100.0)
            pixel_size_max = (
                (1.0 - rect_min[0]) * viewport_size[0] - 2,
                (1.0 - rect_min[1]) * viewport_size[1] - 2,
            )
            pixel_size_original = self._element.pixel_size
            if pixel_size_original is not None:
                with self._transform_rect.element_stack:
                    self._edit_field_stack = ui.ZStack()
                    with self._edit_field_stack:
                        self._edit_field = ui.StringField(
                            self._element.text_model,
                            style_type_name_override=self._element.style_name,
                            multiline=True,
                            identifier="text_input_field",
                            width=ui.Pixel(min(pixel_size_original[0], pixel_size_max[0])),
                            height=ui.Pixel(min(pixel_size_original[1], pixel_size_max[1])),
                        )
                        self._edit_field.enabled = edit_field_enabled
                        if get_markup_state() != MarkupState.COLOR_PICKER:
                            self._edit_field.focus_keyboard(self._focused)
                self._transform_rect.frame.horizontal_clipping = 0
                self._transform_rect.frame.vertical_clipping = 0


class LineMarkupRenderElement(MarkupRenderElement):
    def __init__(self, element, gesture_manager):
        super().__init__(element, gesture_manager)

    def draw_element(self, style=None):
        super().draw_element(style)

        with self._transform_rect.element_stack:
            with ui.ZStack():
                x, y = self._element.points[0]
                size = self._element.stroke
                with ui.Placer(offset_x=ui.Percent(x * 100.0), offset_y=ui.Percent(y * 100.0), stable_size=True):
                    with ui.ZStack():
                        c1 = ui.Circle(
                            height=size,
                            width=size,
                            style_type_name_override=self._element.style_name,
                        )
                for x, y in self._element.points[1:]:
                    with ui.Placer(offset_x=ui.Percent(x * 100.0), offset_y=ui.Percent(y * 100.0), stable_size=True):
                        with ui.ZStack():
                            c2 = ui.Circle(
                                height=size,
                                width=size,
                                style_type_name_override=self._element.style_name,
                            )
                    ui.FreeLine(
                        c1,
                        c2,
                        alignment=ui.Alignment.UNDEFINED,
                        style_type_name_override=self._element.style_name,
                    )
                    c1 = c2

    def can_select(self, x, y, tolerance: int):
        if super().can_select(x, y, tolerance):
            return LineMarkupRenderElement.__point_close_to_piecewise_linear_curve(
                x,
                y,
                self.rect.min_x,
                self.rect.min_y,
                self.rect.max_x,
                self.rect.max_y,
                self._element.points,
                tolerance,
            )
        return False

    @staticmethod
    def __point_close_to_piecewise_linear_curve(
        x: float,
        y: float,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        points: List[Tuple[float, float]],
        tolerance: float,
    ) -> bool:
        if len(points) < 2:  # pragma: no cover
            return False

        # Transform points from bounds local to viewport space
        x1 = points[0][0] * (max_x - min_x) + min_x
        y1 = points[0][1] * (max_y - min_y) + min_y
        for point in points[1:]:
            x2 = point[0] * (max_x - min_x) + min_x
            y2 = point[1] * (max_y - min_y) + min_y
            if MarkupRenderElement.point_close_to_seg(x, y, x1, y1, x2, y2, tolerance):
                return True
            x1 = x2
            y1 = y2
        else:  # pragma: no cover
            return False


class MarkupRenderer:
    def __init__(self, tool_instance):
        self._elements = {}
        self._frame_stack = None
        self._settings = carb.settings.get_settings()
        self._markup_stack = tool_instance.get_markup_stack()
        self.element_destroyed = MarkupEvent()
        with self._markup_stack:
            self._frame = ui.Frame()
        self._gesture_manager = tool_instance.get_gesture_manager()
        self._tool_instance = tool_instance

        # we need an ordered list of the elements in draw order: last is on top
        self._ordered_elements = []

        def on_changed(*x, _self=ref(self)):
            self = _self()
            if self:
                self._on_active_markup_changed(*x)

        self._sub = SettingChangeSubscription(SETTINGS_MARKUP_ACTIVE, on_changed)

    def _on_active_markup_changed(self, item: carb.dictionary.Item, change_type: carb.settings.ChangeEventType):
        if item.get_dict():
            self.refresh_elements()
        else:
            self._frame.clear()
            self._frame_stack = None
            for element in self._elements.values():
                element.destroy()
            self._elements = {}
            self._ordered_elements.clear()

    def refresh_elements(self, refresh_all_elements=False, selected_element=None):

        # If an element is selected, we need it to be drawn last so that it draws over all the other markup elements.
        # To accomplish this, we force a full refresh and defer the selected element initialization until
        # after all other elements are created.

        if refresh_all_elements or selected_element:
            # NOTE: to avoid stale elements on undo/redo, we're just going to destroy all of them
            # and clear our frame in order to force recreation of everything here.
            self._frame.clear()
            self._frame_stack = None
            for element in self._elements.values():
                element.destroy()
            self._elements = {}
            self._ordered_elements.clear()

        inst = get_markup_instance()
        if inst and inst.current_markup:
            prims_to_draw = []
            remove_prim_paths = []
            valid_prim_paths = {}
            if self._frame_stack is None:
                with self._frame:
                    self._frame_stack = ui.ZStack(height=ui.Percent(100), width=ui.Percent(100))

            last_element_to_draw = None
            with self._frame_stack:
                for markup_element in inst.get_markup_elements():
                    prim_path = markup_element.GetPath().pathString
                    valid_prim_paths[prim_path] = True

                    if selected_element:
                        if str(selected_element.prim_path) == prim_path:
                            last_element_to_draw = markup_element
                            continue

                    if prim_path not in self._elements:
                        self._elements[prim_path] = create_markup_render_element(markup_element, self._gesture_manager)
                        prims_to_draw.append(prim_path)
                        self._ordered_elements.append(prim_path)

                if last_element_to_draw:
                    self._elements[str(selected_element.prim_path)] = create_markup_render_element(
                        last_element_to_draw, self._gesture_manager
                    )
                    prims_to_draw.append(str(selected_element.prim_path))
                    self._ordered_elements.append(str(selected_element.prim_path))

            for prim_path in self._elements:
                if prim_path not in valid_prim_paths:
                    remove_prim_paths.append(prim_path)
            for prim_path in remove_prim_paths:
                self._elements[prim_path].destroy()
                self._elements[prim_path] = None
                del self._elements[prim_path]
            for prim_path in prims_to_draw:
                try:
                    element = self._elements[prim_path]
                    element.draw_element()
                    element.selected = False
                    element.on_element_destroyed += self.on_element_destroyed
                except KeyError:  # pragma: no cover
                    continue

            if selected_element and len(self._ordered_elements):
                self._tool_instance.set_selected_element(self._elements[str(selected_element.prim_path)])

    def get_element_at_path(self, element_path):
        return self._elements.get(element_path, None)

    def get_element_at(self, x, y, *, element_type: str = "") -> "MarkupRenderElement|None":
        tolerance = self._settings.get_as_float(MARKUP_SELECTION_TOLERANCE)
        for prim_path in reversed(self._ordered_elements):
            try:
                element = self._elements[prim_path]
                if element.can_select(x, y, tolerance):
                    if element_type:
                        if element_type == element.type:  # pragma: no cover
                            return element
                        else:  # pragma: no cover
                            continue
                    return element
            except KeyError:
                continue

    def on_selection_changed(self, element: "MarkupRenderElement|None"):
        for prim_path in self._elements:
            elm = self._elements[prim_path]
            elm.selected = elm == element

    def on_element_destroyed(self, element):
        self.element_destroyed(element)
