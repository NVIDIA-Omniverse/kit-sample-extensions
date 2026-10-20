# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path
from typing import Dict

import carb.settings
import omni.ui as ui
from omni.kit.widget.stage import AbstractStageColumnDelegate, StageColumnItem

from .payload_model import UsdPrimPayloadModel

FIELD_BACKGROUND = 0xFF23211F
FIELD_TEXT_COLOR_HIDDEN = 0x01000000
KIT_GREEN = 0xFF8A8777
BORDER_RADIUS = 1.5
LIGHT_BORDER_RADIUS = 3


class PayloadColumnDelegate(AbstractStageColumnDelegate):
    """The column delegate that represents the visibility column"""

    def __init__(self):
        super().__init__()
        self._settings = carb.settings.get_settings()
        self._style = self._settings.get("/persistent/app/window/uiStyle")
        if not self._style:
            self._style = "NvidiaDark"

        if self._style == "NvidiaLight":
            self.style_data = {
                "CheckBox::greenCheck": {"font_size": 10, "background_color": KIT_GREEN, "color": 0xFF23211F},
                "CheckBox::greenCheck_mixed": {
                    "font_size": 10,
                    "background_color": KIT_GREEN,
                    "color": FIELD_TEXT_COLOR_HIDDEN,
                    "border_radius": LIGHT_BORDER_RADIUS,
                },
            }
        else:
            self.style_data = {
                "CheckBox::greenCheck": {
                    "font_size": 10,
                    "background_color": KIT_GREEN,
                    "color": FIELD_BACKGROUND,
                    "border_radius": BORDER_RADIUS,
                },
                "CheckBox::greenCheck_mixed": {
                    "font_size": 10,
                    "background_color": KIT_GREEN,
                    "color": FIELD_TEXT_COLOR_HIDDEN,
                    "border_radius": BORDER_RADIUS,
                },
            }

        self.__checkbox_model: Dict[Path, UsdPrimPayloadModel] = {}

    def destroy(self):
        self.__checkbox_model = {}

    @property
    def initial_width(self):
        """The width of the column"""
        return ui.Pixel(54)

    def build_header(self):
        """Build the header"""
        with ui.HStack():
            ui.Spacer(width=10)
            ui.Label("Payload", name="payload_header", style_type_name_override="TreeView.Header")

    async def build_widget(self, item: StageColumnItem):
        """Build the eye widget"""
        if not item or not item.stage:
            return

        prim = item.stage.GetPrimAtPath(item.path)
        if not prim or not prim.IsValid():
            return

        if not prim.GetPrimIndex().hasAnyPayloads:
            return

        if item.path not in self.__checkbox_model:
            self.__checkbox_model[item.path] = UsdPrimPayloadModel(item.stage, item.path)

        with ui.ZStack(height=20, style=self.style_data):
            with ui.HStack():
                ui.Spacer()
                with ui.VStack():
                    ui.Spacer()
                    self._checkbox = ui.CheckBox(name="greenCheck", model=self.__checkbox_model[item.path])
                    ui.Spacer()
                ui.Spacer()
            # Min size
            ui.Spacer(width=40)

        # Check if the payload exists
        model = self.__checkbox_model[item.path]
        if model and not model.valid_payload and prim.IsLoaded():
            self._checkbox.set_style({"background_color": 0xFF6F72FF})
