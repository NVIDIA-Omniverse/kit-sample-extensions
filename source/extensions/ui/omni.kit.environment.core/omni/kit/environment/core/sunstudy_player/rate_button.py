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

PLAY_RATE = [1, 2, 4, 8]


class PlayRateButton(SettingButton):
    """Represent a button for playback speed."""

    def __init__(self, style=PLAY_STYLES, **kwargs):
        super().__init__(
            PlaySettings.RATE,
            style=style,
            style_type_name_override="PlayRateButton",
            tooltip="Set the playback rate",
            **kwargs,
        )

    def _on_clicked(self):
        if self.model.as_int in PLAY_RATE:
            index = PLAY_RATE.index(self.model.as_int)
            index = (index + 1) % len(PLAY_RATE)
        else:
            index = 0
        if self.model.as_int != PLAY_RATE[index]:
            self.model.set_value(PLAY_RATE[index])

    def _on_value_changed(self, model: ui.AbstractValueModel):
        self.name = f"rate_{model.as_int}x"
