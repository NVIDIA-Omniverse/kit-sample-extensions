# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["GlobalPanel", "PlacementPanel", "DisplayPanel", "ManagePanel"]

from abc import ABCMeta, abstractmethod
from collections import Counter
from typing import Callable, List, Optional, Union

import omni.usd as ou
from carb.settings import get_settings as get_carb_settings
from omni import ui
from pxr import Gf, UsdGeom

from ..common import (
    SETTINGS_STARTUP_UI_COLLAPSED,
    VISIBILITY_PATH,
    ConstrainAxis,
    DisplayAxisSpace,
    DistanceType,
    LabelSize,
    MeasureMode,
    MeasureState,
    Precision,
    SnapMode,
    SnapTo,
    UnitType,
    UserSettings,
    get_stage_units,
)
from ..interface.style import STYLE_COMBO_BOX_ALT
from ..manager import MeasurementManager, ReferenceManager, StateMachine
from ..system.export import ExportPanel
from ._delegate import MeasurePanelDelegate
from ._widgets import ResetButton, SnapGroupBox, ToolButton
from .style import *


class SubPanelBase(metaclass=ABCMeta):

    def __init__(self, panel_name: str):
        self._ctx = ou.get_context()
        self._name: str = panel_name
        self._root: Union[ui.Stack, ui.CollapsableFrame] = self._draw()
        self._set_defaults()

    @property
    def visible(self) -> bool:
        return self._root.visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self._root.visible = value

    @abstractmethod
    def _draw(self) -> Union[ui.Stack, ui.CollapsableFrame]:
        """
        Draw the panel content.
        """
        return

    @abstractmethod
    def _set_defaults(self) -> None:
        """
        Set the defaults for panel attributes
        """
        if isinstance(self._root, ui.CollapsableFrame):
            _collapsed = get_carb_settings().get(SETTINGS_STARTUP_UI_COLLAPSED) or []
            if not isinstance(_collapsed, (list, tuple)):
                _collapsed = []
            self._root.collapsed = any(self._name.lower() == panel.lower() for panel in _collapsed)


class GlobalPanel(SubPanelBase):
    def __init__(self):
        self._measure_selected_fn: List[Callable] = []
        super().__init__("Global")

        # Stage Subscription
        self._selection_changed_sub: int = StateMachine().subscribe_to_stage_event(
            self.__on_selection_changed, ou.StageEventType.SELECTION_CHANGED
        )

        # Assign itself to the reference manager
        ReferenceManager().ui_global_panel = self

    @property
    def distance(self) -> DistanceType:
        if not self._cb_distance:
            return DistanceType.CENTER
        model = self._cb_distance.model
        value = model.get_item_value_model().as_int
        return DistanceType(value)

    def _draw(self) -> ui.Stack:
        _stack = ui.VStack(spacing=6)

        with _stack:
            # TODO: FOR BEYOND 2022.3
            # Tool Bar
            with ui.HStack(spacing=0):
                ui.Spacer(width=150)
                with ui.HStack(spacing=4):
                    ui.Spacer()
                    ui.Spacer(width=24)
                    for tool in MeasureMode:
                        if tool.value in [0, 1, 2, 3, 4]:  # TODO: when all are ready we need to use tool.value >= 1
                            ToolButton(tool, StateMachine().set_creation_state)

                        if tool.value == 6:  # Requires a different callback for MeasureSelected
                            ui.Rectangle(width=1, height=24)  # Vertical Separator
                            self._measure_selected = ToolButton(tool, self._on_measure_selected, enabled=False)
                            combo_style = STYLE_COMBO_BOX.copy()
                            combo_style["ComboBox"]["font_size"] = 16  # To cheat the height because combo box.
                            self._cb_distance = ui.ComboBox(
                                UserSettings().session.distance,
                                *[e.name.title() for e in DistanceType],
                                width=80,
                                tooltip="Selected Mode",
                                enabled=False,
                                style=combo_style,
                            )

        # Callbacks
        self._cb_distance.model.add_item_changed_fn(self._on_distance_changed)

        return _stack

    def add_measure_selected_fn(self, function: Callable):
        self._measure_selected_fn.append(function)

    def set_distance_type(self, distance_type: DistanceType):
        d_to_int = list(DistanceType).index(distance_type)
        self._cb_distance.model.get_item_value_model().as_int = d_to_int

    def _set_defaults(self) -> None:
        pass

    def _on_measure_selected(self, mode: Optional[MeasureMode] = None) -> None:
        for fn in self._measure_selected_fn:
            fn()
        StateMachine().reset_state_to_default()

    def _on_distance_changed(self, model: ui.AbstractItemModel, item: ui.AbstractItem) -> None:
        UserSettings().session.distance = model.get_item_value_model(item).get_value_as_int()

    # ------ Listeners / Notifiers ------
    def __on_selection_changed(self):
        stage = self._ctx.get_stage()
        selected_paths = ou.get_context().get_selection().get_selected_prim_paths()
        xformables = Counter(stage.GetPrimAtPath(path).IsA(UsdGeom.Xformable) for path in selected_paths)

        selection_test = xformables[True] >= 2
        self._measure_selected.enabled = selection_test
        self._cb_distance.enabled = selection_test


