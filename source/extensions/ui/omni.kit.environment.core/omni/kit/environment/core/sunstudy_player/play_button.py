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

import carb.settings
import omni.kit.app
from omni import ui
from omni.kit.notification_manager import NotificationButtonInfo, NotificationStatus, post_notification

from ..constants import PlaySettings
from ..style import PLAY_STYLES
from .player import SunstudyPlayer, SunstudySkyType
from .setting_button import SettingButton


class PlayButton(SettingButton):
    """Represent a button to start/stop playing."""

    def __init__(self, player: SunstudyPlayer, style=PLAY_STYLES, show_notification=True, **kwargs):
        if "enable" not in kwargs:
            kwargs["enabled"] = carb.settings.get_settings().get(PlaySettings.ENABLE)
        super().__init__(PlaySettings.PLAYING, style=style, style_type_name_override="PlayButton", **kwargs)

        self._player = player
        self._show_notification = show_notification

    def _on_clicked(self):
        if self.model.as_bool:
            self._player.stop()
        else:
            if not self._player.start():
                if self._show_notification:
                    button_infos = [
                        NotificationButtonInfo("Go to Dynamic Skies", on_complete=self._open_env_browser),
                        NotificationButtonInfo("Close", on_complete=None),
                    ]

                    if "presenter" in omni.kit.app.get_app().get_app_name().lower():
                        message = "Sun Study can only be used on scenes with a Dynamic Sky."
                        post_notification(message, status=NotificationStatus.INFO)
                        return

                    if self._player.sky_type == SunstudySkyType.NONE:
                        message = "Sun Study can only be used with a Dynamic Sky.\nThere is no Dynamic Sky now!"
                    else:
                        message = "Sun Study can only be used with a Dynamic Sky.\nWould you like to choose a Dynamic Sky from the Environment Browser?"
                    post_notification(
                        message, hide_after_timeout=0, status=NotificationStatus.INFO, button_infos=button_infos
                    )

    def _on_value_changed(self, model: ui.AbstractValueModel):
        self.checked = model.as_bool

    def _open_env_browser(self):
        env_window = ui.Workspace.get_window("Environments")
        if env_window:
            env_window.visible = True

            async def __focus_env_window():
                await omni.kit.app.get_app().next_update_async()
                env_window.navigate_to_dynamic_skies()
                env_window.focus()

            asyncio.ensure_future(__focus_env_window())
