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
from omni import ui
from omni.kit.window.preferences import PreferenceBuilder, SettingType

from .constants import (
    DEFAULT_TEMPLATE_PATH,
    PERSISTENT_MDL_RENDER_MODE,
    PERSISTENT_MDL_RENDER_SAMPLES,
    PERSISTENT_MDL_STDIN,
    PERSISTENT_MDL_TEMPLATE_PATH,
    PERSISTENT_USD_RENDER_MODE,
    PERSISTENT_USD_RENDER_SAMPLES,
    PERSISTENT_USD_STDIN,
    PERSISTENT_USD_TEMPLATE_PATH,
    SETTING_MDL_RENDER_MODE,
    SETTING_MDL_RENDER_SAMPLES,
    SETTING_MDL_STDIN,
    SETTING_MDL_TEMPLATE_PATH,
    SETTING_USD_RENDER_MODE,
    SETTING_USD_RENDER_SAMPLES,
    SETTING_USD_STDIN,
    SETTING_USD_TEMPLATE_PATH,
)

SETTING_TITLE = "Material Thumbnail"


# Preferences for Thumbnail Generation
class ThumbnailPage(PreferenceBuilder):
    def __init__(self):
        super().__init__(SETTING_TITLE)
        settings = carb.settings.get_settings()

        # MDL default settings
        mdl_template_path = settings.get(SETTING_MDL_TEMPLATE_PATH)
        if not mdl_template_path:
            # Default template is local file, cannot set in extension.toml
            mdl_template_path = DEFAULT_TEMPLATE_PATH
        settings.set_default(PERSISTENT_MDL_TEMPLATE_PATH, mdl_template_path)

        mdl_stdin = settings.get(SETTING_MDL_STDIN)
        settings.set_default(PERSISTENT_MDL_STDIN, mdl_stdin)

        mdl_render_mode = settings.get(SETTING_MDL_RENDER_MODE)
        settings.set_default(PERSISTENT_MDL_RENDER_MODE, mdl_render_mode)

        mdl_render_samples = settings.get(SETTING_MDL_RENDER_SAMPLES)
        settings.set_default(PERSISTENT_MDL_RENDER_SAMPLES, mdl_render_samples)

        # USD default settings
        usd_template_path = settings.get(SETTING_USD_TEMPLATE_PATH)
        if not usd_template_path:
            # Default template is local file, cannot set in extension.toml
            usd_template_path = DEFAULT_TEMPLATE_PATH
        settings.set_default(PERSISTENT_USD_TEMPLATE_PATH, mdl_template_path)

        usd_stdin = settings.get(SETTING_USD_STDIN)
        settings.set_default(PERSISTENT_USD_STDIN, usd_stdin)

        usd_render_mode = settings.get(SETTING_USD_RENDER_MODE)
        settings.set_default(PERSISTENT_USD_RENDER_MODE, usd_render_mode)

        usd_render_samples = settings.get(SETTING_USD_RENDER_SAMPLES)
        settings.set_default(PERSISTENT_USD_RENDER_SAMPLES, usd_render_samples)

    def build(self):
        with ui.VStack(height=0):
            with self.add_frame("MDL"):
                with ui.VStack():
                    self.create_setting_widget("Thumbnail Stage", PERSISTENT_MDL_TEMPLATE_PATH, "ASSET")
                    self.create_setting_widget("Stdin Prim", PERSISTENT_MDL_STDIN, SettingType.STRING)
                    self.create_setting_widget_combo(
                        "Renderer Type", PERSISTENT_MDL_RENDER_MODE, ["PathTracing", "RayTracing"]
                    )
                    self.create_setting_widget("Rendering Samples", PERSISTENT_MDL_RENDER_SAMPLES, SettingType.INT)

            with self.add_frame("USD"):
                with ui.VStack():
                    self.create_setting_widget("Thumbnail Stage", PERSISTENT_USD_TEMPLATE_PATH, "ASSET")
                    self.create_setting_widget("Stdin Prim", PERSISTENT_USD_STDIN, SettingType.STRING)
                    self.create_setting_widget_combo(
                        "Renderer Type", PERSISTENT_USD_RENDER_MODE, ["PathTracing", "RayTracing"]
                    )
                    self.create_setting_widget("Rendering Samples", PERSISTENT_USD_RENDER_SAMPLES, SettingType.INT)
