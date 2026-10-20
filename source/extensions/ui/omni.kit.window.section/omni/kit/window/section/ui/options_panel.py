# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from typing import Any, Union

import carb
import carb.settings
from omni import ui
from omni.kit.widgets.custom import ExpandPanel

from ..common import (
    SECTION_DIRECTION_TOP,
    SETTING_RTX_DEFAULT_SECTION_DIRECTION,
    SETTING_RTX_DEFAULT_SECTION_MANIPULATOR,
    SETTING_SECTION_DIRECTION,
    SETTING_SECTION_ENABLED,
    SETTING_SECTION_LIGHT,
    SETTING_SECTION_MANIPULATOR,
)
from .constant import PANEL_PADDING_INNER_X, PANEL_SPACING_Y

AXISES = ["X", "Y", "Z"]
ROTATION_DEGREES = ["5", "10", "15", "30", "45", "90"]
CUT_DIRECTIONS = ["-", "+"]


from omni.kit.widget.settings import (
    SettingsWidgetBuilder,
    SettingType,
    create_setting_widget,
    create_setting_widget_combo,
)


class SectionSettingsWidgetBuilder(SettingsWidgetBuilder):
    DEFAULT_SETTINGS = {
        SETTING_SECTION_DIRECTION: SECTION_DIRECTION_TOP,
        SETTING_SECTION_MANIPULATOR: True,
        SETTING_SECTION_ENABLED: False,
        SETTING_SECTION_LIGHT: True,
    }

    @classmethod
    def _get_default(cls, path: str) -> Any:
        if path in SectionSettingsWidgetBuilder.DEFAULT_SETTINGS:
            return SectionSettingsWidgetBuilder.DEFAULT_SETTINGS[path]
        else:  # pragma: no cover
            carb.log_error(f"No default setting for {path}")
            return None

    # TODO: Suspect unused code; remove if so
    @classmethod
    def _restore_defaults(cls, path: str, button=None) -> None:  # pragma: no cover
        default_setting = cls._get_default(path)
        carb.settings.get_settings().set(path, default_setting)
        if button:
            button.visible = False


class OptionsPanel(ExpandPanel):
    def __init__(self):
        section_default_direction = SectionSettingsWidgetBuilder._get_default(SETTING_SECTION_DIRECTION)
        section_default_manipulator = SectionSettingsWidgetBuilder._get_default(SETTING_SECTION_MANIPULATOR)
        section_default_enable = SectionSettingsWidgetBuilder._get_default(SETTING_SECTION_ENABLED)
        section_default_light = SectionSettingsWidgetBuilder._get_default(SETTING_SECTION_LIGHT)
        self._settings = carb.settings.get_settings()
        self._settings.set_default(SETTING_SECTION_MANIPULATOR, section_default_manipulator)
        self._settings.set_default(SETTING_SECTION_ENABLED, section_default_enable)
        self._settings.set_default(SETTING_SECTION_LIGHT, section_default_light)
        self._settings.set_default(SETTING_SECTION_DIRECTION, section_default_direction)
        self._settings.set_default(SETTING_RTX_DEFAULT_SECTION_DIRECTION, section_default_direction)
        self._settings.set_default(SETTING_RTX_DEFAULT_SECTION_MANIPULATOR, section_default_manipulator)
        super().__init__("Options", 0, True)

    def build_panel(self):
        with ui.VStack(spacing=PANEL_SPACING_Y):
            with ui.HStack():
                ui.Spacer(width=PANEL_PADDING_INNER_X)
                with ui.VStack(spacing=10):
                    self._add_setting(SettingType.BOOL, "Display Section Manipulator", SETTING_SECTION_MANIPULATOR)
                ui.Spacer(width=PANEL_PADDING_INNER_X)

    def _add_setting(
        self, setting_type, name: str, path: str, range_from=0, range_to=0, speed=1, has_reset=True, tooltip=""
    ):
        try:
            saved_checkbox_alignment = SettingsWidgetBuilder.checkbox_alignment
            saved_checkbox_alignment_set = SettingsWidgetBuilder.checkbox_alignment_set
            SettingsWidgetBuilder.checkbox_alignment = "left"
            SettingsWidgetBuilder.checkbox_alignment_set = True
        except AttributeError:
            saved_checkbox_alignment = SettingsWidgetBuilder._checkbox_alignment
            saved_checkbox_alignment_set = SettingsWidgetBuilder._checkbox_alignment_set
            SettingsWidgetBuilder._checkbox_alignment = "left"
            SettingsWidgetBuilder._checkbox_alignment_set = True

        with ui.HStack(skip_draw_when_clipped=True):
            SettingsWidgetBuilder._create_label(name, path, tooltip)
            widget, model = create_setting_widget(path, setting_type, range_from, range_to, speed)
            if has_reset:
                button = SectionSettingsWidgetBuilder._build_reset_button(path)
                model.set_reset_button(button)
                button.visible = self._settings.get(path) != SectionSettingsWidgetBuilder._get_default(path)

        try:
            SettingsWidgetBuilder.checkbox_alignment_set = saved_checkbox_alignment_set
            SettingsWidgetBuilder.checkbox_alignment = saved_checkbox_alignment
        except AttributeError:
            SettingsWidgetBuilder._checkbox_alignment_set = saved_checkbox_alignment_set
            SettingsWidgetBuilder._checkbox_alignment = saved_checkbox_alignment
        return widget
