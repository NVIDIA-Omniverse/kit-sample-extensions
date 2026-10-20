# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from typing import Any, Dict, List, Tuple

import carb.settings
from omni.kit.capture.viewport import CaptureExtension
from omni.kit.capture.viewport.capture_options import CaptureOptions
from omni.kit.test import AsyncTestCase
from omni.kit.window.movie_capture.base_widget import APP_OVC_DEVELOPMENT_SETTING_PATH, MC_EXT_OVC_MODE_SETTING_PATH
from omni.kit.window.movie_capture.ui_values_storage import UIValuesStorage
from omni.services.core.main import deregister_router, register_router
from omni.services.core.routers import ServiceAPIRouter

from ..farm_settings_widget import FarmSettingsWidget, is_supported_farm_content_type_extension
from ..utils.farm_queue_utils import ADVANCED_RENDERING_FEATURES_SETTINGS_KEY


class TestFarmSettingsWidgetTestCase(AsyncTestCase):
    """Test case for the Farm Settings widget."""

    def setUp(self) -> None:
        super().setUp()

        self._capture_instance = CaptureExtension.get_instance()

        settings = carb.settings.get_settings_interface()
        self._initial_farms = settings.get("exts/omni.kit.window.movie_capture/available_farms")

    def tearDown(self) -> None:
        self._capture_instance = None

        settings = carb.settings.get_settings_interface()
        settings.set("exts/omni.kit.window.movie_capture/available_farms", self._initial_farms)

        super().tearDown()

    def _on_collect_capture_settings(self, _: bool = True) -> Tuple[CaptureOptions, Dict[str, Any]]:
        """
        Mock implementation of the callback providing capture and Farm settings for the rendering of a task.

        Args:
            _ (bool): Unused.

        Returns:
            Tuple[CaptureOptions, Dict[str, Any]]: A Tuple of `CaptureOptions` and Farm settings to use for the
                rendering of a task on the remote Farm.

        """
        capture_options = self._capture_instance.options
        farm_settings = {}
        return capture_options, farm_settings

    async def test_supported_farm_content_type_extension(self) -> None:
        """Validate supported rendering extensions for Farm rendering."""
        test_extensions_pairs: List[Tuple[str, bool]] = [
            (".mp4", False),
            (".MP4", False),  # Ensure the validation is case-insensitive.
            (".png", True),
            (".exr", True),
        ]

        for test_extensions_pair in test_extensions_pairs:
            with self.subTest(extension_pair=test_extensions_pair):
                extension, expected_result = test_extensions_pair

                is_extension_supported = is_supported_farm_content_type_extension(extension=extension)

                self.assertEqual(first=is_extension_supported, second=expected_result)

    async def test_ui_values_can_be_retrieved(self) -> None:
        """UI values can be retrieved from the Farm Setting Widget's API."""
        TEST_UI_SETTINGS: List[Tuple[str, bool]] = [
            (UIValuesStorage.SETTING_NAME_QUEUE_INSTANCE, "localhost Queue"),
            (UIValuesStorage.SETTING_NAME_TASK_TYPE, "create-render"),
            (UIValuesStorage.SETTING_NAME_TASK_COMMENT, ""),
            (UIValuesStorage.SETTING_NAME_UPLOAD_TO_S3, False),
            (UIValuesStorage.SETTING_NAME_SKIP_UPLOAD_TO_S3, False),
        ]

        ui_values = UIValuesStorage()

        farm_settings_widget = FarmSettingsWidget()
        farm_settings_widget.build_ui()
        farm_settings_widget.get_ui_values(ui_values=ui_values)

        for test_ui_setting in TEST_UI_SETTINGS:
            setting_name, expected_setting_value = test_ui_setting
            retrieved_ui_value = ui_values.get(setting_name=setting_name)

            self.assertEqual(first=retrieved_ui_value, second=expected_setting_value)

    async def test_ui_values_can_be_set(self) -> None:
        """UI values can be applied from the Farm Setting Widget's API."""
        TEST_UI_SETTINGS: List[Tuple[str, bool]] = [
            (UIValuesStorage.SETTING_NAME_QUEUE_INSTANCE, "local://"),
            (UIValuesStorage.SETTING_NAME_TASK_TYPE, ""),
            (UIValuesStorage.SETTING_NAME_TASK_COMMENT, ""),
            (UIValuesStorage.SETTING_NAME_UPLOAD_TO_S3, False),
            (UIValuesStorage.SETTING_NAME_SKIP_UPLOAD_TO_S3, False),
        ]

        original_ui_values = UIValuesStorage()
        modified_ui_values = UIValuesStorage()
        test_ui_values = UIValuesStorage()
        for test_ui_setting in TEST_UI_SETTINGS:
            setting_name, setting_value = test_ui_setting
            test_ui_values.set(setting_name=setting_name, value=setting_value)

        farm_settings_widget = FarmSettingsWidget()
        farm_settings_widget.build_ui()
        farm_settings_widget.get_ui_values(ui_values=original_ui_values)
        farm_settings_widget.apply_ui_values(ui_values=test_ui_values)
        farm_settings_widget.get_ui_values(ui_values=modified_ui_values)

        for test_ui_setting in TEST_UI_SETTINGS:
            test_setting_name, test_setting_value = test_ui_setting
            modified_setting_value = modified_ui_values.get(setting_name=test_setting_name)

            self.assertEqual(first=modified_setting_value, second=test_setting_value)

    async def test_handling_advanced_rendering_features_does_not_raise_if_not_queue_is_selected(self) -> None:
        """Validate that handling advanced rendering features does not raise Exceptions if no Farm Queue is selected."""
        farm_settings_widget = FarmSettingsWidget()
        farm_settings_widget.build_ui()
        try:
            await farm_settings_widget.handle_advanced_rendering_features()
        except:  # pragma: no cover
            self.fail(
                msg="Expected handling of advanced rendering features without any available Farms to not raise exceptions."
            )

    async def test_retrieving_upload_to_s3_ui_value_in_ovc_mode(self) -> None:
        """Validate that remote Farm settings can be retrieved when in OVC mode."""
        settings = carb.settings.get_settings_interface()
        original_is_app_ovc_setting: bool = settings.get_as_bool(APP_OVC_DEVELOPMENT_SETTING_PATH)
        original_is_ext_ovc_setting: bool = settings.get_as_bool(MC_EXT_OVC_MODE_SETTING_PATH)
        settings.set(MC_EXT_OVC_MODE_SETTING_PATH, True)

        _, farm_settings = self._on_collect_capture_settings()
        # Edit some settings to allow reading the "Advanced Render Settings" from a locally-hosted Farm Queue URL,
        # acting as the remote Farm in order to pretend it requesting that USD Stages be uploaded to S3:
        farm_settings["farm_url"] = "local://"
        farm_settings["upload_to_s3"] = False

        # Host a local Service, acting as the remote Farm Queue's setting Service in order to feed its "Advanced Render
        # Settings":
        router = ServiceAPIRouter()

        @router.get("/queue/settings")
        async def queue_settings() -> Dict[str, Any]:
            return {  # pragma: no cover
                "settings": {
                    f"{ADVANCED_RENDERING_FEATURES_SETTINGS_KEY}": {
                        "ui_should_upload": True,
                    },
                },
            }

        register_router(router=router)

        farm_settings_widget = FarmSettingsWidget()
        farm_settings_widget.build_ui()
        await farm_settings_widget.handle_advanced_rendering_features()

        self.assertEqual(first=farm_settings_widget.get_upload_to_s3_ui_value(), second=farm_settings["upload_to_s3"])

        deregister_router(router=router)

        # Restore initial settings:
        settings.set(APP_OVC_DEVELOPMENT_SETTING_PATH, original_is_app_ovc_setting)
        settings.set(MC_EXT_OVC_MODE_SETTING_PATH, original_is_ext_ovc_setting)
