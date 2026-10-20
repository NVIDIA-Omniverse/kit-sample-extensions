# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, List, Optional, Set, Union

import carb.settings
from omni import ui

from ..common import MeasureCreationState, MeasureMode, MeasureState, SnapMode, UserSettings
from ..manager import StateMachine
from .style import *


class ResetButton(ui.Widget):
    """
    The ResetButton class provides access to resetting a value or values when changed.
    """

    def __init__(
        self,
        default_val: Any,
        changed_fn: Union[Callable, List[Callable]],
        reset_fn: Callable,
        initial_value: Optional[Any] = None,
        identifier: Optional[str] = None,
    ) -> None:
        """
        Construct Reset Button.

        ### Arguments:
            `default_val : Any`
                Default value of the item(s) when reset.

            `changed_fn : Union[Callable, List[Callable]]`
                The function(s) to let the button be aware that it is in need of reset

            `reset_fn : Callable`
                The Function to call when item is reset.

            `identifier : Optional[str]`
                An optional identifier of the widget we can use to refer to it in queries.
        """
        super().__init__()
        self._button: ui.Rectangle = self.__build(default_val, changed_fn, reset_fn, initial_value, identifier)

        StateMachine().add_tool_creation_state_changed_fn(self.__on_creation_state_changed)

    @property
    def visible(self) -> bool:
        return self._button.visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self._button.visible = value

    def __on_creation_state_changed(self, creation_state: MeasureCreationState):
        self._button.enabled = creation_state in [MeasureCreationState.NONE, MeasureCreationState.START_SELECTION]

    def __build(
        self,
        reset_val: Any,
        changed_fn: Union[Callable, List[Callable]],
        reset_fn: Callable,
        initial_value: Optional[Any],
        identifier: Optional[str],
    ) -> ui.Rectangle:

        def _reset_check_fn(value: Any, button: int):
            if button == 0 and StateMachine().tool_creation_state in [
                MeasureCreationState.NONE,
                MeasureCreationState.START_SELECTION,
            ]:  # left click
                reset_fn(reset_val)

        def _update_reset_button(value: Any, default_value: Any, btn: ui.Rectangle) -> None:
            if isinstance(value, ui.AbstractItemModel):
                value = value.get_item_value_model()

            if isinstance(default_value, bool):
                value = value.as_bool
            elif isinstance(default_value, int):
                value = value.as_int
            elif isinstance(default_value, float):
                value = value.as_float

            btn.visible = value != default_value

        with ui.VStack(name="container", width=0, style=STYLE_BUTTON_RESET):
            ui.Spacer()
            with ui.ZStack(width=12, height=12):
                with ui.HStack(width=12, height=12):
                    ui.Spacer(width=3)
                    with ui.VStack(width=12, height=12):
                        ui.Spacer()
                        ui.Rectangle(name="reset_invalid", width=5, height=5)
                        ui.Spacer()
                _btn = ui.Rectangle(
                    name="reset_valid",
                    width=12,
                    height=12,
                    margin=0,
                    tooltip=TOOLTIP_RESET,
                    alignment=ui.Alignment.V_CENTER,
                    visible=False,
                    identifier=identifier if identifier is not None else "",
                )
            ui.Spacer()

        _btn.set_mouse_released_fn(lambda x, y, btn, mod: _reset_check_fn(reset_val, btn))

        if not isinstance(changed_fn, list):
            changed_fn = [changed_fn]

        for fn in changed_fn:
            fn(lambda value, x=None: _update_reset_button(value, reset_val, _btn))

        if initial_value is not None:
            _update_reset_button(initial_value, reset_val, _btn)

        return _btn


