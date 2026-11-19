# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
from collections import defaultdict
from typing import List

import carb
import carb.events
import carb.input
import carb.profiler
import carb.settings
import omni.appwindow
import omni.kit.app
import omni.kit.commands
import omni.kit.undo
import omni.usd
from carb.input import KeyboardInput as Key
from omni.kit.manipulator.viewport import ManipulatorFactory
from omni.ui import scene as sc
from pxr import Sdf, Usd, UsdGeom

from ..bindings import CurveEditingModeType, CurvesEventType, get_interface
from .bezier_curve_edits_context import BezierCurveEditsContext, BezierCurveEditsContextManager
from .context_menu import ContextMenu
from .cv_canvas import CvCanvas
from .cv_manipulator import CvManipulator
from .cv_viz import CvVisualizer
from .tool_settings import ToolSettingsWindow

CURVE_DRAW_POINTS_SETTING = "persistent/exts/omni.curve.manipulator/curveDrawPoints"


class BezierCurveEditsUI:
    def __init__(
        self,
        curve_edits_context: BezierCurveEditsContext,
        viewport_api=None,
    ):
        self._curve_manip = get_interface()
        self._usd_context_name = curve_edits_context.usd_context_name
        self._bezier_curve_edits = curve_edits_context.curve_edits
        self._cv_selection = curve_edits_context.selection
        self._curve_context = curve_edits_context.curve_edits.curve_context
        self._editing_prim_paths = []
        self._viewport_api = viewport_api
        self._legacy_mode = viewport_api is None
        self._input = carb.input.acquire_input_interface()
        self._settings = carb.settings.get_settings()
        self._curves = {}
        self._in_curve_editing_mode = False
        self._was_vp_picking_enabled = None
        self._cv_scene_data = {}
        self._cv_marquee = None
        self._cv_manipulator = CvManipulator(
            self._cv_selection,
            self._curve_context,
            usd_context_name=curve_edits_context.usd_context_name,
            viewport_api=viewport_api,
        )

        if self._legacy_mode is False:
            self._cv_visualizers_root = sc.Transform()

        self._tool_settings = ToolSettingsWindow(
            "Curve", viewport_api, self._usd_context_name, refresh_ui_fn=lambda: self._refresh_tangents()
        )

        self._context = curve_edits_context.usd_context
        self._selection = self._context.get_selection()
        self._stage_event_sub = self._context.get_stage_event_stream().create_subscription_to_pop(self._on_stage_event)

        self._sub_keyboard = None
        self._sub_setting = None
        self._context_menu_task = None

        self._curve_event_sub = self._curve_manip.get_curves_event_stream(
            self._curve_context
        ).create_subscription_to_pop(self.on_curves_event, name="omni.curve.manipulator")

        if self._context.get_stage_state() == omni.usd.StageState.OPENED:
            self._on_stage_opened()

        self._delayed_task = None
        if self._curve_manip.is_in_curve_editing_mode(self._curve_context):
            mode = self._curve_manip.get_curve_editing_mode(self._curve_context)
            paths = self._curve_manip.get_editing_curve_paths(self._curve_context)

            # This usually happens when an VP2 instance is created after curve editing is started
            # need to refresh_vp2 since in constructor the VP2 instance is not fully constructed and setting windows fails to find it
            async def delayed_on_edit():
                self._tool_settings.refresh_vp2()
                self._on_begin_curve_edit(int(mode), paths)
                self._delayed_task = None

            self._delayed_task = asyncio.ensure_future(delayed_on_edit())

    def __del__(self):
        self.destroy()

    def destroy(self):
        if self._delayed_task:
            self._delayed_task.cancel()
            self._delayed_task = None

        if self._sub_keyboard:
            self._input.unsubscribe_to_keyboard_events(None, self._sub_keyboard)
            self._sub_keyboard = None

        if self._sub_setting is not None:
            self._settings.unsubscribe_to_change_events(self._sub_setting)
            self._sub_setting = None

        self._curve_event_sub = None

        if self._cv_manipulator:
            self._cv_manipulator.destroy()
            self._cv_manipulator = None

        self.destroy_curve_visualizers()

        if self._tool_settings:
            self._tool_settings.destroy()
            self._tool_settings = None

        self._stage_event_sub = None

        if self._legacy_mode:
            if self._in_curve_editing_mode:
                vp = self._get_active_legacy_viewport()
                if vp:
                    vp.set_enabled_picking(self._was_vp_picking_enabled)

        if self._context_menu_task:
            self._context_menu_task.cancel()
            self._context_menu_task = None

    def _on_stage_event(self, event: carb.events.IEvent):
        if event.type == int(omni.usd.StageEventType.OPENED):
            self._on_stage_opened()
        elif event.type == int(omni.usd.StageEventType.CLOSING):
            self._stage = None
        elif event.type == int(omni.usd.StageEventType.SELECTION_CHANGED):
            if self._in_curve_editing_mode:
                selected_prim_paths = [path for path in self._context.get_selection().get_selected_prim_paths()]
                if selected_prim_paths != self._editing_prim_paths:
                    omni.kit.commands.execute("DisableCurveEditing", curve_context=self._curve_context)
                    try:
                        import omni.kit.notification_manager as nm

                        nm.post_notification(
                            "You have selected a different prim on the stage causing you to exit edit mode of the basis curve."
                        )
                    except ImportError:
                        pass

    def _on_stage_opened(self):
        self._stage = self._context.get_stage()

    # Wait until the standard viewport 1.0 context menu shows up, then override it with CV context menu.
    # The context menu is triggered via picking request callback, and is processed on rendering thread, then called back
    # on main thread. The timing is nondeterministic and varying at different FPS rate. If we do not wait for it, the
    # viewport context menu can show up after CV context menu and overrides it.
    #
    # No need to do it for VP2 as VP2 context menu is gesture based and will be prevented when invoking CV context menu
    async def _wait_for_vp1_context_menu(self):
        from omni.kit.viewport.utility import get_active_viewport
        from omni.kit.viewport.utility.legacy_viewport_api import LegacyViewportAPI

        legacy_viewport_api = get_active_viewport()
        if isinstance(legacy_viewport_api, LegacyViewportAPI):
            viewport_legacy = legacy_viewport_api.legacy_window

            future = asyncio.Future()

            def on_mouse_event(event: carb.events.IEvent):
                # check its expected event
                if event.type == int(omni.kit.ui.MenuEventType.ACTIVATE):
                    if not future.done():
                        future.set_result(True)

            sub = viewport_legacy.get_mouse_event_stream().create_subscription_to_pop(on_mouse_event, order=1)

            await future

    # delay the context menu for one frame to override default viewport context menu
    async def _on_context_menu_async(self, basis_curves, id):

        if self._legacy_mode:
            await self._wait_for_vp1_context_menu()

        cv_dict = defaultdict(list)

        selected_cvs = self._cv_selection.get_selected_cvs()
        for basis_curves, id in selected_cvs:
            cv_dict[basis_curves].append(id)

        ContextMenu.on_context_menu({"cv_dict": cv_dict, "usd_context_name": self._usd_context_name})

    def _on_context_menu(self, basis_curves, id):
        if self._context_menu_task is None or self._context_menu_task.done():
            self._context_menu_task = asyncio.ensure_future(self._on_context_menu_async(basis_curves, id))

    def create_cv_visualizers(self, paths: List[str]):
        if self._legacy_mode:
            prims = []
            for path in paths:
                path = Sdf.Path(path)
                basis_curves = UsdGeom.BasisCurves.Get(self._stage, path)
                if basis_curves:
                    self._curves[path] = basis_curves
                    self._cv_scene_data[path] = ManipulatorFactory.create_manipulator(
                        CvVisualizer,
                        basis_curves=basis_curves,
                        selection=self._cv_selection,
                        on_context_menu_fn=self._on_context_menu,
                    )
                    self._cv_scene_data[path].selected_ids = set()
                    prims.append(basis_curves)
            if prims:
                self._cv_marquee = ManipulatorFactory.create_manipulator(
                    CvCanvas,
                    enabled=True,
                    viewport_api=self._viewport_api,
                    curve_context=self._curve_context,
                    selection=self._cv_selection,
                    basis_curves_list=prims,
                )
        else:
            with self._cv_visualizers_root:
                prims = []
                for path in paths:
                    path = Sdf.Path(path)
                    basis_curves = UsdGeom.BasisCurves.Get(self._stage, path)
                    if basis_curves:
                        self._curves[path] = basis_curves
                        self._cv_scene_data[path] = CvVisualizer(
                            basis_curves=basis_curves,
                            selection=self._cv_selection,
                            on_context_menu_fn=self._on_context_menu,
                        )
                        self._cv_scene_data[path].selected_ids = set()
                        prims.append(basis_curves)
                if prims:
                    self._cv_marquee = CvCanvas(
                        enabled=True,
                        viewport_api=self._viewport_api,
                        curve_context=self._curve_context,
                        selection=self._cv_selection,
                        basis_curves_list=prims,
                        edit_modifier_flag=0,
                        append_modifier_flag=carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT,
                    )

    def destroy_curve_visualizers(self):
        if self._legacy_mode:
            for viz in self._cv_scene_data.values():
                ManipulatorFactory.destroy_manipulator(viz)
            self._cv_scene_data.clear()

            if self._cv_marquee:
                ManipulatorFactory.destroy_manipulator(self._cv_marquee)
                self._cv_marquee = None
        else:
            for viz in self._cv_scene_data.values():
                viz.enabled = False

            self._cv_scene_data.clear()
            self._cv_visualizers_root.clear()

            if self._cv_marquee:
                self._cv_marquee.enabled = False
                self._cv_marquee = None

    def on_curves_event(self, event: carb.events.IEvent):
        if event.type == int(CurvesEventType.ADD_MULTIPLE_POINTS):
            self._refresh_tangents()
        elif event.type == int(CurvesEventType.BEGIN_CURVE_EDIT):
            self._on_begin_curve_edit(event.payload["mode"], event.payload["paths"])
        elif event.type == int(CurvesEventType.BEGIN_ADD) or event.type == int(CurvesEventType.ADDING):
            self._refresh_tangents()
        elif event.type == int(CurvesEventType.END_CURVE_EDIT):
            self._on_end_curve_edit()

    def _on_begin_curve_edit(self, mode: int, paths: List[str]):
        BezierCurveEditsContextManager.get_context(self._usd_context_name).set_default_prim_paths(paths)
        self._editing_prim_paths = [path for path in paths]
        self._tool_settings.show_window(True)
        self._tool_settings.set_prim_paths(self._stage, paths)
        self._tool_settings.set_pencil_mode(mode)
        self.create_cv_visualizers(paths)
        if self._legacy_mode:
            vp = self._get_active_legacy_viewport()
            if vp:
                self._was_vp_picking_enabled = vp.is_enabled_picking()
                # disallow selection change from viewport
                # user can still change selection from stage window or via commands, in that case it exits curve editing mode
                vp.set_enabled_picking(False)
                self._was_vp_picking_enabled_before_shift = vp.is_enabled_picking()
        self._alt_down_count = 0
        self._shift_down_count = 0
        self._ctrl_down_count = 0
        self._in_curve_sampling_mode = False  # when holding shift and sampling a new CV point
        self._sub_keyboard = self._input.subscribe_to_keyboard_events(None, self._on_keyboard_event)
        self._in_curve_editing_mode = True
        if self._sub_setting is not None:
            self._settings.unsubscribe_to_change_events(self._sub_setting)
            self._sub_setting = None
        self._sub_setting = self._settings.subscribe_to_node_change_events(
            CURVE_DRAW_POINTS_SETTING, lambda *_: self._update_visualizers()
        )
        self._update_visualizers()

    def _on_end_curve_edit(self):
        self._editing_prim_paths = []
        if self._sub_setting is not None:
            self._settings.unsubscribe_to_change_events(self._sub_setting)
            self._sub_setting = None
        self._tool_settings.show_window(False)
        self._in_curve_editing_mode = False
        self.destroy_curve_visualizers()
        if self._legacy_mode:
            vp = self._get_active_legacy_viewport()
            if vp:
                vp.set_enabled_picking(self._was_vp_picking_enabled)
        if self._sub_keyboard:
            self._input.unsubscribe_to_keyboard_events(None, self._sub_keyboard)
            self._sub_keyboard = None

    def _refresh_tangents(self):
        for path in self._cv_scene_data:
            cv_scene_data = self._cv_scene_data[path]
            if isinstance(cv_scene_data, CvVisualizer):
                cv_scene_data.refresh_tangents()

    def _set_value_to_attribute(self, prop_path, value: List, prev=None):
        omni.kit.commands.execute("ChangeProperty", prop_path=prop_path, value=value, prev=prev)

    def _update_extent_attribute(self, basis_curves):
        extent_attr = basis_curves.GetExtentAttr()
        if extent_attr:
            bounds = UsdGeom.Boundable.ComputeExtentFromPlugins(basis_curves, Usd.TimeCode.Default())
            if bounds is not None:
                self._set_value_to_attribute(extent_attr.GetPath(), bounds)

    def _update_visualizers(self):
        enable_visualizers = not self._settings.get(CURVE_DRAW_POINTS_SETTING)
        self._cv_selection.set_enabled(enable_visualizers)
        for p in self._cv_scene_data:
            cv_scene_data = self._cv_scene_data[p]
            if isinstance(cv_scene_data, CvVisualizer):
                cv_scene_data.enable_interactive_items(enable_visualizers)

    def _on_keyboard_event(self, event, *args, **kwargs) -> bool:
        if isinstance(self._cv_marquee, CvCanvas):
            type = event.type
            if type == carb.input.KeyboardEventType.KEY_PRESS or type == carb.input.KeyboardEventType.KEY_RELEASE:
                if event.input in self._cv_marquee.append_modifier_keys():
                    curve_edits = BezierCurveEditsContextManager.get_context(self._usd_context_name).curve_edits
                    curve_edits.set_curve_modifier_pressed(self._cv_marquee.is_append_modifier_down())
            return True

        def exit_sampling_mode():
            if self._in_curve_sampling_mode:
                self._in_curve_sampling_mode = False
                if self._legacy_mode:
                    vp = self._get_active_legacy_viewport()
                    if vp:
                        vp.set_enabled_picking(self._was_vp_picking_enabled_before_shift)

        # Keep track of both ctrl and shift, and only enter sampling mode if shift is down and ctrl is up
        # This is to avoid CTRL+SHIFT marquee selection hotkey conflict
        if event.type == carb.input.KeyboardEventType.KEY_RELEASE:
            if event.input == Key.LEFT_ALT or event.input == Key.RIGHT_ALT:
                self._alt_down_count -= 1
                curve_edits = BezierCurveEditsContextManager.get_context(self._usd_context_name).curve_edits
                curve_edits.set_curve_modifier_pressed(bool(self._alt_down_count > 0))
            elif event.input == Key.LEFT_SHIFT or event.input == Key.RIGHT_SHIFT:
                self._shift_down_count -= 1
                # exit sampling mode when shift is up, regardless of ctrl state
                if self._shift_down_count <= 0:
                    self._shift_down_count = 0
                    exit_sampling_mode()
            elif event.input == Key.LEFT_CONTROL or event.input == Key.RIGHT_CONTROL:
                self._ctrl_down_count -= 1
                if self._shift_down_count <= 0:
                    self._shift_down_count = 0

        if event.type == carb.input.KeyboardEventType.KEY_PRESS:
            if event.input == Key.LEFT_ALT or event.input == Key.RIGHT_ALT:
                self._alt_down_count += 1
                curve_edits = BezierCurveEditsContextManager.get_context(self._usd_context_name).curve_edits
                curve_edits.set_curve_modifier_pressed(bool(self._alt_down_count > 0))
            elif event.input == Key.LEFT_SHIFT or event.input == Key.RIGHT_SHIFT:
                self._shift_down_count += 1
                # enter sampling mode only if shift is down and ctrl is up
                if self._shift_down_count == 1 and self._ctrl_down_count <= 0:
                    vp = self._get_active_legacy_viewport()
                    if vp:
                        self._was_vp_picking_enabled_before_shift = vp.is_enabled_picking()
                        # Need to reenable picking to add points when SHIFT is down
                        vp.set_enabled_picking(True)
                        self._in_curve_sampling_mode = True
            elif event.input == Key.LEFT_CONTROL or event.input == Key.RIGHT_CONTROL:
                self._ctrl_down_count += 1
                # exit sample mode if ctrl is down while shift is still down
                if self._ctrl_down_count == 1 and self._shift_down_count > 0:
                    exit_sampling_mode()
        return True

    def _get_active_legacy_viewport(self):
        try:
            import omni.kit.viewport_legacy

            # TODO VP2.0
            viewport = omni.kit.viewport_legacy.get_viewport_interface()
            self._vp1_instances = viewport.get_instance_list()

            for instance in self._vp1_instances:
                window = viewport.get_viewport_window(instance)
                # Since we cannot know from here which viewport is in, just request from focused viewport.
                if window.is_focused():
                    return window

            return omni.kit.viewport_legacy.get_default_viewport_window()
        except ImportError:
            pass
        return None
