# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni import ui

from ..constants import PlaySettings
from ..style import PLAY_STYLES
from .setting_button import SettingButton


class PlayLoopButton(SettingButton):
    """
    Represent a button for playback loop.
    """

    def __init__(self, style=PLAY_STYLES, **kwargs):
        super().__init__(
            PlaySettings.LOOP,
            style=style,
            style_type_name_override="PlayLoopButton",
            tooltip="Set the playback loop",
            **kwargs,
        )

    def _on_clicked(self):
        self.model.set_value(not self.model.as_bool)

    def _on_value_changed(self, model: ui.AbstractValueModel):
        self.selected = model.as_bool
