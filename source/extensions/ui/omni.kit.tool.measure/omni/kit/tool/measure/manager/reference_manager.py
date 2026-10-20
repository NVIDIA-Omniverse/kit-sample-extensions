# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import cast

import omni.usd as ou
from omni.kit.usd.layers import Layers, get_layers
from pxr import Usd


class ReferenceManager:
    def __singleton_init__(self):

        # Sidecar
        try:
            from omni.usd_presenter.sidecar import SideCarData, register_data

            self.__sidecar: SideCarData = register_data("Measure")
        except ImportError:
            self.__sidecar = None

        # Selection State
        self._selection_state = None
        # Selection Group
        self._selection_group: int = ou.get_context().register_selection_group()
        ou.get_context().set_selection_group_outline_color(self._selection_group, [1.0, 1.0, 0.0, 1.0])
        ou.get_context().set_selection_group_shade_color(self._selection_group, [1.0, 1.0, 0.0, 0.125])
        # Gestures
        self._gesture_screen = None

        # UI PANEL
        self._ui_panel = None
        self._ui_global_panel = None
        self._ui_placement_panel = None
        self._ui_display_panel = None
        self._ui_manage_panel = None

        # Measurement Scene
        self._measure_scene: "MeasureScene" = None

    def __new__(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
            cls._instance.__singleton_init__()
        return cls._instance

    @property
    def edit_context(self) -> Usd.EditContext:
        _ctx = ou.get_context()
        target = Usd.EditContext(_ctx.get_stage(), Usd.EditTarget(None))

        layers = cast(Layers, get_layers(_ctx))
        if layers.get_live_syncing().is_in_live_session():
            return target

        return self.__sidecar.edit_context if self.__sidecar else target

    @property
    def selection_state(self):
        return self._selection_state

    @property
    def selection_group(self):
        return self._selection_group

    @selection_state.setter
    def selection_state(self, value):
        self._selection_state = value

    @property
    def gesture_screen(self):
        return self._gesture_screen

    @gesture_screen.setter
    def gesture_screen(self, value):
        self._gesture_screen = value

    @property
    def ui_panel(self):
        return self._ui_panel

    @ui_panel.setter
    def ui_panel(self, panel):
        self._ui_panel = panel

    @property
    def ui_global_panel(self):
        return self.ui_global_panel

    @ui_global_panel.setter
    def ui_global_panel(self, panel):
        self._ui_global_panel = panel

    @property
    def ui_placement_panel(self):
        return self._ui_placement_panel

    @ui_placement_panel.setter
    def ui_placement_panel(self, panel):
        self._ui_placement_panel = panel

    @property
    def ui_display_panel(self):
        return self._ui_display_panel

    @ui_display_panel.setter
    def ui_display_panel(self, panel):
        self._ui_display_panel = panel

    @property
    def ui_manage_panel(self):
        return self._ui_manage_panel

    @ui_manage_panel.setter
    def ui_manage_panel(self, panel):
        self._ui_manage_panel = panel

    @property
    def measure_scene(self):
        return self._measure_scene

    @measure_scene.setter
    def measure_scene(self, value):
        self._measure_scene = value
