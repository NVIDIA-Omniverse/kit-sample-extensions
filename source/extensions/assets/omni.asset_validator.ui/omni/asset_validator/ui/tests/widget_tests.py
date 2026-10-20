# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from unittest import mock

import omni.kit.test
import omni.ui
from omni.asset_validator.ui import (
    ApplicationModel,
    EmbeddedValidatorWidget,
)
from omni.kit import ui_test


class EmbeddedValidatorWidgetTest(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self.offset_changed_fn = mock.Mock()
        self.model = ApplicationModel.create()

        self.widget = EmbeddedValidatorWidget(model=self.model, offset_x_changed_fn=self.offset_changed_fn)

    async def tearDown(self):
        self.widget.destroy()

    async def test_offset_x(self):
        # Test getting and setting offset_x
        self.widget.offset_x = 400
        self.assertEqual(self.widget.offset_x.value, 400)

    async def test_reset(self):
        # Test reset with both assets and rules
        self.model.uri = "test_uri"
        self.model.stage = mock.Mock()

        self.widget.reset(reset_assets=True, reset_rules=True)

        self.assertEqual(self.model.uri, "")
        self.assertIsNone(self.model.stage)

        # Test reset with only assets
        self.model.uri = "test_uri"
        self.model.stage = mock.Mock()

        self.widget.reset(reset_assets=True, reset_rules=False)

        self.assertEqual(self.model.uri, "")
        self.assertIsNone(self.model.stage)

        # Test reset with only rules
        self.model.uri = "test_uri"
        clear_mock = mock.Mock()
        self.model.results.clear = clear_mock

        self.widget.reset(reset_assets=False, reset_rules=True)

        self.assertEqual(self.model.uri, "test_uri")  # Should not change
        clear_mock.assert_called_once()

    async def test_widget(self):
        window = omni.ui.Window("TestWindow")
        with window.frame:
            EmbeddedValidatorWidget(model=self.model)

        await ui_test.human_delay()
