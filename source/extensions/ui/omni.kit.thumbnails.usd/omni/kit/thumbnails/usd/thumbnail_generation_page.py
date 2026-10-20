# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb.settings
import omni.ui as ui
from omni.kit.window.preferences import PERSISTENT_SETTINGS_PREFIX, PreferenceBuilder, SettingType, show_file_importer

MDL_PREFERENCES_PATH = "/exts/omni.kit.window.preferences/show_thumbnail_generation_mdl"


def set_default_usd_thumbnail_generator_settings():
    """Setup default value for the setting of the USD Thumbnail Generator"""
    settings = carb.settings.get_settings()
    settings.set_default_int("/app/thumbnailsGenerator/usd/width", 256)
    settings.set_default_int("/app/thumbnailsGenerator/usd/height", 256)
    settings.set_default_string(PERSISTENT_SETTINGS_PREFIX + "/app/thumbnailsGenerator/usd/renderer", "RayTracing")
    settings.set_default_int(PERSISTENT_SETTINGS_PREFIX + "/app/thumbnailsGenerator/usd/iterations", 8)
    settings.set_default_bool(PERSISTENT_SETTINGS_PREFIX + "/exts/omni.kit.thumbnails.usd/thumbnail_on_save", True)
    settings.set_default_bool(PERSISTENT_SETTINGS_PREFIX + "/exts/omni.kit.thumbnails.usd/wait_stage_load", False)
    settings.set_default_bool(PERSISTENT_SETTINGS_PREFIX + "/exts/omni.kit.thumbnails.usd/wait_stage_load_timeout", 50)


def set_default_mdl_thumbnail_generator_settings():
    """Setup default value for the setting of the MDL Thumbnail Generator"""
    settings = carb.settings.get_settings()
    settings.set_default_int("/app/thumbnailsGenerator/mdl/width", 256)
    settings.set_default_int("/app/thumbnailsGenerator/mdl/height", 256)
    settings.set_default_string(PERSISTENT_SETTINGS_PREFIX + "/app/thumbnailsGenerator/mdl/renderer", "PathTracing")
    settings.set_default_int(PERSISTENT_SETTINGS_PREFIX + "/app/thumbnailsGenerator/mdl/iterations", 512)

    template_url = "/Library/AEC/Materials/Library_Default.thumbnail.usd"
    settings.set_default_string(
        PERSISTENT_SETTINGS_PREFIX + "/app/thumbnailsGenerator/mdl/usd_template_path", template_url
    )
    settings.set_default_string(
        PERSISTENT_SETTINGS_PREFIX + "/app/thumbnailsGenerator/mdl/standin_usd_path", "/Stage/ShaderKnob"
    )


class ThumbnailGenerationPreferences(PreferenceBuilder):
    def __init__(self):
        super().__init__("Thumbnail Generation")

        self._settings = carb.settings.get_settings()

        # default_settings
        set_default_usd_thumbnail_generator_settings()
        set_default_mdl_thumbnail_generator_settings()

    def build(self):
        """Thumbnail Generation"""
        with ui.VStack(height=0):
            if carb.settings.get_settings().get(MDL_PREFERENCES_PATH):
                with self.add_frame("MDL Thumbnail Generation Settings"):
                    with ui.VStack():
                        self._settings_widget = self.create_setting_widget(
                            "Path usd template to render MDL Thumnail",
                            PERSISTENT_SETTINGS_PREFIX + "/app/thumbnailsGenerator/mdl/usd_template_path",
                            SettingType.STRING,
                            clicked_fn=self._on_browse_button_fn,
                        )

                        self.create_setting_widget(
                            "Name of the standin Prim",
                            PERSISTENT_SETTINGS_PREFIX + "/app/thumbnailsGenerator/mdl/standin_usd_path",
                            SettingType.STRING,
                        )
                        self.create_setting_widget_combo(
                            "Renderer Type",
                            PERSISTENT_SETTINGS_PREFIX + "/app/thumbnailsGenerator/mdl/renderer",
                            ["RayTracing", "PathTracing"],
                        )
                        self.create_setting_widget(
                            "Rendering Samples",
                            PERSISTENT_SETTINGS_PREFIX + "/app/thumbnailsGenerator/mdl/iterations",
                            SettingType.INT,
                        )
                self.spacer()

            with self.add_frame("USD Thumbnail Generation Settings"):
                with ui.VStack():
                    self.create_setting_widget_combo(
                        "Renderer Type",
                        PERSISTENT_SETTINGS_PREFIX + "/app/thumbnailsGenerator/usd/renderer",
                        ["RayTracing", "PathTracing"],
                    )
                    self.create_setting_widget(
                        "Rendering Samples",
                        PERSISTENT_SETTINGS_PREFIX + "/app/thumbnailsGenerator/usd/iterations",
                        SettingType.INT,
                    )
                    self.create_setting_widget(
                        "Save usd thumbnail on save",
                        PERSISTENT_SETTINGS_PREFIX + "/exts/omni.kit.thumbnails.usd/thumbnail_on_save",
                        SettingType.BOOL,
                    )

                    self._wait_stage_load_model = self.create_setting_widget(
                        "Generate until all assets loaded",
                        PERSISTENT_SETTINGS_PREFIX + "/exts/omni.kit.thumbnails.usd/wait_stage_load",
                        SettingType.BOOL,
                    ).model

                    self._wait_stage_load_timeout = self.create_setting_widget(
                        "Waiting assets loaded timeout",
                        PERSISTENT_SETTINGS_PREFIX + "/exts/omni.kit.thumbnails.usd/wait_stage_load_timeout",
                        SettingType.INT,
                    )

                    self._sub_wait_stage_load = self._wait_stage_load_model.subscribe_value_changed_fn(
                        self._on_wait_stage_load_changed
                    )
                    self._on_wait_stage_load_changed(self._wait_stage_load_model)

    def _on_wait_stage_load_changed(self, model: ui.AbstractValueModel) -> None:
        wait_stage_load = model.as_bool
        self._wait_stage_load_timeout.enabled = wait_stage_load

    def _on_browse_button_fn(self, owner):
        """Called when the user picks the Browse button."""
        path = self._settings_widget.model.get_value_as_string()
        show_file_importer(title="Select Template", click_apply_fn=self._on_file_pick, filename_url=path)

    def _on_file_pick(self, full_path):
        """Called when the user accepts directory in the Select Directory dialog."""
        self._settings.set(PERSISTENT_SETTINGS_PREFIX + "/app/thumbnailsGenerator/mdl/usd_template_path", full_path)
        self._settings_widget.model.set_value(full_path)

    def __del__(self):
        self._sub_wait_stage_load = None
        self._wait_stage_load_timeout = None
        super().__del__()