class PlacementPanel(SubPanelBase):
    def __init__(self):
        self._snap_state = {SnapTo.CUSTOM: [SnapMode.VERTEX], SnapTo.PERPENDICULAR: [SnapMode.SURFACE]}

        self._snap_group: Optional[SnapGroupBox] = None
        super().__init__("Placement")

        StateMachine().add_tool_state_changed_fn(self._on_tool_state_changed)

        # Assign itself to the reference manager
        ReferenceManager().ui_placement_panel = self

    @property
    def snap_to(self) -> SnapTo:
        if not self._cb_snap_selection_mode:
            return SnapTo.CUSTOM
        model = self._cb_snap_selection_mode.model
        index = model.get_item_value_model().as_int
        return SnapTo(index)

    @property
    def snap_group(self) -> Optional[SnapGroupBox]:
        return self._snap_group

    @property
    def snap_mode(self) -> List[SnapMode]:
        if not self._snap_group:
            return [SnapMode.SURFACE]
        return self._snap_group.snaps

    @property
    def constrain_mode(self) -> ConstrainAxis:
        if not self._constrain_combo:
            return ConstrainAxis.STAGE_UP

        model = self._constrain_combo.model
        index = model.get_item_value_model().as_int
        return ConstrainAxis(index)

    def _draw(self) -> ui.CollapsableFrame:
        _frame = ui.CollapsableFrame(self._name, name="frame", style=STYLE_PLACEMENT_PANEL)

        with _frame:
            with ui.VStack(name="container", height=0, spacing=8):
                with ui.HStack(height=0):
                    ui.Label("Snap To", width=0, tooltip=TOOLTIP_SNAP_TO)
                    ui.Spacer(width=24)
                    self._cb_snap_selection_mode = ui.ComboBox(
                        UserSettings().session.snapping_mode,
                        *[e.name.title() for e in SnapTo],
                        width=ui.Fraction(1),
                        alignment=ui.Alignment.RIGHT,
                        style=STYLE_COMBO_BOX_ALT,
                    )
                    ui.Spacer(width=4)
                    with ui.HStack(width=0):
                        ResetButton(
                            UserSettings().default_session.snapping_mode,
                            self._cb_snap_selection_mode.model.add_item_changed_fn,
                            self._on_snap_selection_mode_reset,
                            initial_value=self._cb_snap_selection_mode.model,
                        )

                self._snap_group = SnapGroupBox("Snap To")
                with ui.CollapsableFrame("Options", name="foreground"):
                    with ui.VStack(spacing=4):
                        # # Snap Precision
                        # with ui.HStack(spacing=0, width=ui.Percent(100)):
                        #     ui.Label("Snap Precision", width=150)
                        #     self._precision_float = ui.FloatField(name="precision")
                        #     self._precision_float.model.as_float = 0.5
                        #     ui.Spacer(width=5)
                        #     ResetButton(
                        #         0.5,
                        #         self._precision_float.model.add_value_changed_fn,
                        #         self._on_precision_reset
                        #     )
                        # Constraint
                        self._constrain_stack = ui.HStack(spacing=0, width=ui.Percent(100))
                        with self._constrain_stack:
                            ui.Label("Constrain To", width=150, tooltip=TOOLTIP_CONSTRAINT)
                            self._constrain_combo = ui.ComboBox(
                                UserSettings().session.constrain_axis,
                                *[e.name.replace("_", " ").title() for e in ConstrainAxis],
                                width=ui.Fraction(1),
                                alignment=ui.Alignment.RIGHT,
                            )
                            ui.Spacer(width=5)
                            ResetButton(
                                UserSettings().default_session.constrain_axis,
                                self._constrain_combo.model.add_item_changed_fn,
                                self._on_constraint_reset,
                                initial_value=self._constrain_combo.model,
                            )
                        # # Backface Cull
                        # with ui.HStack(spacing=0, width=ui.Percent(100)):
                        #     ui.Label("Backface Cull", width=150)
                        #     self._cull_chk = ui.CheckBox(selected=True, width=24)
                        #     self._cull_chk.model.set_value(True)
                        #     ui.Line(style=STYLE_LINE)
                        #     ui.Spacer(width=5)
                        #     ResetButton(
                        #         True,
                        #         self._cull_chk.model.add_value_changed_fn,
                        #         self._on_cull_reset
                        #     )

        # Callbacks:
        self._constrain_combo.model.add_item_changed_fn(self._on_constrain_axis_changed)
        self._cb_snap_selection_mode.model.add_item_changed_fn(self._on_snap_selection_mode_changed)

        return _frame

    def lock_properties(self, lock: bool) -> None:
        snap_selection_lock = StateMachine().tool_mode == MeasureMode.POINT_TO_POINT
        self._cb_snap_selection_mode.enabled = not lock if snap_selection_lock else False

    def _set_defaults(self) -> None:
        return super()._set_defaults()

    def _on_constrain_axis_changed(self, model: ui.AbstractItemModel, item: ui.AbstractItem) -> None:
        index = model.get_item_value_model().as_int
        UserSettings().session.constrain_axis = index

    def _on_snap_selection_mode_changed(self, model: ui.AbstractItemModel, item: ui.AbstractItem) -> None:
        self._snap_state[SnapTo(UserSettings().session.snapping_mode)] = self._snap_group.snaps

        index = model.get_item_value_model().as_int
        self._snap_group.snaps = self._snap_state.get(SnapTo(index), [])

        use_perpendicular: bool = SnapTo(index) == SnapTo.PERPENDICULAR
        self._snap_group.lock_snaps(use_perpendicular, self._snap_group.snaps)
        UserSettings().session.snapping_mode = index

    def _on_snap_selection_mode_reset(self, value: int):
        if not self._cb_snap_selection_mode:
            return
        model = self._cb_snap_selection_mode.model
        model.get_item_value_model().set_value(value)

    def _on_precision_reset(self, value: float) -> None:
        if not self._precision_float:
            return
        model = self._precision_float.model
        model.as_float = value

    def _on_constraint_reset(self, value: int) -> None:
        if not self._constrain_combo:
            return
        model = self._constrain_combo.model
        model.get_item_value_model().set_value(value)

    def _on_cull_reset(self, value: bool) -> None:
        if not self._cull_chk:
            return
        model = self._cull_chk.model
        model.set_value(value)

    def _on_tool_state_changed(self, state: MeasureState, mode: MeasureMode) -> None:
        if mode != MeasureMode.POINT_TO_POINT:
            self._cb_snap_selection_mode.model.get_item_value_model().as_int = 0
            self._cb_snap_selection_mode.enabled = False
        else:
            self._cb_snap_selection_mode.enabled = True

        self._constrain_combo.enabled = state != MeasureState.NONE and mode == MeasureMode.AREA


