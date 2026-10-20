# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import dataclasses
from enum import IntEnum
from typing import Tuple

from omni import ui
from omni.kit.async_engine import run_coroutine

from .events import MarkupEvent
from .markup_state import MarkupState, get_markup_state, return_to_previous_state, set_markup_state


class MouseKey(IntEnum):
    NONE = -1
    LEFT = 0
    RIGHT = 1
    MIDDLE = 2


HANDLE_SIZE = 8
DRAG_SIZE = HANDLE_SIZE * 1.5


@dataclasses.dataclass
class Rect:

    point_0: Tuple[float, float]
    point_1: Tuple[float, float]

    @property
    def min_x(self) -> float:
        return min(self.point_0[0], self.point_1[0])

    @property
    def min_y(self) -> float:
        return min(self.point_0[1], self.point_1[1])

    @property
    def max_x(self) -> float:
        return max(self.point_0[0], self.point_1[0])

    @property
    def max_y(self) -> float:
        return max(self.point_0[1], self.point_1[1])

    @property
    def mid_x(self) -> float:
        return (self.min_x + self.max_x) / 2

    @property
    def mid_y(self) -> float:
        return (self.min_y + self.max_y) / 2

    @property
    def flat(self) -> Tuple[float, float, float, float]:
        return self.point_0 + self.point_1


