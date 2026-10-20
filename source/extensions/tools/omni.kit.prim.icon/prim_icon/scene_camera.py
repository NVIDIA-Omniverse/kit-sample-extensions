# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["CameraModel"]

from typing import List

import carb.eventdispatcher
import omni.usd
from omni.kit.viewport.utility import get_active_viewport_camera_path
from omni.ui import scene as sc
from pxr import Gf, Sdf, Tf, Usd, UsdGeom


class CameraModel(sc.AbstractManipulatorModel):  # pragma: no cover
    """
    The model that tracks the current USD camera and has two items
    'projection' and 'view' that represent the camera matrices.
    """

    def __init__(self):
        super().__init__()

        # Active camera
        self._camera_prim = None
        self._camera_path = None

        # Tracking the camera
        self._usd_context = omni.usd.get_context()
        stage = self._usd_context.get_stage()
        self._stage_listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._notice_changed, stage)
        self._stage_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            observer_name="omni.kit.prim.icon.scene_camera",
            event_name=self._usd_context.stage_event_name(omni.usd.StageEventType.OPENED),
            on_event=lambda _: self._on_stage_opened(),
        )

    def _on_stage_opened(self):
        self._stage_listener = None
        stage = self._usd_context.get_stage()
        self._stage_listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._notice_changed, stage)
        self._item_changed(None)

    def destroy(self):
        self._stage_sub = None
        self._stage_listener = None
        self._camera_prim = None
        self._camera_path = None
        super().destroy()

    def get_as_floats(self, item):
        """Called by SceneView to get projection and view matrices"""
        if item == self.get_item("projection"):
            return self._get_projection()
        if item == self.get_item("view"):
            return self._get_view()

    def _notice_changed(self, notice, stage):
        """Called by Tf.Notice"""
        for p in notice.GetChangedInfoOnlyPaths():
            if p.GetPrimPath() == self._camera_path:
                # If it's a camera, dirty the model and view will request new
                # matrices when it needs
                # Technically the view also changes when a parent of the
                # camera_path has changed transform; but for an example
                # it's fine.
                self._item_changed(None)

    @staticmethod
    def _flatten(transform):
        """Convert array[n][m] to array[n*m]"""
        # flatten the matrix by hand
        # USING LIST COMPREHENSION IS VERY SLOW (e.g. return [item for sublist
        # in transform for item in sublist]), which takes around 10ms.
        return [
            transform[0][0],
            transform[0][1],
            transform[0][2],
            transform[0][3],
            transform[1][0],
            transform[1][1],
            transform[1][2],
            transform[1][3],
            transform[2][0],
            transform[2][1],
            transform[2][2],
            transform[2][3],
            transform[3][0],
            transform[3][1],
            transform[3][2],
            transform[3][3],
        ]

    def _get_camera(self):
        """Returns the current camera's frustum"""
        if not self._camera_prim:
            # Get the camera prim
            self._camera_path = get_active_viewport_camera_path()
            stage = omni.usd.get_context().get_stage()
            if stage and self._camera_path:
                self._camera_prim = stage.GetPrimAtPath(self._camera_path)

        # Extract view and projection
        if self._camera_prim:
            return UsdGeom.Camera(self._camera_prim).GetCamera().frustum

    def _get_view(self) -> List[float]:
        """Returns the view matrix as a list"""
        frustum = self._get_camera()
        if frustum:
            view = frustum.ComputeViewMatrix()
        else:
            view = Gf.Matrix4d(1.0)
        return self._flatten(view)

    def _get_projection(self) -> List[float]:
        """Returns the projection matrix as a list"""
        frustum = self._get_camera()
        if frustum:
            projection = frustum.ComputeProjectionMatrix()
        else:
            projection = Gf.Matrix4d(1.0)
        return self._flatten(projection)
