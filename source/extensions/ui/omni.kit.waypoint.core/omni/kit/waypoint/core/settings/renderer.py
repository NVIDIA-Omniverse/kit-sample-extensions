# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
from pxr import Usd

from .abstract_setting import AbstractWaypointSetting

WAYPOINT_ATTR_RENDERER = "render"


class RendererSetting(AbstractWaypointSetting):
    def __init__(self, edit_context: Usd.EditContext = None):
        super().__init__(edit_context)
        # Temporarily disable the properties in waypoint
        """
        self._render_param_paths = [
            "/rtx/pathtracing/maxBounces",  # 0
            "/rtx/pathtracing/maxSpecularAndTransmissionBounces",  # 1
            "/rtx/pathtracing/totalSpp",  # 2
            "/rtx/rendermode",  # 3
            "/app/renderer/resolution/multiplier",  # 4
            "/app/renderer/resolution/width",  # 5
            "/app/renderer/resolution/height",  # 6
            "/app/renderer/gpuSynchronization",  # 7
            "/rtx/shadows/denoiser/quarterRes",  # 8
            "/rtx/sceneDb/ambientLightColor",  # 9
            "/rtx/sceneDb/ambientLightIntensity",  # 10
            "/rtx/ambientOcclusion/rayLength",  # 11
            "/rtx/reflections/halfRes",  # 12
            "/rtx/reflections/maxReflectionBounces",  # 13
            "/rtx/translucency/reflectionCutoff",  # 14
            "/rtx/pathtracing/mgpu/enabled",  # 15
            "/renderer/eco_mode_enable",  # 16
            "/rtx/post/tonemap/op",  # 17
            "/rtx/post/colorcorr/enabled",  # 18
            "/rtx/post/colorcorr/outputMode",  # 19
            "/rtx/post/colorgrad/enabled",  # 20
            "/rtx/post/colorgrad/outputMode",  # 21
            "/rtx/reflections/enabled",  # 22
            "/rtx/shadows/enabled",  # 23
            "/rtx/translucency/enabled",  # 24
            "/rtx/ambientOcclusion/enabled",  # 25
            "/rtx/ambientOcclusion/temporalSqrtLength",  # 26
            "/rtx/indirectDiffuse/enabled",  # 27
            "/rtx/post/lensFlares/enabled",  # 28
            "/rtx/post/lensFlares/flareScale",  # 29
            "/rtx/post/chromaticAberration/enabled",  # 30
            "/rtx/post/chromaticAberration/strengthR",  # 31
            "/rtx/post/chromaticAberration/strengthG",  # 32
            "/rtx/post/chromaticAberration/strengthB",  # 33
            "/rtx/post/histogram/enabled",  # 34
            "/rtx/domeLight/baking/resolution",  # 35
            "/rtx/post/dof/enabled",  # 36
            "/rtx/post/dof/overrideEnabled",  # 37
            "/rtx/post/dof/viewUIEnabled",  # 38
            "/rtx/post/aa/op",  # 39
            "/rtx/directLighting/sampledLighting/enabled",  # 40
            "/rtx/directLighting/sampledLighting/samplesPerPixel",  # 41
            "/rtx/reflections/sampledLighting/enabled",  # 42
            "/rtx/indirectDiffuse/enabled",  # 43
            "/rtx/raytracing/cached/enabled",  # 44
            "/rtx/reflections/halfRes",  # 45
            "/rtx/renderpreset"  # Additional 1
        ]
        # """
        # self._render_param_paths = ["/rtx/renderpreset"]
        self._render_param_paths = [
            # Tone Mapping Settings
            "/rtx/post/tonemap/op",  # Tone Mapping Operator
            "/rtx/post/tonemap/maxWhiteLuminance",  # Max White Luminance (Modified Reinhard only)
            "/rtx/post/tonemap/whiteScale",  # White Scale Value (HableUc2 only)
            "/rtx/post/tonemap/irayReinhard/crushBlacks",  # Crush Blacks (Iray only)
            "/rtx/post/tonemap/irayReinhard/burnHighlights",  # Burn Highlights (Iray only)
            "/rtx/post/tonemap/irayReinhard/burnHighlightsPerComponent",  # Burn Highlights per Component (Iray only)
            "/rtx/post/tonemap/irayReinhard/burnHighlightsMaxComponent",  # Burn Highlights max Component (Iray only)
            "/rtx/post/tonemap/irayReinhard/saturation",  # Saturation (Iray only)
            "/rtx/post/tonemap/enableSrgbToGamma",  # SRGB to Gamma Conversion (not Clamp)
            "/rtx/post/tonemap/filmIso",  # Film ISO
            "/rtx/post/tonemap/exposureTime",  # Camera Exposure Time
            "/rtx/post/tonemap/fNumber",  # F-stop
            "/rtx/post/tonemap/responsivity",  # Responsivity
            "/rtx/post/tonemap/whitepoint",  # White Point
            "/rtx/post/tonemap/colorMode",  # Tone Mapping Color Space
            "/rtx/post/tonemap/wrapValue",  # Wrap Value
            "/rtx/post/tonemap/dither",  # Dither strength
            # Auto Exposure
            "/rtx/post/histogram/filterType",  # Histogram Filter
            "/rtx/post/histogram/tau",  # Adaptation Speed
            "/rtx/post/histogram/whiteScale",  # White Point Scale
            "/rtx/post/histogram/useExposureClamping",  # Exposure Value Clamping
            "/rtx/post/histogram/minEV",  # Minimum Value (when clamping enabled)
            "/rtx/post/histogram/maxEV",  # Maximum Value (when clamping enabled)
            # Color Grading
            "/rtx/post/colorgrad/mode",  # Mode
            "/rtx/post/colorgrad/outputMode",  # Output Color Space (ACES mode only)
            "/rtx/post/colorgrad/blackpoint",  # Black Point
            "/rtx/post/colorgrad/whitepoint",  # White Point
            "/rtx/post/colorgrad/contrast",  # Contrast
            "/rtx/post/colorgrad/lift",  # Lift
            "/rtx/post/colorgrad/gain",  # Gain
            "/rtx/post/colorgrad/multiply",  # Multiply
            "/rtx/post/colorgrad/offset",  # Offset
            "/rtx/post/colorgrad/gamma",  # Gamma
            # Bloom (FFT Bloom)
            "/rtx/post/lensFlares/flareScale",  # Scale
            "/rtx/post/lensFlares/cutoffPoint",  # Cutoff Point
            "/rtx/post/lensFlares/cutoffFuzziness",  # Cutoff Fuzziness
            "/rtx/post/lensFlares/alphaExposureScale",  # Alpha channel scale
            "/rtx/post/lensFlares/energyConstrainingBlend",  # Energy Constrained
            "/rtx/post/lensFlares/physicalSettings",  # Physical Model
            "/rtx/post/lensFlares/apertureShapeCircular",  # Circular Aperture (physical model)
            "/rtx/post/lensFlares/blades",  # Blades (physical model, non-circular)
            "/rtx/post/lensFlares/apertureRotation",  # Aperture Rotation (physical model)
            "/rtx/post/lensFlares/sensorDiagonal",  # Sensor Diagonal (physical model)
            "/rtx/post/lensFlares/sensorAspectRatio",  # Sensor Aspect Ratio (physical model)
            "/rtx/post/lensFlares/fNumber",  # F-stop (physical model)
            "/rtx/post/lensFlares/focalLength",  # Focal Length (mm) (physical model)
            "/rtx/post/lensFlares/noiseStrength",  # Noise Strength (physical model)
            "/rtx/post/lensFlares/dustStrength",  # Dust Strength (physical model)
            "/rtx/post/lensFlares/scratchStrength",  # Scratch Strength (physical model)
            "/rtx/post/lensFlares/spectralBlurSamples",  # Spectral Blur Samples (physical model)
            "/rtx/post/lensFlares/spectralBlurIntensity",  # Blur Scaling (physical model)
            "/rtx/post/lensFlares/spectralBlurWavelengthRange",  # Blur Wavelength range (nm) (physical model)
            "/rtx/post/lensFlares/haloFlareRadius",  # Halo Radius (non-physical model)
            "/rtx/post/lensFlares/haloFlareFalloff",  # Halo Flare Falloff (non-physical model)
            "/rtx/post/lensFlares/haloFlareWeight",  # Halo Flare Weight (non-physical model)
            "/rtx/post/lensFlares/anisoFlareFalloffY",  # Aniso Falloff Y (non-physical model)
            "/rtx/post/lensFlares/anisoFlareFalloffX",  # Aniso Falloff X (non-physical model)
            "/rtx/post/lensFlares/anisoFlareWeight",  # Aniso Flare Weight (non-physical model)
            "/rtx/post/lensFlares/isotropicFlareFalloff",  # Isotropic Flare Falloff (non-physical model)
            "/rtx/post/lensFlares/isotropicFlareWeight",  # Isotropic Flare Weight (non-physical model)
            "/rtx/post/lensFlares/debugVisMode",  # Visualization
            "/rtx/renderpreset",  # Additional 1
        ]
        self._settings = carb.settings.get_settings()

    def get_name(self):
        return "Render Settings"

    def is_dirty(self):
        if not self.valid:
            return False

        for param in self._render_param_paths:
            value = self._settings.get(param)
            if param in self._data:
                if not self.equal_data(value, self._data[param]):
                    return True
            elif value is not None:
                return True
        return False

    def create(self, valid: bool = True):
        super().create(valid)
        if not valid:
            return

        # Collect data from render settings
        self._data.clear()
        for param in self._render_param_paths:
            value = self._settings.get(param)
            if value is not None:
                self._data[param] = value

    def recall(self, prim: Usd.Prim):
        if not self.valid:
            return
        # Pull/apply current data to renderer/settingsd
        """
        # Temporarily disable renderer properties recall
        rtx_render_mode = self._settings.get("/rtx/rendermode")
        if rtx_render_mode != self._data["/rtx/rendermode"]:
            if self._data["/rtx/rendermode"] == "iray":
                # Entering iray renderer
                iv = omni.kit.viewport.acquire_viewport_interface()
                if iv:
                    viewport_window = iv.get_viewport_window(None)
                    viewport_window.set_active_hydra_engine("iray")
            elif rtx_render_mode == "iray":
                # Leaving iray renderer
                iv = omni.kit.viewport.acquire_viewport_interface()
                if iv:
                    viewport_window = iv.get_viewport_window(None)
                    # viewport_window.set_active_hydra_engine("rtx")
                    viewport_window.set_active_hydra_engine("rtx")
        """

        for param in self._render_param_paths:
            value = self._data.get(param)
            if value is not None:
                self._settings.set(param, value)

    def save_to_usd(self, prim: Usd.Prim) -> None:
        self._save_data_to_usd(prim, WAYPOINT_ATTR_RENDERER)

    def load_from_usd(self, prim: Usd.Prim) -> bool:
        return self._load_data_from_usd(prim, WAYPOINT_ATTR_RENDERER)