class TransformRect:
    frame: ui.Frame
    element_stack: ui.ZStack
    controls: "dict[str, ui.Shape]"
    _stack: ui.ZStack
    _rect: Rect
    _frame_placer: ui.Placer
    _drag_placer: ui.Placer
    _drag_frame: ui.Frame
    _drag_box: ui.Rectangle
    _cp1: ui.Placer
    _cp2: ui.Placer
    _cp3: ui.Placer
    _cp4: ui.Placer
    _mp1: ui.Placer
    _mp2: ui.Placer
    _mp3: ui.Placer
    _mp4: ui.Placer
    _placers: "tuple[ui.Placer, ...]"
    _show_controls: bool
    active: bool

    # Everything in here is % driven, it makes the code messy.
    def __init__(self, rect: Rect = Rect((10, 10), (30, 30)), *, show_controls=True, gesture_manager=None):
        self._rect = rect
        self._pressed = []
        self._moved = []
        self._released = []
        self._stack = ui.ZStack()
        self._stack.set_mouse_pressed_fn(self.on_pressed)
        self._stack.set_mouse_moved_fn(self.on_moved)
        self._stack.set_mouse_released_fn(self.on_released)

        self.controls: "dict[str, ui.Shape]" = {}
        self.placers: "dict[str, ui.Placer]" = {}
        self._show_controls = show_controls
        self.__update_control_points = True
        self._stack.set_computed_content_size_changed_fn(self.update_shapes)
        self.changed = MarkupEvent()
        self.changed_continuous = MarkupEvent()
        self._pressed_in_edit = False

        self._gesture_manager = gesture_manager
        self._hovered_gesture_controls = set()
        self._gesture_drag_blocked = False

        self.active = False

        self._build_ui()

    def _set_gesture_control_hovered(self, control_name: str, hovered: bool) -> None:
        if not self._gesture_manager:
            return

        if hovered and self.active and control_name not in self._hovered_gesture_controls:
            self._hovered_gesture_controls.add(control_name)
            self._gesture_manager.acquire_gesture_block()
        elif not hovered and control_name in self._hovered_gesture_controls:
            self._hovered_gesture_controls.remove(control_name)
            self._gesture_manager.release_gesture_block()

    def _set_gesture_drag_blocked(self, blocked: bool) -> None:
        if not self._gesture_manager or blocked == self._gesture_drag_blocked or (blocked and not self.active):
            return

        self._gesture_drag_blocked = blocked
        if blocked:
            self._gesture_manager.acquire_gesture_block()
        else:
            self._gesture_manager.release_gesture_block()

    def _clear_gesture_blocks(self) -> None:
        if not self._gesture_manager:
            return

        for _ in self._hovered_gesture_controls:
            self._gesture_manager.release_gesture_block()
        self._hovered_gesture_controls.clear()
        self._set_gesture_drag_blocked(False)

    def destroy(self) -> None:
        self._clear_gesture_blocks()

    def _build_ui(self):

        def on_pressed_in_edit_area(x, y, m, *_):
            # Only care about left mouse
            if m != MouseKey.LEFT:  # pragma: no cover
                return
            self._pressed_in_edit = True

        def on_released_in_edit_area(x, y, m, *_):
            # Only care about left mouse
            if m != MouseKey.LEFT:  # pragma: no cover
                return
            self._pressed_in_edit = False

        with self._stack:
            self._frame_placer = ui.Placer(
                offset_x=ui.Percent(self._rect.min_x),
                offset_y=ui.Percent(self._rect.min_y),
            )
            with self._frame_placer:
                self.frame = ui.Frame(
                    width=ui.Percent(self._rect.max_x - self._rect.min_x),
                    height=ui.Percent(self._rect.max_y - self._rect.min_y),
                    content_clipping=1,
                )
                with self.frame:
                    with ui.ZStack():
                        self._edit_area = ui.Rectangle(style={"background_color": 0x00000000})
                        self._edit_area.set_mouse_pressed_fn(on_pressed_in_edit_area)
                        self._edit_area.set_mouse_released_fn(on_released_in_edit_area)
                        self.element_stack = ui.ZStack()

            self._toolbar_placer = ui.Placer(
                offset_x=ui.Percent(self._rect.min_x),
                offset_y=ui.Percent(self._rect.max_y + 1),
            )
            with self._toolbar_placer:
                self.toolbar = ui.Frame(
                    width=0,
                    height=0,
                    # separate_window=1,
                )
                with self.toolbar:
                    ui.Rectangle(style={"debug_color": 0x88FFFFFF})

            control_stack = ui.ZStack(
                style={
                    ":checked": {
                        "background_color": 0x0,
                        "border_color": 0x0 if self._show_controls else 0x0,
                        "border_width": 1,
                    },
                    "background_color": 0xFFDDDDDD if self._show_controls else 0x0,
                    "border_color": 0xFF222222 if self._show_controls else 0x0,
                    "border_width": 1,
                    "corner_flag": ui.CornerFlag.ALL,
                    "border_radius": 20,
                },
                identifier="transform_control_stack",
            )
            with control_stack:
                self._drag_placer = ui.Placer(
                    name="drag", offset_x=self._frame_placer.offset_x, offset_y=self._frame_placer.offset_y
                )
                with self._drag_placer:
                    self._drag_frame = ui.Frame(
                        width=ui.Percent(self._rect.max_x - self._rect.min_x),
                        height=ui.Pixel(HANDLE_SIZE * 1.5),
                        style={"debug_color": 0},
                    )
                    with self._drag_frame:
                        self._build_drag_box()

                self._cp1 = ui.Placer(
                    name="cp1",
                )
                self._cp2 = ui.Placer(
                    name="cp2",
                )
                self._cp3 = ui.Placer(
                    name="cp3",
                )
                self._cp4 = ui.Placer(
                    name="cp4",
                )
                self._mp1 = ui.Placer(
                    name="mp1",
                    drag_axis=ui.Axis.X,
                )
                self._mp2 = ui.Placer(
                    name="mp2",
                    drag_axis=ui.Axis.X,
                )
                self._mp3 = ui.Placer(
                    name="mp3",
                    drag_axis=ui.Axis.Y,
                )
                self._mp4 = ui.Placer(
                    name="mp4",
                    drag_axis=ui.Axis.Y,
                )
                self._placers = (
                    self._cp1,
                    self._cp2,
                    self._cp3,
                    self._cp4,
                    self._mp1,
                    self._mp2,
                    self._mp3,
                    self._mp4,
                )
                for pl in self._placers:
                    pl.identifier = "transform_placer_" + pl.name

                    # Ensure the placer's can't go out of bounds
                    def on_x(x: ui.Length, p=pl):
                        drag_percent = (
                            (DRAG_SIZE / self._stack.computed_width * 100) if self._stack.computed_width else 3
                        )
                        p.offset_x = ui.Percent(max(0, min(float(x), 100 - drag_percent)))

                    def on_y(y: ui.Length, p=pl):
                        drag_percent = (
                            (DRAG_SIZE / self._stack.computed_height * 100) if self._stack.computed_height else 3
                        )
                        p.offset_y = ui.Percent(max(0, min(float(y), 100 - drag_percent)))

                    pl.set_offset_x_changed_fn(on_x)
                    pl.set_offset_y_changed_fn(on_y)

                    with pl:
                        with ui.ZStack(height=DRAG_SIZE, width=DRAG_SIZE):
                            ctrl = ui.Frame(height=1, width=1)
                            with ui.Placer(offset_x=ui.Pixel(-DRAG_SIZE / 2.0), offset_y=ui.Pixel(-DRAG_SIZE / 2.0)):
                                ctrl_frame = ui.Frame(height=DRAG_SIZE, width=DRAG_SIZE)
                                with ctrl_frame:
                                    ui.Circle(
                                        alignment=ui.Alignment.CENTER,
                                        radius=HANDLE_SIZE / 2.0,
                                        size_policy=ui.CircleSizePolicy.FIXED,
                                    )
                        self.controls[pl.name] = ctrl
                        self.placers[pl.name] = pl

                    def on_pressed(x: float, y: float, m: int, *_, p: ui.Placer = pl):
                        # Only care about left mouse
                        if m != MouseKey.LEFT:  # pragma: no cover
                            return
                        self._pressed.append(p)
                        self._set_gesture_drag_blocked(True)

                    def on_released(x: float, y: float, m: int, *_, p=pl):
                        # Only care about left mouse
                        if m != MouseKey.LEFT:  # pragma: no cover
                            return
                        self._released.append(p)
                        p.selected = False
                        self._set_gesture_drag_blocked(False)

                    def on_moved(x: float, y: float, *_, p=pl):
                        if not p.selected or not p.enabled or p.checked:
                            return

                        # These mouse callbacks give us coordinates based on the whole application window
                        # We want them in the local screen space, so offseting by the parent stack.
                        pos_x = ui.Percent((x - self._stack.screen_position_x) / self._stack.computed_width * 100)
                        pos_y = ui.Percent((y - self._stack.screen_position_y) / self._stack.computed_height * 100)
                        # This mess is basically making sure that aligned controls update in sync with each other.
                        # We don't really care about the overall orientation of the rectangle, instead we just track
                        # the various edges. (cp is corner-placer, mp is midpoint-placer)
                        if any((self._cp1.selected, self._cp2.selected, self._mp1.selected)):
                            self._cp1.offset_x = self._cp2.offset_x = self._mp1.offset_x = pos_x
                        elif any((self._cp3.selected, self._cp4.selected, self._mp2.selected)):
                            self._cp3.offset_x = self._cp4.offset_x = self._mp2.offset_x = pos_x
                        self._mp3.offset_x = self._mp4.offset_x = ui.Percent(
                            (float(self._cp1.offset_x) + self._cp3.offset_x) / 2
                        )

                        if any((self._cp1.selected, self._cp3.selected, self._mp3.selected)):
                            self._cp1.offset_y = self._cp3.offset_y = self._mp3.offset_y = pos_y
                        elif any((self._cp2.selected, self._cp4.selected, self._mp4.selected)):
                            self._cp2.offset_y = self._cp4.offset_y = self._mp4.offset_y = pos_y
                        self._mp1.offset_y = self._mp2.offset_y = ui.Percent(
                            (float(self._cp1.offset_y) + self._cp2.offset_y) / 2
                        )

                        self.update_shapes()

                    def on_hovered(hov: bool, p: ui.Placer = pl):
                        self._set_gesture_control_hovered(p.name, hov)
                        self.toolbar.enabled = not (hov or any(pl.selected for pl in self._placers))

                    ctrl_frame.set_mouse_pressed_fn(on_pressed)
                    ctrl_frame.set_mouse_released_fn(on_released)
                    ctrl_frame.set_mouse_moved_fn(on_moved)
                    ctrl_frame.set_mouse_hovered_fn(on_hovered)

    def _build_drag_box(self):
        def on_drag_moved(x, y, *_):
            # Don't try to move the drag control _and_ any of the handles
            # this can kind of happen if you bunch the controls up real small.
            if (
                any(placer.selected for placer in self._placers)
                or not self._drag_placer.selected
                or self._drag_placer.checked
            ):  # pragma: no cover
                return
            nonlocal dx, dy

            cx = (x - dx) / self._stack.computed_width * 100
            cy = (y - dy) / self._stack.computed_height * 100
            x_drag_percent = (DRAG_SIZE / self._stack.computed_width * 100) if self._stack.computed_width else 3
            y_drag_percent = (DRAG_SIZE / self._stack.computed_height * 100) if self._stack.computed_height else 3
            # We only want to update the placer positions,
            # if we're not bashing into one of the sides,
            # basically translation only, no scaling
            max_x = 100 - x_drag_percent
            max_y = 100 - y_drag_percent
            if all(0 <= placer.offset_x + cx <= max_x for placer in self._placers) and all(
                0 <= placer.offset_y + cy <= max_y for placer in self._placers
            ):
                for placer in self._placers:
                    placer.offset_x = ui.Percent(placer.offset_x + cx)
                    placer.offset_y = ui.Percent(placer.offset_y + cy)

            dx, dy = x, y
            self.update_shapes()

        def on_drag_pressed(x, y, m, *_):
            # Only care about left mouse
            if m != MouseKey.LEFT:  # pragma: no cover
                return
            # When moving the drag handle, we work in deltas so we know how much to apply
            # to each of the individual controls.
            # Not really perfect, but I don't think much of anything will be here.
            nonlocal dx, dy
            dx, dy = x, y
            self._drag_placer.selected = True
            self._set_gesture_drag_blocked(True)

        def on_drag_released(x, y, m, *_):
            # Only care about left mouse
            if m != MouseKey.LEFT:  # pragma: no cover
                return
            self._drag_placer.selected = False
            self._released.append(self._drag_placer)
            self._set_gesture_drag_blocked(False)

        dx, dy = 0, 0

        with ui.HStack():
            ui.Spacer()
            self._drag_box = ui.Rectangle(
                width=3 * HANDLE_SIZE, height=1.5 * HANDLE_SIZE, identifier="transform_drag_box"
            )
            ui.Spacer()

        self._drag_box.set_mouse_pressed_fn(on_drag_pressed)
        self._drag_box.set_mouse_released_fn(on_drag_released)
        self._drag_box.set_mouse_moved_fn(on_drag_moved)
        self._drag_box.set_mouse_hovered_fn(
            lambda hovered: self._set_gesture_control_hovered(self._drag_placer.name, hovered)
        )

    def on_startup(self):  # pragma: no cover
        self.update_shapes()
        self._stack.set_computed_content_size_changed_fn(None)  # type: ignore
        if not self._show_controls:
            for placer in self._placers:
                placer.enabled = False
            self._drag_placer.enabled = False

    def on_pressed(self, *_) -> None:
        run_coroutine(self.process_pressed())

    async def process_pressed(self):
        # If we've hit multiple controls, we want to get the top-most corner, otherwise the drag experience is bad.
        # reversed gets us the clicked controls in front-to-back order, if there are no corner controls being clicked
        # then we just need the front most

        # We don't need to process these gestures if the TransformRect isn't active
        if not self.active:
            self._pressed[:] = []
            return

        if get_markup_state() in (MarkupState.EDIT, MarkupState.EDIT_COMMENT):
            exit_edit = len(self._pressed) == 0 and not self._drag_placer.selected
            if get_markup_state() == MarkupState.EDIT_COMMENT:
                exit_edit = exit_edit and not self._pressed_in_edit

            if exit_edit:
                set_markup_state(MarkupState.READY)
            else:
                found = False
                for pressed in reversed(self._pressed):
                    if pressed.name.startswith("cp"):
                        pressed.selected = True
                        found = True
                        break

                if not found and self._pressed:
                    self._pressed[-1].selected = True

        elif get_markup_state() == MarkupState.STYLE_CHANGE:
            # Done transitioning, we can return to Edit. Without this we get stuck in STYLE_CHANGE
            # mode after pressing the element edit toolbar buttons, which makes it impossible to
            # interact with the elements in the viewport.
            return_to_previous_state()

        self._pressed[:] = []

    def on_moved(self, *_):
        run_coroutine(self.process_moved())

    async def process_moved(self):
        self._moved[:] = []

    def on_released(self, x, y, m, k):
        # Only care about left mouse
        if m != MouseKey.LEFT:  # pragma: no cover
            return
        self._set_gesture_drag_blocked(False)
        run_coroutine(self.process_released())

    async def process_released(self):
        if self._released:
            self.changed(self._rect)
        self._released[:] = []

    def update_shapes(self, **kwargs):
        if self.__update_control_points:
            self.__update_control_points = False
            self._cp1.offset_x = ui.Percent(self._rect.point_0[0])
            self._cp1.offset_y = ui.Percent(self._rect.point_0[1])
            self._cp2.offset_x = ui.Percent(self._rect.point_0[0])
            self._cp2.offset_y = ui.Percent(self._rect.point_1[1])
            self._cp3.offset_x = ui.Percent(self._rect.point_1[0])
            self._cp3.offset_y = ui.Percent(self._rect.point_0[1])
            self._cp4.offset_x = ui.Percent(self._rect.point_1[0])
            self._cp4.offset_y = ui.Percent(self._rect.point_1[1])
            self._mp1.offset_x = ui.Percent(self._rect.point_0[0])
            self._mp1.offset_y = ui.Percent(self._rect.mid_y)
            self._mp2.offset_x = ui.Percent(self._rect.point_1[0])
            self._mp2.offset_y = ui.Percent(self._rect.mid_y)
            self._mp3.offset_x = ui.Percent(self._rect.mid_x)
            self._mp3.offset_y = ui.Percent(self._rect.point_0[1])
            self._mp4.offset_x = ui.Percent(self._rect.mid_x)
            self._mp4.offset_y = ui.Percent(self._rect.point_1[1])
        # This does a few things, first it ensure that the element's frame is aligned with the various controls
        # Then it make sure the drag-all "Hat" is centered above the control rectangle
        # It also ensures that the toolbar won't push off the edge of the screen
        drag_handle_percent = (3 * HANDLE_SIZE) / self._stack.computed_height * 100
        handle_height = HANDLE_SIZE / self._stack.computed_height * 100

        min_x, *_, max_x = sorted(float(pl.offset_x) for pl in self._placers)
        min_y, *_, max_y = sorted(float(pl.offset_y) for pl in self._placers)
        self._rect.point_0 = float(self._cp1.offset_x), float(self._cp1.offset_y)
        self._rect.point_1 = float(self._cp4.offset_x), float(self._cp4.offset_y)

        self._frame_placer.offset_x = ui.Percent(min_x)
        self._frame_placer.offset_y = ui.Percent(min_y)
        self.frame.width = ui.Percent(max_x - min_x)
        self.frame.height = ui.Percent(max_y - min_y)

        self._drag_placer.offset_x = self._frame_placer.offset_x
        self._drag_placer.offset_y = ui.Percent(max(0, min(float(min_y) - drag_handle_percent, 100 - handle_height)))
        self._drag_frame.width = self.frame.width
        self._drag_frame.height = ui.Pixel(HANDLE_SIZE * 1.5)

        toolbar_width = self.toolbar.computed_width / self._stack.computed_width * 100
        toolbar_height = self.toolbar.computed_height / self._stack.computed_height * 100
        self._toolbar_placer.offset_x = ui.Percent(max(0, min(float(min_x), 99 - toolbar_width)))
        self._toolbar_placer.offset_y = ui.Percent(
            max(0, min(float(min_y + self.frame.height + handle_height), 99 - toolbar_height))
        )
        self.changed_continuous(self._rect)

    @property
    def visible(self) -> bool:  # pragma: no cover
        return all(p.checked for p in self._placers) and self._drag_placer.checked

    @visible.setter
    def visible(self, value: bool):
        def _walk(w):
            for c in ui.Inspector.get_children(w):
                yield from _walk(c)
            yield w

        for p in self._placers:
            p.checked = not value
            for child in _walk(p):
                child.checked = not value

        self._drag_placer.checked = not value
        for c in _walk(self._drag_placer):
            c.checked = not value

        if not value:
            self._clear_gesture_blocks()

    @property
    def rect(self):
        return self._rect
