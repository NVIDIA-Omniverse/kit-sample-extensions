# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.ui as ui
from omni.kit.window.preferences import PERSISTENT_SETTINGS_PREFIX, PreferenceBuilder, SettingType


class CameraManipPreferences(PreferenceBuilder):
    def __init__(self):
        super().__init__("Navigation")

    def build(self):
        with ui.VStack(height=0):
            with self.add_frame("Orbit"):
                with ui.VStack():
                    w = self.create_setting_widget(
                        "Maintain Distance to Focal Point",
                        PERSISTENT_SETTINGS_PREFIX
                        + "/exts/omni.kit.viewport.navigation.camera_manipulator/orbitMaintainDistanceToFocal",
                        SettingType.BOOL,
                        tooltip="Whether to maintain the camera distance to focal point when picking a new focal point.",
                    )
                    w.identifier = "maintain_distance_to_frame"

        # OMFP-2881: Add perspective camera FOV persistent setting for user specified default value.
        with ui.VStack(height=0):
            with self.add_frame("Camera"):
                with ui.VStack():
                    w = self.create_setting_widget(
                        "Focal Length",
                        PERSISTENT_SETTINGS_PREFIX + "/exts/omni.kit.viewport.navigation.camera_manipulator/fov",
                        SettingType.FLOAT,
                    )
                    w.identifier = "camera_focal_length"
