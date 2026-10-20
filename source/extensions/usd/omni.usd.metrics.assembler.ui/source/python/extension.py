# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import carb.settings
import omni.ext
import omni.usd
from carb.eventdispatcher import get_eventdispatcher

from .constants import METRICS_ASSEMBLER_HUD_SETTING_SUFFIX
from .metricsAssemblerManager import MetricsAssemblerManager
from .tools import get_per_viewport_setting_path, get_viewport_defaults_setting_path


class MetricsAssemblerUI(omni.ext.IExt):
    def __init__(self):
        super().__init__()
        self._reg_viewport_layer = None
        self._metrics_assembler_viewport_menu = None
        self._metrics_assembler_manager = None
        self._preferences = None
        self._stage_event_sub = None

    def on_startup(self, ext_id):
        # set default hud viewport menu value
        settings = carb.settings.get_settings()
        settings.set_bool(get_viewport_defaults_setting_path(METRICS_ASSEMBLER_HUD_SETTING_SUFFIX), True)

        try:
            from omni import ui
            from omni.kit.viewport.menubar.core import CategoryStateItem
            from omni.kit.viewport.window import ViewportWindow
            from omni.kit.viewport.window.scene.scenes import CameraAxisLayer

            ui_enable = True
        except Exception as e:
            ui_enable = False

        if ui_enable:
            from omni.kit.viewport.registry import RegisterViewportLayer

            from .metricsAssemblerUnitsView import MetricsAssemblerUnitsView
            from .metricsAssemblerViewportMenu import MetricsAssemblerViewportMenu

            self._metrics_assembler_viewport_menu = MetricsAssemblerViewportMenu()
            self._reg_viewport_layer = RegisterViewportLayer(
                MetricsAssemblerUnitsView, "omni.usd.metrics.assembler.ui.MetricsAssemblerUnitsView"
            )
        else:
            self._metrics_assembler_viewport_menu = None
            self._reg_viewport_layer = None

        self._metrics_assembler_manager = MetricsAssemblerManager()
        try:
            import omni.kit.window.preferences.scripts.preferences_window as preferences_window

            from .settings import MetricsAssemblerPreferences

            self._preferences = preferences_window.register_page(MetricsAssemblerPreferences())
        except Exception as e:
            self._preferences = None

        self._stage_event_sub = [
            get_eventdispatcher().observe_event(
                observer_name="omni.usd.metrics.assembler.ui:MetricsAssemblerUI",
                event_name=omni.usd.get_context().stage_event_name(event),
                on_event=func,
            )
            for event, func in (
                (omni.usd.StageEventType.OPENED, lambda _: self._on_stage_open_event()),
                (omni.usd.StageEventType.CLOSED, lambda _: self._on_stage_close_event()),
            )
        ]

    def on_shutdown(self):
        if self._metrics_assembler_viewport_menu:
            self._metrics_assembler_viewport_menu.destroy()
            self._metrics_assembler_viewport_menu = None

        if self._reg_viewport_layer:
            self._reg_viewport_layer.destroy()
            self._reg_viewport_layer = None

        if self._metrics_assembler_manager:
            self._metrics_assembler_manager.on_shutdown()
            self._metrics_assembler_manager = None

        try:
            import omni.kit.window.preferences.scripts.preferences_window as preferences_window

            if self._preferences:
                preferences_window.unregister_page(self._preferences)
                self._preferences.on_shutdown()
                self._preferences = None
        except Exception:
            self._preferences = None

        self._stage_event_sub = None

    def _on_stage_open_event(self):
        if self._metrics_assembler_manager:
            self._metrics_assembler_manager.stage_opened(omni.usd.get_context().get_stage())

    def _on_stage_close_event(self):
        if self._metrics_assembler_manager:
            self._metrics_assembler_manager.stage_closed()
