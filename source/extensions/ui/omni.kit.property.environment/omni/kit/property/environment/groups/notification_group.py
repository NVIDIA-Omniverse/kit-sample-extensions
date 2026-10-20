# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from datetime import datetime

import omni.kit.app
from omni import ui
from omni.kit.environment.core import (
    EnvironmentProperties,
    PlayButton,
    PlayLoopButton,
    PlayRateButton,
    SunstudyTimeSlider,
    UsdModelBuilder,
    get_sunstudy_player,
)
from pxr import Sdf

from ..style import SLIDER_STYLE
from .calendar_window import CalendarWindow
from .property_group import AbstractPropertyGroup

IMAGE_BUTTON_STYLE = {
    "Rectangle::button": {"background_color": 0xFF343432},
    "Rectangle::button:selected": {"background_color": 0xFF292929},
    "Rectangle::button:hovered": {"border_width": 1, "border_color": 0xFF2F2F2F},
}


class NotificationGroup(AbstractPropertyGroup):
    def __init__(self):
        self._player = get_sunstudy_player()

        super().__init__("Dynamic sky")

    def destroy(self):
        super().destroy()

    def _build_widgets(self):
        with ui.VStack(height=0, spacing=8):
            ui.Label(
                "There is no Dynamic Sky in the stage. To use Sun Study Controls, add a Dynamic sky.",
                word_wrap=True,
                name="label",
            )
            with ui.HStack():
                ui.Spacer()
                ui.Button("Go to Dynamic Skies", width=80, clicked_fn=self._open_env_browser)
                ui.Spacer()

    def _open_env_browser(self):
        env_window = ui.Workspace.get_window("Environments")
        if env_window:
            env_window.visible = True

            async def __focus_env_window():
                await omni.kit.app.get_app().next_update_async()
                env_window.navigate_to_dynamic_skies()
                env_window.focus()

            asyncio.ensure_future(__focus_env_window())
