# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
import carb.settings
from omni import ui
from omni.kit.widget.settings import create_setting_widget
from omni.kit.window.preferences import PreferenceBuilder, SettingType

from .style import PREFERENCE_PAGE_STYLES

TELEPORT_FILTER_KEYWORD = "/persistent/exts/omni.kit.tool.teleport/keyWord"
TELE_BEAM_VISIBLE = "/exts/omni.kit.tool.teleport/beamVisible"
TELEPORT_RING_MANIPULATOR_VISIBLE = "/exts/omni.kit.tool.teleport/ringManipulatorVisible"
TELEPORT_RING_MANIPULATOR_FIXED_SIZE = "/exts/omni.kit.tool.teleport/ringManipulatorFixedSize"
TELEPORT_RING_MANIPULATOR_SCALE = "/exts/omni.kit.tool.teleport/ringManipulatorScale"
TELEPORT_RING_MANIPULATOR_MIN_SIZE = "/exts/omni.kit.tool.teleport/ringManipulatorMinSize"
TELEPORT_RING_MANIPULATOR_MAX_SIZE = "/exts/omni.kit.tool.teleport/ringManipulatorMaxSize"
from .teleport_widget import MAX_SLOPE_ANGLE_PATH


class TeleportPage(PreferenceBuilder):
    """
    Represent a pereference page to show and edit environment settings.
    """

    def __init__(self):
        super().__init__("Navigation")
        self._settings = carb.settings.get_settings()
        self._models = []
        self._widgets = []

        saved_settings = [
            TELEPORT_FILTER_KEYWORD,
        ]

        # save default setting, make reset button work
        for setting in saved_settings:
            value = self._settings.get(setting)
            if value is None:
                if setting.startswith("/persistent"):
                    default_setting = setting[len("/persistent") :]
                    value = self._settings.get(default_setting)
            self._settings.set(setting, value)

    def destroy(self):
        pass

    def _create_setting_widget_with_reset(
        self, label_name: str, setting_path: str, setting_type: SettingType, **kwargs
    ):
        vheight = 24
        if setting_type == SettingType.FLOAT or setting_type == SettingType.INT or setting_type == SettingType.STRING:
            vheight = 20
        with ui.HStack(height=vheight):
            label = ui.Label(label_name, style_type_name_override="Setting.Label", word_wrap=True, width=ui.Percent(50))
            widget, model = create_setting_widget(setting_path, setting_type, **kwargs)
            button = self._build_reset_button(setting_path)
        if widget:
            try:
                model = widget.model
                model.set_reset_button(button)

                self._widgets.append(widget)
                self._models.append(model)
            except:
                pass
            return widget

    def _build_reset_button(self, path) -> ui.Rectangle:
        with ui.VStack(width=15, height=20):
            ui.Spacer(height=5)
            with ui.ZStack(width=15, height=15):
                with ui.HStack(spacing=0):
                    ui.Spacer()
                    with ui.VStack(width=0):
                        ui.Spacer()
                        ui.Rectangle(width=5, height=5, style_type_name_override="Reset_invalid.Rect")
                        ui.Spacer()
                    ui.Spacer()
                btn = ui.Rectangle(
                    width=12, height=12, style_type_name_override="Reset.Rect", tooltip="Click to reset value"
                )
                btn.visible = False

            btn.set_mouse_pressed_fn(lambda x, y, m, w, p=path, b=btn: self._restore_defaults(path, b))
            ui.Spacer()
        return btn

    def _restore_defaults(self, path: str, button: ui.Widget = None) -> None:
        default_path = self._get_default_setting_path(path)
        default_value = self._settings.get(default_path)
        self._settings.set(path, default_value)
        if button:
            button.visible = False

    def build(self):
        with self.add_frame("Teleport"):
            with ui.VStack(spacing=2, height=0, style=PREFERENCE_PAGE_STYLES):
                self._build_teleport_settings()

    def _build_teleport_settings(self):
        self._filter_keyword_widget = self._create_setting_widget_with_reset(
            "Filter Keyword",
            TELEPORT_FILTER_KEYWORD,
            SettingType.STRING,
            style_type_name_override="Setting.Field",
        )
        self._toggle_beam = self._create_setting_widget_with_reset(
            "Show Beam",
            TELE_BEAM_VISIBLE,
            SettingType.BOOL,
        )

        self._max_slope_angle = self._create_setting_widget_with_reset(
            "Max Slope Angle",
            MAX_SLOPE_ANGLE_PATH,
            SettingType.FLOAT,
        )

        self._toggle_ring_manipulator_visible = self._create_setting_widget_with_reset(
            "Enable Gizmo",
            TELEPORT_RING_MANIPULATOR_VISIBLE,
            SettingType.BOOL,
        )

        self._toggle_ring_manipulator_fixed_size = self._create_setting_widget_with_reset(
            "Fixed Gizmo Size",
            TELEPORT_RING_MANIPULATOR_FIXED_SIZE,
            SettingType.BOOL,
        )

        self._toggle_ring_manipulator_scale = self._create_setting_widget_with_reset(
            "Gizmo Scale",
            TELEPORT_RING_MANIPULATOR_SCALE,
            SettingType.FLOAT,
        )

        self._toggle_ring_manipulator_min_size = self._create_setting_widget_with_reset(
            "Gizmo Min Size (Pixels)",
            TELEPORT_RING_MANIPULATOR_MIN_SIZE,
            SettingType.INT,
        )

        self._toggle_ring_manipulator_max_size = self._create_setting_widget_with_reset(
            "Gizmo Max Size (Pixels)",
            TELEPORT_RING_MANIPULATOR_MAX_SIZE,
            SettingType.INT,
        )
