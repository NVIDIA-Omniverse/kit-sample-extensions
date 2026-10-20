# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path
from typing import List

import carb
import carb.dictionary
import carb.settings
import omni.kit.app
import omni.kit.context_menu
from omni.kit.manipulator.tool.snap import SnapToolButton

from .toolbar_registry import get_toolbar_registry

TOOLS_ENABLED_SETTING_PATH = "/exts/omni.curve.manipulator/tools/enabled"


class CurveManipTools:
    def __init__(self):
        super().__init__()
        self._settings = carb.settings.get_settings()
        self._dict = carb.dictionary.get_dictionary()
        self._toolbar_reg = get_toolbar_registry()

        self._builtin_tool_classes = {
            "prim:0snap": SnapToolButton,
        }
        self._registered_tool_ids: List[str] = []

        self._sub = self._settings.subscribe_to_node_change_events(TOOLS_ENABLED_SETTING_PATH, self._on_setting_changed)
        if self._settings.get(TOOLS_ENABLED_SETTING_PATH) is True:
            self._register_tools()

    def __del__(self):
        self.destroy()

    def destroy(self):
        self._unregister_tools()
        if self._sub is not None:
            self._settings.unsubscribe_to_change_events(self._sub)
            self._sub = None

    def _register_tools(self):
        for id, tool_class in self._builtin_tool_classes.items():
            self._toolbar_reg.register_tool(tool_class, id)
            self._registered_tool_ids.append(id)

    def _unregister_tools(self):
        for id in self._registered_tool_ids:
            self._toolbar_reg.unregister_tool(id)

        self._registered_tool_ids.clear()

    def _on_setting_changed(self, item, event_type):
        enabled = self._dict.get(item)
        if enabled and not self._registered_tool_ids:
            self._register_tools()
        elif not enabled:
            self._unregister_tools()
