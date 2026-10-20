# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["SectionScene"]

import carb.settings
import omni.kit.app
import omni.ui as ui
from omni.kit.viewport.utility import get_active_viewport_window
from omni.ui import scene as sc

from ..common import (
    SECTION_COLOR,
    SECTION_DIRECTION_TOP,
    SECTION_HOVER,
    SETTING_SECTION_DIRECTION,
    SETTING_SECTION_ENABLED,
    SectionManager,
    get_data_path,
)
from .section_manipulator import SectionManipulator
from .section_model import SectionModel

ICON_SIZE = 32
ICON_OFFSET = 100


class SectionScene:
    """The window with the manupulator"""

    def __init__(self, ext_id: str, model: SectionModel, **kwargs):
        self._ext_id = ext_id
        self._settings = carb.settings.get_settings()
        self._section_model = model
        self._manipulator = None
        self._viewport_window = get_active_viewport_window()
        self.detachable = False
        self._scene_view = None

        self._cut_direction_setting_tp = omni.kit.app.SettingChangeSubscription(
            SETTING_SECTION_DIRECTION, lambda *_: self._on_section_direction_changed()
        )

        self.__build_window()

    @property
    def viewport_api(self):
        return self._viewport_window.viewport_api if self._viewport_window else None

    def destroy(self):
        if self._manipulator:
            self._manipulator.destroy()
            self._manipulator = None

        self._section_model = None
        self._settings = None
        self._cut_direction_setting_tp = None

        if self._viewport_window and self._scene_view:
            self._viewport_window.viewport_api.remove_scene_view(self._scene_view)

        if self._scene_view:
            self._scene_view.destroy()
            self._scene_view = None

        self._viewport_window = None

    def __build_window(self):
        """Called to build the widgets of the window"""
        self.frame = self._viewport_window.get_frame(self._ext_id)
        with self.frame:
            self._scene_view = sc.SceneView()
            with self._scene_view.scene:
                self._manipulator = SectionManipulator(model=self._section_model, viewport_window=self._viewport_window)

            self._viewport_window.viewport_api.add_scene_view(self._scene_view)

    def show(self, visible: bool):
        self.frame.visible = visible
        if self._manipulator:
            self._manipulator.show(visible)

    def show_section_gizmo(self, value):
        if self._manipulator:
            self._manipulator.show_gizmo(value)

    def _on_section_direction_changed(self):
        if self._section_model:
            self._section_model.update_section_plane()