class ToolButton(ui.Button):
    def __init__(self, tool: MeasureMode, clicked_fn: Callable[[MeasureMode], None], enabled: bool = True):
        self._mode: MeasureMode = tool
        self._clicked_fn: Callable[[MeasureMode], None] = clicked_fn

        name = tool.name.lower()
        style = generate_toolbar_button_style(name)

        super().__init__(
            "",
            tooltip=name.replace("_", " ").title(),
            style=style,
            clicked_fn=self._on_clicked,
            width=24,
            height=24,
            enabled=enabled,
        )

        # Statemachine callback for Icon coloring
        self._state_sub = StateMachine().add_tool_state_changed_fn(self._on_state_changed)

    def _on_clicked(self):
        # Check if tool is active. If so. Change state and reset the state machine
        if self.checked:
            StateMachine().reset_state_to_default(is_current_tool=False)
            return

        self._clicked_fn(self._mode)

    def _on_state_changed(self, state: MeasureState, mode: MeasureMode) -> None:
        value = state == MeasureState.CREATE and mode == self._mode
        self.checked = value


class GroupBoxBase(metaclass=ABCMeta):
    def __init__(
        self, group_name: str, draw_label=True, content_name: str = "group_content", bounds_name: str = "group_bounds"
    ):
        self._name = group_name
        self._bounds_name = bounds_name
        self._content_name = content_name
        self._draw_label = draw_label
        self._group: ui.ZStack = self.__build()

    def __build(self) -> ui.ZStack:
        _root = ui.ZStack(name="group_root", style=STYLE_GROUP_BOX)

        with _root:
            # Group Rect
            ui.Rectangle(name=self._bounds_name)
            # Group Text
            if self._draw_label:
                with ui.VStack(spacing=0, name="group_text"):
                    with ui.ZStack():
                        with ui.HStack(spacing=0, height=12):
                            ui.Spacer(width=4)
                            ui.Rectangle(name="label_back", width=len(self._name) * 8)
                            ui.Spacer()
                        with ui.HStack(spacing=0, height=12):
                            ui.Spacer(width=4)
                            ui.Label(self._name, name="group_label", alignment=ui.Alignment.TOP)

            # Content
            with ui.HStack(spacing=0, name=self._content_name):
                self._build_content()

        return _root

    @abstractmethod
    def _build_content(self):
        pass


# Placement
@dataclass
class Snaps:
    """
    Class for keeping track of active or disabled snaps
    """

    surface: Optional[SnapMode] = None
    pivot: Optional[SnapMode] = None
    center: Optional[SnapMode] = None
    vertex: Optional[SnapMode] = None
    edge: Optional[SnapMode] = None
    mid: Optional[SnapMode] = None

    @property
    def active(self) -> List[SnapMode]:
        _active: List[SnapMode] = [val for _, val in vars(self).items() if not callable(val) and val]
        return _active


GEOMETRY_SNAP_UNSUPPORTED = (
    "Vertex, Edge and Mid Point snaps are currently unsupported in Kit 111: they need the hit mesh face, which only "
    "the removed OVRTX world-ray raycast query reported."
)
_geometry_snap_warned = False


