# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Optional

from omni import ui

from .style import ICON_PATH, UI_STYLES

DEFAULT_MESSAGE = "No asset is current selected.\nSelect an asset to see its materials here."


class EmptyNotification:
    """
    When no materials selected, show notification.
    """

    def __init__(self):
        self._container = ui.ZStack(style=UI_STYLES)
        with self._container:
            ui.Rectangle(style_type_name_override="EmptyNotification.Frame")
            with ui.VStack(spacing=10):
                ui.Spacer(height=10)
                with ui.HStack(height=0):
                    ui.Spacer()
                    ui.ImageWithProvider(
                        f"{ICON_PATH}/prim_dark@3x.png",
                        width=192,
                        height=192,
                        fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                        style_type_name_override="EmptyNotification.Image",
                    )
                    ui.Spacer()
                self._message_label = ui.Label(
                    "No asset is current selected.",
                    height=0,
                    alignment=ui.Alignment.CENTER,
                    style_type_name_override="EmptyNotification.Label",
                )
                self._suggestion_label = ui.Label(
                    "Select an asset to see its materials here.",
                    height=0,
                    alignment=ui.Alignment.CENTER,
                    style_type_name_override="EmptyNotification.Label",
                )

    @property
    def visible(self) -> bool:
        return self._container.visible

    @visible.setter
    def visible(self, value) -> None:
        self._container.visible = value

    def set_message(self, message: str = DEFAULT_MESSAGE) -> None:
        messages = message.split("\n")
        self._message_label.text = messages[0]
        self._suggestion_label.text = messages[1]
