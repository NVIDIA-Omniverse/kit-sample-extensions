# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import asyncio

import carb
import carb.settings
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni import ui
from omni.kit.viewport.window.scene.scenes import CameraAxisLayer
from omni.ui import color as cl
from pxr import Sdf, Tf, Usd, UsdGeom

from .constants import METRICS_ASSEMBLER_HUD_SETTING_SUFFIX
from .tools import get_per_viewport_setting_path, get_persistent_per_viewport_setting_path, resolve_viewport_setting


class MetricsAssemblerUnitsView:
    """View class for displaying units in the viewport.

    Displays the current stage's distance units (e.g. meters, feet) in an overlay in the viewport.
    Handles unit changes and viewport visibility settings.
    """

    UNIT_TEXT_HORIZ_OFFSET: int = 12
    UNIT_TEXT_WIDTH: int = 35
    UNIT_TEXT_HEIGHT: int = 14

    KNOWN_UNITS: tuple[str, ...] = ("cm", "dm", "m", "km", "mm", "in", "ft", "mi")
    KNOWN_MPU: tuple[float, ...] = (0.01, 0.1, 1.0, 1000.0, 0.001, 0.0254, 0.3048, 1609.34)
    EPSILON: float = 0.02

    def __init__(self, desc: dict):
        """Initialize the units view.

        Args:
            desc (dict): Description dictionary containing viewport API
        """
        self._settings_subs = []
        self._change_info_path_subscriptions = []
        self._objects_changed_listener = None
        self._units_text = None
        self._overlay_visible = False
        self._root = None
        self._units_ui_ctrl = None
        # Last metersPerUnit value we saw. Used to detect changes so we can warn the user that
        # only the unit metadata is updated — existing geometry is not auto-converted.
        self._last_known_mpu: float | None = None

        self._stage_event_sub = [
            get_eventdispatcher().observe_event(
                observer_name="omni.usd.metrics.assembler.ui:MetricsAssemblerUnitsView",
                event_name=omni.usd.get_context().stage_event_name(omni.usd.StageEventType.OPENED),
                on_event=lambda _: self._on_stage_open_event(),
            )
        ]

        viewport_api = desc.get("viewport_api")
        if not viewport_api:
            raise RuntimeError("Cannot create MetricsAssemblerUnitsView without a viewport")

        self._viewport_api_id: str = str(viewport_api.id)

        viewport_setting_path = get_per_viewport_setting_path(
            self._viewport_api_id, METRICS_ASSEMBLER_HUD_SETTING_SUFFIX
        )

        # settings subs
        self._settings_subs = [
            omni.kit.app.SettingChangeSubscription(viewport_setting_path, self._show_overlay_changed)
        ]

        # info path change subs
        self._change_info_path_subscriptions = [
            omni.usd.get_watcher().subscribe_to_change_info_path("/", self._on_change_info_path)
        ]

        # Direct Tf.Notice listener catches stage-metadata changes at the absolute root
        # (e.g. metersPerUnit) which the watcher's path subscription can miss when the
        # change is dispatched as a resync rather than info-only.
        self._register_objects_changed_listener()

        self._create_overlay()

        self._refresh_units()  # get initial text value

        # setup the visibility setting
        carb.settings.get_settings().set_bool(
            viewport_setting_path,
            bool(resolve_viewport_setting(self._viewport_api_id, METRICS_ASSEMBLER_HUD_SETTING_SUFFIX)),
        )

    def _adjust_cam_axis_layer_size(self, units_overlay_visible: bool) -> None:
        """Adjust camera axis layer size based on units overlay visibility.

        Args:
            units_overlay_visible (bool): Whether units overlay is visible
        """
        if units_overlay_visible:
            height = CameraAxisLayer.CAMERA_AXIS_DEFAULT_SIZE[1] + self.UNIT_TEXT_HEIGHT + 10
        else:
            height = CameraAxisLayer.CAMERA_AXIS_DEFAULT_SIZE[1]
        carb.settings.get_settings().set(
            f"{CameraAxisLayer.get_axis_size_setting_path(self._viewport_api_id)}/1", height
        )

    async def _adjust_cam_axis_layer_size_async(self, units_overlay_visible: bool) -> None:
        """Asynchronously adjust camera axis layer size.

        Args:
            units_overlay_visible (bool): Whether units overlay is visible
        """
        await omni.kit.app.get_app().next_update_async()
        self._adjust_cam_axis_layer_size(units_overlay_visible)

    def _create_overlay(self) -> None:
        """Create the units overlay UI.

        Args:
            viewport: The viewport to create overlay in
        """
        self._adjust_cam_axis_layer_size(self._overlay_visible)

        direction = ui.Direction.BOTTOM_TO_TOP
        self._root = ui.Stack(direction)
        with self._root:
            with ui.Stack(ui.Direction.BOTTOM_TO_TOP):
                with ui.Stack(ui.Direction.LEFT_TO_RIGHT, height=self.UNIT_TEXT_HEIGHT):
                    with ui.HStack():
                        ui.Spacer(width=self.UNIT_TEXT_HORIZ_OFFSET)
                        self._units_ui_ctrl = ui.Button(
                            self._units_text if self._units_text else "?",
                            width=self.UNIT_TEXT_WIDTH,
                            height=self.UNIT_TEXT_HEIGHT,
                            style={
                                "Button": {"background_color": cl.viewport_menubar_background},
                                "Button.Label": {"color": cl.viewport_menubar_light},
                                # TODO change to default or appropriate color(s) when we support on-click actions:
                                "Button:hovered": {"background_color": cl.viewport_menubar_background},
                                "Button:pressed": {"background_color": cl.viewport_menubar_background},
                            },
                            clicked_fn=self._unit_overlay_button_clicked,
                        )
                        ui.Spacer()
                ui.Spacer()

    def _unit_overlay_button_clicked(self) -> None:
        """Handle unit overlay button clicks."""
        pass  # TODO implement once we support on-click actions

    def _on_change_info_path(self, path: str) -> None:
        """Handle stage info path changes.

        Args:
            path: Changed path
        """
        self._refresh_units()

    def _register_objects_changed_listener(self) -> None:
        """(Re)register a Tf.Notice listener on the current stage so any change to
        stage-level metadata at the absolute root (e.g. metersPerUnit) refreshes the
        unit overlay."""
        self._revoke_objects_changed_listener()
        stage = omni.usd.get_context().get_stage()
        if stage:
            self._objects_changed_listener = Tf.Notice.Register(
                Usd.Notice.ObjectsChanged, self._on_stage_objects_changed, stage
            )

    def _revoke_objects_changed_listener(self) -> None:
        """Revoke the Tf.Notice listener if it was registered."""
        if self._objects_changed_listener:
            self._objects_changed_listener.Revoke()
            self._objects_changed_listener = None

    def _on_stage_objects_changed(self, notice: "Usd.Notice.ObjectsChanged", sender: object) -> None:
        """Refresh units when the absolute root path is in either the resynced or
        changed-info-only path sets — this is where stage-level metadata changes are
        reported. If metersPerUnit actually changed on a non-empty stage, also warn
        the user that existing geometry is not auto-converted."""
        abs_root = Sdf.Path.absoluteRootPath
        if abs_root not in notice.GetChangedInfoOnlyPaths() and abs_root not in notice.GetResyncedPaths():
            return

        stage = omni.usd.get_context().get_stage()
        new_mpu = UsdGeom.GetStageMetersPerUnit(stage) if stage else None
        old_mpu = self._last_known_mpu

        if (
            stage
            and new_mpu is not None
            and old_mpu is not None
            and not self._mpu_equal(old_mpu, new_mpu)
            and self._is_stage_non_empty(stage)
        ):
            new_unit = self._mpu_to_unit_label(new_mpu)
            # Only warn when the new value resolves to one of our known unit presets.
            # Intermediate slider values would otherwise spam a warning on every drag tick.
            if new_unit != "?":
                self._post_unit_change_warning(new_unit)

        self._refresh_units()

    def _show_overlay_changed(self, item: str, event_type: carb.settings.ChangeEventType) -> None:
        """Handle overlay visibility changes.

        Args:
            item: Changed settings item
            event_type: Type of change event
        """
        if event_type == carb.settings.ChangeEventType.CHANGED:
            self._overlay_visible = carb.settings.get_settings().get_as_bool(
                get_per_viewport_setting_path(self._viewport_api_id, METRICS_ASSEMBLER_HUD_SETTING_SUFFIX)
            )

            self.visible = self._overlay_visible

            # save the value to persistent settings
            viewport_persistent_setting_path = get_persistent_per_viewport_setting_path(
                self._viewport_api_id, METRICS_ASSEMBLER_HUD_SETTING_SUFFIX
            )
            carb.settings.get_settings().set_bool(viewport_persistent_setting_path, self._overlay_visible)

            # This method is called by ChangeSetting Kit command and it prevents _adjust_cam_axis_layer_size from
            # working properly (model and settings chain events of change-subscriptions at the core of the issue).
            # Calling it out of this subscription one frame later fixes the issue.
            asyncio.ensure_future(self._adjust_cam_axis_layer_size_async(self._overlay_visible))

    def _on_stage_open_event(self) -> None:
        """Handle stage open events."""
        # Reset so the first refresh on the newly-opened stage just seeds the baseline
        # without firing the "units changed" warning.
        self._last_known_mpu = None
        self._register_objects_changed_listener()
        self._refresh_units()

    def get_distance_units(self, stage: Usd.Stage) -> str:
        """Get distance units for a stage.

        Args:
            stage: USD stage to get units from

        Returns:
            str: Unit string or empty if not found
        """
        if not stage:
            return ""
        mpu = UsdGeom.GetStageMetersPerUnit(stage)
        epsilon = self.EPSILON
        for unit, known_mpu in zip(self.KNOWN_UNITS, self.KNOWN_MPU):
            if abs(mpu - known_mpu) < known_mpu * epsilon:
                return unit
        return ""

    def _refresh_units(self) -> None:
        """Refresh the displayed units based on current stage."""
        stage = omni.usd.get_context().get_stage()
        self._units_text = self.get_distance_units(stage)
        if stage:
            self._last_known_mpu = UsdGeom.GetStageMetersPerUnit(stage)

        if self._units_ui_ctrl:
            if self._units_text:
                self._units_ui_ctrl.text = self._units_text
                self._units_ui_ctrl.visible = True
            else:
                self._units_ui_ctrl.visible = False

    @staticmethod
    def _mpu_equal(a: float, b: float) -> bool:
        """Tolerance-based equality for metersPerUnit comparisons."""
        if a == 0.0 or b == 0.0:
            return a == b
        return abs(a - b) <= max(abs(a), abs(b)) * 1e-6

    def _mpu_to_unit_label(self, mpu: float) -> str:
        """Convert a metersPerUnit value to its friendly unit label (cm, dm, m, ...).
        Returns '?' if the value doesn't match a known unit."""
        epsilon = self.EPSILON
        for unit, known_mpu in zip(self.KNOWN_UNITS, self.KNOWN_MPU):
            if abs(mpu - known_mpu) < known_mpu * epsilon:
                return unit
        return "?"

    @staticmethod
    def _is_stage_non_empty(stage: Usd.Stage) -> bool:
        """A stage is 'non-empty' if its pseudo-root has any children. Matches the
        intent of the bug discussion: if the user has opened or authored any content,
        a unit-change warning is appropriate because positions/sizes are not auto-converted."""
        if not stage:
            return False
        return any(True for _ in stage.GetPseudoRoot().GetAllChildren())

    def _post_unit_change_warning(self, new_unit: str) -> None:
        """Toast (WARNING) + log to make it clear that only the unit metadata is updated;
        existing geometry is not auto-converted, so positions and sizes may now be wrong."""
        message = (
            f"Stage units changed to: '{new_unit}'.\n"
            "Object positions and sizes are NOT auto-converted.\n"
            "Existing geometry may now be at the wrong scale.\n"
            "Use omni.usd.metrics.assembler (change_stage_units) to convert geometry."
        )
        carb.log_warn(message)
        try:
            import omni.kit.notification_manager as nm

            nm.post_notification(
                message,
                status=nm.notification_info.NotificationStatus.WARNING,
                duration=8,
            )
        except Exception:
            # Notification manager may not be loaded; the carb.log_warn above still records the event.
            pass

    def destroy(self) -> None:
        """Clean up resources."""
        self._revoke_objects_changed_listener()
        self._stage_event_sub = []
        self._settings_subs = []
        self._change_info_path_subscriptions = []

        if self._overlay_visible:
            self._adjust_cam_axis_layer_size(False)

        if self._units_ui_ctrl:
            self._units_ui_ctrl.destroy()
            self._units_ui_ctrl = None
        if self._root:
            self._root.clear()
            self._root.destroy()
            self._root = None

    @property
    def visible(self) -> bool:
        """Get overlay visibility.

        Returns:
            bool: Whether overlay is visible
        """
        return self._root.visible

    @visible.setter
    def visible(self, value: bool) -> None:
        """Set overlay visibility.

        Args:
            value (bool): Visibility to set
        """
        self._root.visible = value

    @property
    def categories(self) -> list[str]:
        """Get view categories.

        Returns:
            list: List of category strings
        """
        return ["hud"]

    @property
    def name(self) -> str:
        """Get view name.

        Returns:
            str: View name
        """
        return "MetricsAssembler"