class DisplayPanel(SubPanelBase):
    def __init__(self):
        super().__init__("Display")

        StateMachine().add_tool_state_changed_fn(self._on_tool_state_changed)

        # Assign itself to the reference manager
        ReferenceManager().ui_display_panel = self

    @property
    def display_axis(self) -> DisplayAxisSpace:
        model = self._cb_display_axis.model
        index = model.get_item_value_model().as_int
        return DisplayAxisSpace(index)

    @property
    def precision(self) -> Precision:
        if not self._precision_combo:
            return Precision.INTEGER
        model = self._precision_combo.model
        index = model.get_item_value_model().as_int
        item = model.get_item_children()[index]
        value = model.get_item_value_model(item).as_string
        return Precision(value)

    @property
    def unit(self) -> UnitType:
        if not self._cb_units:
            return UnitType.CENTIMETERS
        model = self._cb_units.model
        index = model.get_item_value_model().as_int
        item = model.get_item_children()[index]
        unit = model.get_item_value_model(item).as_string
        return UnitType[unit.upper()]

    @property
    def precision_int(self) -> int:
        if not self._precision_combo:
            return 0
        model = self._precision_combo.model
        return model.get_item_value_model().as_int

    @property
    def color(self) -> Gf.Vec4f:
        if not self._color_widget:
            return Gf.Vec4f(0.0, 1.0, 1.0, 1.0)
        model = self._color_widget.model
        sub_models = model.get_item_children()
        colors = [model.get_item_value_model(channel).as_float for channel in sub_models]
        return Gf.Vec4f(colors[0], colors[1], colors[2], 1.0)

    @property
    def text_size(self) -> LabelSize:
        if not self._size_combo:
            return LabelSize.MEDIUM
        model = self._size_combo.model
        index = model.get_item_value_model().as_int
        item = model.get_item_children()[index]
        size = model.get_item_value_model(item).as_string.upper().replace(" ", "_")
        return LabelSize[size]

    def _draw(self) -> ui.CollapsableFrame:
        _frame = ui.CollapsableFrame(self._name, name="frame", style=STYLE_DISPLAY_PANEL, identifier="DisplayPanal")

        with _frame:
            with ui.VStack(name="container", spacing=4, height=0):
                # Supplemental Display Axis
                with ui.HStack(spacing=0):
                    ui.Label("Display XYZ", width=150, tooltip=TOOLTIP_AXIS)
                    self._cb_display_axis = ui.ComboBox(
                        UserSettings().session.display_axis,
                        *[e.name.title() for e in DisplayAxisSpace],
                        width=ui.Fraction(1),
                        alighnment=ui.Alignment.RIGHT,
                        enabled=True,
                        identifier="AxisCombo",
                    )
                    ui.Spacer(width=5)
                    ResetButton(
                        UserSettings().default_session.display_axis,
                        self._cb_display_axis.model.add_item_changed_fn,
                        self._on_display_axis_reset,
                        initial_value=self._cb_display_axis.model,
                        identifier="AxisResetBtn",
                    )
                # Measurement Units
                with ui.HStack(spacing=0):
                    ui.Label("Units", width=150, tooltip=TOOLTIP_UNIT)
                    self._cb_units = ui.ComboBox(
                        UserSettings().session.units,
                        *[e.name.title() for e in UnitType],
                        width=ui.Fraction(1),
                        alignment=ui.Alignment.RIGHT,
                        identifier="UnitsCombo",
                    )
                    ui.Spacer(width=5)
                    ResetButton(
                        UserSettings().default_session.units,
                        self._cb_units.model.add_item_changed_fn,
                        self._on_units_reset,
                        initial_value=self._cb_units.model,
                        identifier="UnitsResetBtn",
                    )
                # Measurement Precision
                with ui.HStack(spacing=0):
                    ui.Label("Precision", width=150, tooltip=TOOLTIP_PRECISION)
                    self._precision_combo = ui.ComboBox(
                        UserSettings().session.label_precision,
                        *[e.value for e in Precision],
                        width=ui.Fraction(1),
                        aligntment=ui.Alignment.RIGHT,
                        identifier="PrecisionCombo",
                    )
                    ui.Spacer(width=5)
                    ResetButton(
                        UserSettings().default_session.label_precision,
                        self._precision_combo.model.add_item_changed_fn,
                        self._on_precision_reset,
                        initial_value=self._precision_combo.model,
                        identifier="PrecisionResetBtn",
                    )
                # Measurement Label
                with ui.HStack(spacing=0):
                    ui.Label("Label Size", width=150, tooltip=TOOLTIP_LABEL_SIZE)
                    self._size_combo = ui.ComboBox(
                        UserSettings().session.label_size,
                        *[e.name.title().replace("_", " ") for e in LabelSize],
                        width=ui.Fraction(1),
                        alignment=ui.Alignment.RIGHT,
                        identifier="LabelSizeCombo",
                    )
                    ui.Spacer(width=5)
                    ResetButton(
                        UserSettings().default_session.label_size,
                        self._size_combo.model.add_item_changed_fn,
                        self._on_size_reset,
                        initial_value=self._size_combo.model,
                        identifier="LabelSizeResetBtn",
                    )
                # Measurement Color
                with ui.HStack(spacing=0):
                    ui.Label("Line Color", width=150, tooltip=TOOLTIP_COLOR)
                    self._color_widget = ui.ColorWidget(
                        UserSettings().session.get_color_r(),
                        UserSettings().session.get_color_g(),
                        UserSettings().session.get_color_b(),
                        width=50,
                        height=0,
                    )
                    self._color_widget.model.add_end_edit_fn(self._on_color_updated)
                    ui.Spacer(width=5)
                    ui.Line(style=STYLE_LINE)
                    ui.Spacer(width=5)
                    self._color_reset_btn = ResetButton(
                        [
                            UserSettings().default_session.get_color_r(),
                            UserSettings().default_session.get_color_g(),
                            UserSettings().default_session.get_color_b(),
                        ],
                        self._color_widget.model.add_item_changed_fn,
                        self._on_color_reset,
                        initial_value=[
                            UserSettings().session.get_color_r(),
                            UserSettings().session.get_color_g(),
                            UserSettings().session.get_color_b(),
                        ],
                        identifier="ColorResetBtn",
                    )

        # Callbacks
        self._size_combo.model.add_item_changed_fn(self._on_label_size_changed)
        self._cb_display_axis.model.add_item_changed_fn(self._on_display_axis_changed)
        self._cb_units.model.add_item_changed_fn(self._on_units_changed)
        self._precision_combo.model.add_item_changed_fn(self.__on_precision_changed)

        return _frame

    def lock_properties(self, lock: bool) -> None:
        axis_lock = StateMachine().tool_mode in [MeasureMode.NONE, MeasureMode.POINT_TO_POINT]
        self._cb_display_axis.enabled = not lock if axis_lock else False
        self._cb_units.enabled = not lock
        self._precision_combo.enabled = not lock
        self._size_combo.enabled = not lock
        self._color_widget.enabled = not lock

    def _set_defaults(self) -> None:
        return super()._set_defaults()

    def __on_precision_changed(self, model: ui.AbstractItemModel, item: ui.AbstractItem) -> None:
        UserSettings().session.label_precision = model.get_item_value_model(item).get_value_as_int()

    def _on_units_changed(self, model: ui.AbstractItemModel, item: ui.AbstractItem) -> None:
        UserSettings().session.units = model.get_item_value_model(item).get_value_as_int()

    def _on_display_axis_changed(self, model: ui.AbstractItemModel, item: ui.AbstractItem) -> None:
        UserSettings().session.display_axis = model.get_item_value_model(item).get_value_as_int()

    def _on_display_axis_reset(self, value: int):
        model = self._cb_display_axis.model
        model.get_item_value_model().set_value(value)

    def _on_name_visibility_changed(self, model: ui.AbstractValueModel) -> None:
        value = model.as_bool

    def _on_color_updated(self, model: ui.AbstractItemModel, item: ui.AbstractItem) -> None:
        value = [model.get_item_value_model(i).as_float for i in model.get_item_children()]
        UserSettings().session.set_color_rgba(value)

    def _on_label_size_changed(self, model: ui.AbstractItemModel, item: ui.AbstractItem):
        UserSettings().session.label_size = model.get_item_value_model(item).get_value_as_int()

    def _on_precision_reset(self, value: int) -> None:
        if not self._precision_combo:
            return
        model = self._precision_combo.model
        model.get_item_value_model().set_value(value)

    def _on_units_reset(self, value: int) -> None:
        # Reset the units to the scene's default.
        model = self._cb_units.model
        model.get_item_value_model().set_value(UserSettings().default_session.units)

    def _on_size_reset(self, value: int) -> None:
        if not self._size_combo:
            return
        model = self._size_combo.model
        model.get_item_value_model().set_value(value)

    def _on_color_reset(self, value: List[Union[int, float]]) -> None:
        model = self._color_widget.model
        sub_models = model.get_item_children()
        model.get_item_value_model(sub_models[0]).as_float = value[0]
        model.get_item_value_model(sub_models[1]).as_float = value[1]
        model.get_item_value_model(sub_models[2]).as_float = value[2]
        self._on_color_updated(model, sub_models[0])
        self._color_reset_btn.visible = False

    def _on_tool_state_changed(self, state: MeasureState, mode: MeasureMode):
        axis_lock: bool = mode in [MeasureMode.NONE, MeasureMode.POINT_TO_POINT]

        display_axis = self._cb_display_axis
        display_axis.enabled = axis_lock

        if not axis_lock:
            display_axis.model.get_item_value_model().set_value(DisplayAxisSpace.NONE.value)

        unit_lock: bool = mode != MeasureMode.ANGLE
        display_unit = self._cb_units
        display_unit.enabled = unit_lock