class SnapGroupBox(GroupBoxBase):

    def __init__(self, group_name: str):
        self._settings = carb.settings.get_settings()
        self._snaps = Snaps()
        self._on_snaps_changed_fn: Set[Callable[[List[SnapMode]], None]] = set()
        super().__init__(
            group_name, draw_label=False, content_name="snap_group_content", bounds_name="snap_group_bounds"
        )

    @property
    def snaps(self) -> List[SnapMode]:
        return self._snaps.active

    @snaps.setter
    def snaps(self, snaps: List[SnapMode]) -> None:
        self._snaps.surface = None
        self._snaps.vertex = None
        self._snaps.mid = None
        self._snaps.center = None
        self._snaps.edge = None
        self._snaps.pivot = None

        for snap in snaps:
            match snap:
                case SnapMode.SURFACE:
                    self._snaps.surface = SnapMode.SURFACE
                case SnapMode.VERTEX:
                    self._snaps.vertex = SnapMode.VERTEX
                case SnapMode.MIDPOINT:
                    self._snaps.mid = SnapMode.MIDPOINT
                case SnapMode.CENTER:
                    self._snaps.center = SnapMode.CENTER
                case SnapMode.EDGE:
                    self._snaps.edge = SnapMode.EDGE
                case SnapMode.PIVOT:
                    self._snaps.pivot = SnapMode.PIVOT

        if snaps:
            self._snap_collection.model.set_value(self._display_order.index(snaps[0]))

    def _build_content(self):
        with ui.HStack(spacing=24, style=STYLE_CHECKBOX):
            self._snap_collection = ui.RadioCollection()
            self._display_order = []
            button_size = 12
            label_spacing = 6
            label_width = 0
            enable_geometry_snap = self._geometry_snap_enabled()
            with ui.VStack(spacing=button_size, width=0):
                with ui.HStack(spacing=0):
                    self._surface = ui.RadioButton(
                        radio_collection=self._snap_collection, style=STYLE_RADIO_BUTTON, width=button_size
                    )
                    ui.Spacer(width=label_spacing)
                    self._surface_label = ui.Label("Surface", width=label_width, tooltip=TOOLTIP_NONE)
                    self._display_order.append(SnapMode.SURFACE)
                with ui.HStack(spacing=0):
                    self._vertex = ui.RadioButton(
                        radio_collection=self._snap_collection,
                        style=STYLE_RADIO_BUTTON,
                        width=button_size,
                        enabled=enable_geometry_snap,
                    )
                    ui.Spacer(width=label_spacing)
                    self._vertex_label = ui.Label(
                        "Vertex",
                        width=label_width,
                        tooltip=TOOLTIP_VERTEX if enable_geometry_snap else GEOMETRY_SNAP_UNSUPPORTED,
                        enabled=enable_geometry_snap,
                    )
                    self._display_order.append(SnapMode.VERTEX)
                with ui.HStack(spacing=0):
                    self._mid = ui.RadioButton(
                        radio_collection=self._snap_collection,
                        style=STYLE_RADIO_BUTTON,
                        width=button_size,
                        enabled=enable_geometry_snap,
                    )
                    ui.Spacer(width=label_spacing)
                    self._mid_label = ui.Label(
                        "Mid Point",
                        width=label_width,
                        tooltip=TOOLTIP_MIDPOINT if enable_geometry_snap else GEOMETRY_SNAP_UNSUPPORTED,
                        enabled=enable_geometry_snap,
                    )
                    self._display_order.append(SnapMode.MIDPOINT)
            with ui.VStack(spacing=button_size, width=0):
                with ui.HStack(spacing=0):
                    self._center = ui.RadioButton(
                        radio_collection=self._snap_collection, style=STYLE_RADIO_BUTTON, width=button_size
                    )
                    ui.Spacer(width=label_spacing)
                    self._center_label = ui.Label("Center", width=label_width, tooltip=TOOLTIP_CENTER)
                    self._display_order.append(SnapMode.CENTER)
                with ui.HStack(spacing=0):
                    self._edge = ui.RadioButton(
                        radio_collection=self._snap_collection,
                        style=STYLE_RADIO_BUTTON,
                        width=button_size,
                        enabled=enable_geometry_snap,
                    )
                    ui.Spacer(width=label_spacing)
                    self._edge_label = ui.Label(
                        "Edge",
                        width=label_width,
                        tooltip=TOOLTIP_EDGE if enable_geometry_snap else GEOMETRY_SNAP_UNSUPPORTED,
                        enabled=enable_geometry_snap,
                    )
                    self._display_order.append(SnapMode.EDGE)
                with ui.HStack(spacing=0):
                    self._pivot = ui.RadioButton(
                        radio_collection=self._snap_collection, style=STYLE_RADIO_BUTTON, width=button_size
                    )
                    ui.Spacer(width=label_spacing)
                    self._pivot_label = ui.Label("Pivot", width=label_width, tooltip=TOOLTIP_PIVOT)
                    self._display_order.append(SnapMode.PIVOT)

            self._update_widget_style_name()

            # If geometry snap is not supported, fallback to surface.
            if not enable_geometry_snap:
                if (
                    UserSettings().session.snap_vertex is True
                    or UserSettings().session.snap_midpoint is True
                    or UserSettings().session.snap_edge is True
                ):
                    UserSettings().session.snap_vertex = UserSettings().session.snap_midpoint = (
                        UserSettings().session.snap_edge
                    ) = False
                    UserSettings().session.snap_surface = True

            if UserSettings().session.snap_surface:
                self._snap_collection.model.set_value(self._display_order.index(SnapMode.SURFACE))
            elif UserSettings().session.snap_vertex:
                self._snap_collection.model.set_value(self._display_order.index(SnapMode.VERTEX))
            elif UserSettings().session.snap_midpoint:
                self._snap_collection.model.set_value(self._display_order.index(SnapMode.MIDPOINT))
            elif UserSettings().session.snap_center:
                self._snap_collection.model.set_value(self._display_order.index(SnapMode.CENTER))
            elif UserSettings().session.snap_edge:
                self._snap_collection.model.set_value(self._display_order.index(SnapMode.EDGE))
            elif UserSettings().session.snap_pivot:
                self._snap_collection.model.set_value(self._display_order.index(SnapMode.PIVOT))
            else:
                self._snap_collection.model.set_value(self._display_order.index(SnapMode.SURFACE))

            # Null space
            with ui.VStack(width=ui.Percent(33)):
                ui.Spacer()

        # Callbacks
        # self._surface.model.add_value_changed_fn(self._on_surface_changed)
        self._snap_collection.model.add_value_changed_fn(self._on_snaps_changed)

        # Bootstrap
        self._update_snaps(self._snap_collection.model)

    def _update_widget_style_name(self):
        for widget in [
            self._surface,
            self._surface_label,
            self._vertex,
            self._vertex_label,
            self._mid,
            self._mid_label,
            self._center,
            self._center_label,
            self._edge,
            self._edge_label,
            self._pivot,
            self._pivot_label,
        ]:
            widget.name = "" if widget.enabled else "disabled"

    def add_on_snaps_changed_fn(self, func: Callable[[List[SnapMode]], None]):
        self._on_snaps_changed_fn.add(func)

    def clear_snaps(self):
        self.set_snap(SnapMode.SURFACE)

    def lock_snaps(self, locked: bool, exclude: List[SnapMode] = []) -> None:
        enable_geometry_snap = self._geometry_snap_enabled()

        self._surface_label.enabled = self._surface.enabled = not locked or SnapMode.SURFACE in exclude
        self._pivot_label.enabled = self._pivot.enabled = not locked or SnapMode.PIVOT in exclude
        self._center_label.enabled = self._center.enabled = not locked or SnapMode.CENTER in exclude
        self._vertex_label.enabled = self._vertex.enabled = (
            not locked or SnapMode.VERTEX in exclude
        ) and enable_geometry_snap
        self._mid_label.enabled = self._mid.enabled = (
            not locked or SnapMode.MIDPOINT in exclude
        ) and enable_geometry_snap
        self._edge_label.enabled = self._edge.enabled = (
            not locked or SnapMode.EDGE in exclude
        ) and enable_geometry_snap

        self._update_widget_style_name()

    def set_snap(self, mode: SnapMode) -> None:
        if self._snap_collection is None:
            return
        self._snap_collection.model.set_value(self._display_order.index(mode))

    def set_next_snap(self) -> None:
        if self._snap_collection is None:
            return
        current_snap_idx = self._snap_collection.model.as_int
        current_snap_idx = (current_snap_idx + 1) % len(self._display_order)
        self.set_snap(self._display_order[current_snap_idx])

    def _update_snaps(self, model):
        self.snaps = [self._display_order[model.as_int]]

    def _on_snaps_changed(self, model: ui.AbstractValueModel) -> None:
        self._update_snaps(model)

        for fn in self._on_snaps_changed_fn:
            fn(self.snaps)

    def _geometry_snap_enabled(self):
        # Vertex, Edge and Mid Point snaps need the hit mesh face, which only the world-ray raycast query reported.
        # Kit 111 dropped that query (7 Oct 2026) and pick hits carry no face, so these snaps are unsupported.
        global _geometry_snap_warned
        if not _geometry_snap_warned:
            carb.log_warn(GEOMETRY_SNAP_UNSUPPORTED)
            _geometry_snap_warned = True
        return False
