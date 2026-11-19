# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import Dict

from carb import settings
from omni.kit.viewport.window import ViewportWindow
from omni.usd import StageEventType

from .state_machine import StateMachine

"""
This class is abstracted from omni.kit.viewport.utility.disable_selection() providing a means
to manage the state without creating and deleting the same object over and over again.
"""


class SelectionStateManager:
    def __init__(self, viewport_window: ViewportWindow):
        self.__vp_window: ViewportWindow = viewport_window
        self.__settings = settings.get_settings()
        self.__layers: Dict = {}

        ctx_menu_enabled = self.__settings.get("/exts/omni.kit.window.viewport/showContextMenu")
        self.__ctx_menu_restore = ctx_menu_enabled if ctx_menu_enabled is not None else True

        self._open_sub = StateMachine().subscribe_to_stage_event(self.store_layers, StageEventType.OPENED)

        self.store_layers()

    def __del__(self):
        self.restore()
        for key in self.__layers:
            self.__layers[key] = None

    @property
    def enabled(self) -> bool:
        sel_layer = self.__layers["Selection"]
        ctx_layer = self.__layers["ContextMenu"]

        if sel_layer and ctx_layer:
            return sel_layer.visible and ctx_layer.visible

        # For the case [USD-PRESENTER] that we don't have a context menu layer
        if sel_layer is None:
            return False
        return sel_layer.visible

    @enabled.setter
    def enabled(self, value: bool) -> None:
        # In review mode we currently do not allow selection, so we have to hardcode it here
        if self.__settings.get_as_string("/app/application_mode").lower() == "review":
            return

        self.__settings.set("/exts/omni.kit.window.viewport/showContextMenu", value)

        for key in self.__layers:
            item = self.__layers[key]
            if item is not None and hasattr(item, "visible"):
                item.visible = value

    def store_layers(self):
        self.__layers: Dict = {
            "Selection": self.__vp_window._find_viewport_layer("Selection", category="manipulator"),
            "ContextMenu": self.__vp_window._find_viewport_layer("ContextMenu", category="manipulator"),
        }

    def restore(self):
        """
        Restores the viewport layer states to the original settings.
        """

        self.store_layers()
        self.enabled = True

        # Override the enabled setting of show context menu to its default
        if self.enabled:
            self.__settings.set("/exts/omni.kit.window.viewport/showContextMenu", self.__ctx_menu_restore)
