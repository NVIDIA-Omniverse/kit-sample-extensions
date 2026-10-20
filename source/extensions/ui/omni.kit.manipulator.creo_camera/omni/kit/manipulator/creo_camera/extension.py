## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Creo Camera Manipulator Extension.

This extension uses Kit's public RegisterScene API to register a custom
pan-only camera manipulator into all viewports, and disables the default
camera manipulator to avoid conflicts.
"""

import omni.ext
from omni.kit.viewport.registry import RegisterScene
from omni.kit.viewport.utility import get_active_viewport_window

from .creo_camera_manipulator import CreoCameraFactory


class CreoCameraManipulatorExtension(omni.ext.IExt):
    """
    Extension that adds Creo-style camera manipulation to viewports.

    Uses RegisterScene API for registration, and _find_viewport_layer
    (semi-public API used in tests) to disable the default manipulator.
    """

    def __init__(self):
        super().__init__()
        # Keep lifecycle robust even if startup fails early or shutdown is called defensively.
        self._scene_registration = None
        self._cam_layer = None
        self._default_camera_visible = None

    def on_startup(self, ext_id):
        """
        Extension startup.

        Registers the Creo camera manipulator and disables default one.
        """
        # Reset state in case of restart.
        self._scene_registration = None
        self._cam_layer = None
        self._default_camera_visible = None

        # Register our Creo camera manipulator
        # This automatically adds it to all viewports!
        self._scene_registration = RegisterScene(CreoCameraFactory, "omni.kit.manipulator.creo_camera.CreoCamera")

        # Disable the default camera manipulator to avoid conflicts
        self._disable_default_camera_manipulator()

    def _disable_default_camera_manipulator(self):
        """
        Disable the default Kit camera manipulator.

        Uses _find_viewport_layer (semi-public API, used in Kit's own tests).
        """
        import omni.kit.viewport.window.events

        # Disable default mouse wheel zoom
        omni.kit.viewport.window.events.set_ui_delegate(None)

        viewport_window = get_active_viewport_window()
        if not viewport_window:
            return

        # Find the default Camera manipulator scene
        cam_layer = viewport_window._find_viewport_layer("Camera", "manipulator")
        if cam_layer:
            # Save original state for restoration
            self._default_camera_visible = cam_layer.visible
            self._cam_layer = cam_layer
            # Disable it
            cam_layer.visible = False
        else:
            self._default_camera_visible = None
            self._cam_layer = None

    def on_shutdown(self):
        """
        Extension shutdown.

        Unregister the Creo camera manipulator and restore default.
        """
        # Restore default camera manipulator
        if self._cam_layer and self._default_camera_visible is not None:
            self._cam_layer.visible = self._default_camera_visible

        # Unregister our scene (this removes it from all viewports)
        if self._scene_registration:
            self._scene_registration.destroy()
            self._scene_registration = None
