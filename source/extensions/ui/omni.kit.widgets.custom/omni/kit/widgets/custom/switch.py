# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path

from omni import ui

from .constant import COLORS, MouseKey
from .style import get_ui_style

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("icons")

DEFAULT_SWITCH_WIDTH = 30
DEFAULT_SWITCH_HEIGHT = 30


class Switch:
    def __init__(self, on=False, switch_fn=None, images=None, **kwargs):
        if images is None:
            self._on_image = f"{ICON_PATH}/Switch_On.svg"
            self._off_image = f"{ICON_PATH}/Switch_Off.svg"
        else:
            self._on_image = images[0]
            self._off_image = images[1]

        self._on_switch_fn = switch_fn
        self._status = on

        if "width" not in kwargs:
            kwargs["width"] = DEFAULT_SWITCH_WIDTH
        if "height" not in kwargs:
            kwargs["height"] = DEFAULT_SWITCH_HEIGHT

        self._icon = ui.Image(
            self._on_image if self._status else self._off_image,
            mouse_pressed_fn=lambda x, y, key, a: self._on_switch_clicked(key),
            **kwargs,
        )

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value
        if self._status:
            self._icon.source_url = self._on_image
        else:
            self._icon.source_url = self._off_image

    @property
    def enabled(self):
        return self._icon.enabled

    @enabled.setter
    def enabled(self, value):
        self._icon.enabled = value

    def set_tooltip(self, tooltip):
        self._icon.set_tooltip(tooltip)

    def _on_switch_clicked(self, button, *_):
        if button != MouseKey.LEFT:
            return

        # The switch is changed.
        self._set_status(not self._status)

    def _set_status(self, status):
        if self._on_switch_fn:
            succ = self._on_switch_fn(status)
            if succ is not None and not succ:
                # do not change status
                return

        self.status = status


class SwitchOrCheckbox:
    def __init__(self, status=False, changed_fn=None, **kwargs):
        self._style = get_ui_style()
        if self._style == "NvidiaLight":
            self._switch = Switch(status, changed_fn, **kwargs)
        else:
            if "height" not in kwargs:
                widghet_height = 20
            else:
                widghet_height = kwargs["height"]
            with ui.VStack(width=0):
                ui.Spacer()
                self._checkbox = ui.CheckBox(height=widghet_height)
                ui.Spacer()
            self._changed_fn = changed_fn
            self._checkbox.model.set_value(status)
            self._checkbox.model.add_value_changed_fn(self._on_changed)

    @property
    def status(self):
        if self._style == "NvidiaLight":
            return self._switch.status
        else:
            return self._checkbox.model.get_value_as_bool()

    @status.setter
    def status(self, value):
        if self._style == "NvidiaLight":
            self._switch.status = value
        else:
            self._checkbox.model.set_value(value)

    @property
    def enabled(self):
        if self._style == "NvidiaLight":
            return self._switch.enabled
        else:
            return self._checkbox.enabled

    @enabled.setter
    def enabled(self, value):
        if self._style == "NvidiaLight":
            self._switch.enabled = value
        else:
            self._checkbox.enabled = value

    def _on_changed(self, model):
        # The checkbox is changed.
        if self._changed_fn:
            self._changed_fn(model.get_value_as_bool())
