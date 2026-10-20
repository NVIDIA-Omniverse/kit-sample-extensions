# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.usd as ou
from omni.ui.scene import Matrix44
from pxr import Gf

from ..common import Singleton
from .section_model import SectionModel
from .section_scene import SectionScene


@Singleton
class SectionTool:
    def __init__(self):
        self._model = SectionModel()
        self._scene = None

    def __del__(self):  # pragma: no cover
        self.destroy()

    def destroy(self):
        if self._scene:
            self._scene.destroy()
        # Release the model's stage listeners with the extension; otherwise they outlive it and fire when the
        # stage closes later in app shutdown.
        if self._model:
            self._model.destroy()

    def reset(self):
        self._model.refresh()

    # TODO: Suspect unused code; remove if so
    @property
    def visible(self):  # pragma: no cover
        return self._scene is not None

    @property
    def scene(self):
        return self._scene

    # TODO: This needs a refactor
    def set_visibility(self, value: bool, ext_id: str) -> None:
        if value:
            if not self._scene:
                self._scene = SectionScene(ext_id, self._model)

        if self._scene:
            self._scene.show(value)
            self.show_section_gizmo(value)

    def show_section_gizmo(self, value: bool):
        if self._scene:
            self._scene.show_section_gizmo(value)