class ManagePanel(SubPanelBase):
    def __init__(self):
        self.__query_model = ui.SimpleStringModel()
        self.__query_sub = self.__query_model.add_value_changed_fn(self._on_search_changed)

        self._delegate = MeasurePanelDelegate()
        self._export_window = ExportPanel()
        self._export_window.visible = False
        super().__init__("Manage")

        # Get callback for selection changed
        self._selection_sub = StateMachine().subscribe_to_stage_event(
            self.__on_stage_selection_changed, ou.StageEventType.SELECTION_CHANGED
        )

        # Assign itself to the reference manager
        ReferenceManager().ui_manage_panel = self

    def __on_stage_selection_changed(self):
        selection = ou.get_context().get_selection()
        if len(selection.get_selected_prim_paths()) == 0:
            self._measurement_view.clear_selection()
            ReferenceManager().measure_scene.deselect_all()

    def _on_search_changed(self, model) -> None:
        query = model.as_string
        self._search_overlay.visible = len(query) == 0
        MeasurementManager()._model.set_search(query)

    def _on_tree_selection_changed(self, items) -> None:
        selected_paths = [str(item.path) for item in items]

        ReferenceManager().measure_scene.deselect_all()
        for item in items:
            ReferenceManager().measure_scene.select(item.uuid)

        selection = ou.get_context().get_selection()
        selection.set_selected_prim_paths(selected_paths, True)

    def _on_tree_hover_changed(self, item: "MeasurePrim", hovered: bool) -> None:
        if not hasattr(item, "uuid"):
            return
        if not item.visible:
            ReferenceManager().measure_scene.clear_hovered()
            return
        ReferenceManager().measure_scene.set_hovered(item.uuid, hovered)

    def _on_filter_reset(self) -> None:
        MeasurementManager()._model.reset_filters()
        for item in self.__filter_items:
            if item.checked:
                item.checked = False

    def _on_filter_by(self, mode: MeasureMode, enabled: bool) -> None:
        MeasurementManager()._model.set_filter_type(mode, enabled)

    def _on_export_csv(self):
        self._export_window.visible = True

    def _on_hide_all(self):
        MeasurementManager().set_visibility_all(False)
        # UserSettings().persistent.set_bool(VISIBILITY_PATH, False)
        for uuid, item in self._delegate.items:
            item.visibility_btn.checked = True

    def _on_unhide_all(self):
        MeasurementManager().set_visibility_all(True)
        # UserSettings().persistent.set_bool(VISIBILITY_PATH, True)
        for uuid, item in self._delegate.items:
            item.visibility_btn.checked = False

    def _draw_menu(self):
        with ui.Frame():
            # Filter Menu
            self._filter_menu = ui.Menu("Filter")
            with self._filter_menu:
                ui.MenuItem("Filter by type", enabled=False, opaque_for_mosue_events=True)
                ui.Separator()
                ui.MenuItem("Reset", triggered_fn=self._on_filter_reset, opaque_for_mouse_events=True)
                ui.Separator()
                filter_p2p = ui.MenuItem(
                    "Point To Point",
                    checkable=True,
                    checked_changed_fn=lambda c: self._on_filter_by(MeasureMode.POINT_TO_POINT, c),
                )
                filter_multi = ui.MenuItem(
                    "Multi Point",
                    checkable=True,
                    checked_changed_fn=lambda c: self._on_filter_by(MeasureMode.MULTI_POINT, c),
                )
                filter_angle = ui.MenuItem(
                    "Angle", checkable=True, checked_changed_fn=lambda c: self._on_filter_by(MeasureMode.ANGLE, c)
                )
                filter_area = ui.MenuItem(
                    "Area", checkable=True, checked_changed_fn=lambda c: self._on_filter_by(MeasureMode.AREA, c)
                )
                filter_selected = ui.MenuItem(
                    "Selected", checkable=True, checked_changed_fn=lambda c: self._on_filter_by(MeasureMode.SELECTED, c)
                )

            self.__filter_items = [filter_p2p, filter_multi, filter_angle, filter_area, filter_selected]

            # Options Menu
            self._options_menu = ui.Menu("Options")
            with self._options_menu:
                ui.MenuItem("Options", enabled=False)
                ui.Separator()
                option_csv = ui.MenuItem("Export to CSV", triggered_fn=self._on_export_csv)
                ui.Separator()
                option_hide_all = ui.MenuItem("Hide All", triggered_fn=self._on_hide_all)
                option_unhide_all = ui.MenuItem("Unhide All", triggered_fn=self._on_unhide_all)
                ui.Separator()
                option_delete_all = ui.MenuItem("Delete All", triggered_fn=MeasurementManager().delete_all)
            ui.Spacer(width=0, height=0)  # to bump off options menu

    def _draw(self) -> ui.CollapsableFrame:
        self._draw_menu()
        _frame = ui.CollapsableFrame(self._name, name="frame", identifier="ManagePanel", style=STYLE_DISPLAY_PANEL)

        with _frame:
            with ui.VStack(name="container", spacing=4, height=0):
                # Local Visibility
                # with ui.HStack(spacing=4):
                # self._toggle_local_visibility = ui.CheckBox(width=12, style=STYLE_CHECKBOX)

                # Toolbar
                with ui.HStack(spacing=4):
                    with ui.ZStack(style=STYLE_SEARCH_FIELD):
                        self._search_field = ui.StringField(
                            model=self.__query_model, name="search", identifier="Search"
                        )
                        self._search_overlay = ui.Label("Search Measurements", name="overlay")
                    filter_btn = ui.Button(
                        tooltip=TOOLTIP_FILTER,
                        style=STYLE_BUTTON_FILTER,
                        width=24,
                        height=24,
                        clicked_fn=lambda: self._filter_menu.show(),
                    )
                    options_btn = ui.Button(
                        tooltip=TOOLTIP_OPTIONS,
                        style=STYLE_BUTTON_OPTIONS,
                        width=24,
                        height=24,
                        clicked_fn=lambda: self._options_menu.show(),
                    )

                ui.Spacer(width=4)
                # Tree View / Delegate info
                scroll_frame = ui.ScrollingFrame(
                    height=200,
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
                )
                with scroll_frame:
                    self._measurement_view = ui.TreeView(
                        MeasurementManager()._model,
                        delegate=self._delegate,
                        root_visible=False,
                        header_visible=True,
                        column_widths=[
                            ui.Pixel(45),
                            ui.Pixel(45),
                            ui.Fraction(1),
                            ui.Fraction(1),
                            ui.Pixel(45),
                            ui.Pixel(45),
                        ],
                        style={"margin": 0.5},
                        selection_changed_fn=self._on_tree_selection_changed,
                    )
                    self._measurement_view.set_hover_changed_fn(self._on_tree_hover_changed)

        return _frame

    def _set_defaults(self) -> None:
        return super()._set_defaults()

    def update_selection(self):
        self._measurement_view.selection = MeasurementManager().selected
