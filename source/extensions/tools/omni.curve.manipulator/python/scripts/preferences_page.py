# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.ui as ui
from omni.kit.window.preferences import PreferenceBuilder
from pxr import UsdGeom

from .settings_constants import Constants


class Preferences(PreferenceBuilder):
    def __init__(self):
        super().__init__("Curve Tools")

    def build(self):
        with ui.VStack(height=0):
            with self.add_frame("Creation"):
                with ui.VStack():
                    self.create_setting_widget_combo(
                        'Default "purpose" for newly created UsdGeomBasisCurves',
                        Constants.DEFAULT_USDGEOM_BASISCURVE_PURPOSE_SETTING,
                        [
                            UsdGeom.Tokens.default_,
                            UsdGeom.Tokens.render,
                            UsdGeom.Tokens.proxy,
                            UsdGeom.Tokens.guide,
                        ],
                    )
