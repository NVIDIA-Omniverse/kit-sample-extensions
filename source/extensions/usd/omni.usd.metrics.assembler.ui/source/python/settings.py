# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.metrics.assembler.core.bindings._metricsAssembler as metricsAssembler
from omni import ui
from omni.kit.widget.settings.settings_widget import SettingType, create_setting_widget, create_setting_widget_combo
from omni.kit.window.preferences.scripts.preferences_window import PreferenceBuilder

from .metricsAssemblerManager import MetricsAssemblerMode

BUTTON_HEIGHT: int = 30


def build_section(name: str, build_func: callable) -> None:
    """Build a collapsable UI section with consistent styling.

    Creates a collapsable frame with standard indentation and layout for preferences sections.

    Args:
        name (str): The display name for the section header
        build_func (callable): Function that builds the UI content within the section

    Returns:
        None
    """
    with ui.CollapsableFrame(name, height=0):
        with ui.HStack():
            ui.Spacer(width=20)
            with ui.VStack():
                build_func()


class MetricsAssemblerPreferences(PreferenceBuilder):
    """Class for building the Metrics Assembler preferences UI panel.

    Inherits from PreferenceBuilder to create a preferences page for configuring
    Metrics Assembler settings.
    """

    def __init__(self) -> None:
        """Initialize the preferences builder with default settings."""
        super().__init__("Metrics Assembler")
        self._widgets: list = []
        self._line_height: int = 20

    def on_shutdown(self) -> None:
        """Clean up resources when shutting down."""
        self._widgets = []

    def _add_setting_combo_and_label(self, name: str, path: str, items: dict, **kwargs) -> None:
        """Add a combo box setting with label to the preferences UI.

        Args:
            name (str): Display name for the setting
            path (str): Settings path for the combo box value
            items (dict): Dictionary mapping display names to setting values
            **kwargs: Additional arguments passed to create_setting_widget_combo
        """
        with ui.HStack(height=24):
            self.label(name)
            create_setting_widget_combo(path, items, **kwargs)

    def _add_setting_checkbox_and_label(self, name: str, path: str, **kwargs) -> None:
        """Add a checkbox setting with label to the preferences UI.

        Args:
            name (str): Display name for the setting
            path (str): Settings path for the checkbox value
            **kwargs: Additional arguments passed to create_setting_widget
        """
        with ui.HStack(height=self._line_height):
            self._widgets.append(create_setting_widget(path, SettingType.BOOL), **kwargs)
            # overpowering ui.Line from create_setting_widget to stay at ~zero width
            ui.Label(name, width=ui.Fraction(100))

    def _build_metrics_assembler_mode_setting(self) -> None:
        """Build the UI section for Metrics Assembler mode settings.

        Creates combo box and checkbox settings for configuring the Metrics
        Assembler operation mode and related options.
        """
        self._add_setting_combo_and_label(
            "Metrics Assembler Operation Mode",
            metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE,
            {
                "Disabled": MetricsAssemblerMode.DISABLED,
                "Warn": MetricsAssemblerMode.WARN,
                "Ask to Resolve": MetricsAssemblerMode.ASK,
                "Auto Resolve": MetricsAssemblerMode.AUTO,
            },
        )
        self._add_setting_checkbox_and_label(
            "Metrics Assembler Parameters Change Listener Enabled",
            metricsAssembler.SETTINGS_METRICS_ASSEMBLER_PARAMS_CHANGE_LISTENER_ENABLED,
        )
        self._add_setting_checkbox_and_label(
            "Metrics Assembler Conform To XformCommonAPI (do not add unitsResolve xformOps)",
            metricsAssembler.SETTINGS_METRICS_ASSEMBLER_CONFORM_TO_XFORM_COMMON_API,
        )

    def build(self) -> None:
        """Build the complete preferences UI panel.

        Creates the main UI layout and adds all settings sections.
        """
        with ui.VStack(height=0):
            build_section("General", self._build_metrics_assembler_mode_setting)
