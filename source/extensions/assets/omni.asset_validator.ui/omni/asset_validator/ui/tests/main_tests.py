# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import carb
import omni.kit.test
from omni.asset_validator.ui import ApplicationModel, MainWidget
from omni.kit import ui_test
from omni.ui import Window


class MainWidgetTest(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self.model = ApplicationModel.create()

    async def tearDown(self):
        carb.settings.get_settings().set("exts/omni.asset_validator.ui/capabilities/enabled", False)
        carb.settings.get_settings().set("exts/omni.asset_validator.ui/features/enabled", False)

    async def test_widget(self):
        window = Window("TestWindow")
        with window.frame:
            MainWidget(self.model)

            await ui_test.human_delay()

    async def test_widget_with_capabilities(self):
        carb.settings.get_settings().set("exts/omni.asset_validator.ui/capabilities/enabled", True)
        window = Window("TestWindow")
        with window.frame:
            MainWidget(self.model)

            await ui_test.human_delay()

    async def test_widget_with_features(self):
        carb.settings.get_settings().set("exts/omni.asset_validator.ui/features/enabled", True)
        window = Window("TestWindow")
        with window.frame:
            MainWidget(self.model)

            await ui_test.human_delay()

    async def test_widget_with_capabilities_and_features(self):
        carb.settings.get_settings().set("exts/omni.asset_validator.ui/capabilities/enabled", True)
        carb.settings.get_settings().set("exts/omni.asset_validator.ui/features/enabled", True)
        window = Window("TestWindow")
        with window.frame:
            MainWidget(self.model)

            await ui_test.human_delay()
