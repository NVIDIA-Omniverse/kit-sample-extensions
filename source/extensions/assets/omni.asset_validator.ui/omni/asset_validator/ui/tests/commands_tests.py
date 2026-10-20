# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import omni.kit.test
from omni.asset_validator.ui import ApplicationModel, ValidatorCommandsWidget
from omni.ui import Window
from pxr import Usd


class ValidatorCommandsWidgetTest(omni.kit.test.AsyncTestCase):

    async def setUp(self):
        self.model = ApplicationModel.create()

        self.model.asset = Usd.Stage.CreateInMemory()
        self.model.asset.DefinePrim("/World", "Xform")

    async def test_validate_ok(self):
        window = Window("TestWindow")
        with window.frame:
            widget = ValidatorCommandsWidget(self.model)
            self.assertTrue(widget._analyze_button.visible)
            self.assertFalse(widget._cancel_button.visible)
            self.assertTrue(widget._fix_button.enabled)
            self.assertTrue(widget._clear_button.enabled)

            widget._validate()
            self.assertFalse(widget._analyze_button.visible)
            self.assertTrue(widget._cancel_button.visible)
            self.assertFalse(widget._fix_button.enabled)
            self.assertFalse(widget._clear_button.enabled)

            await self.model.wait_tasks()
            self.assertTrue(widget._analyze_button.visible)
            self.assertFalse(widget._cancel_button.visible)
            self.assertTrue(widget._fix_button.enabled)
            self.assertTrue(widget._clear_button.enabled)

    async def test_cancel_ok(self):
        window = Window("TestWindow")
        with window.frame:
            widget = ValidatorCommandsWidget(self.model)
            self.assertTrue(widget._analyze_button.visible)
            self.assertFalse(widget._cancel_button.visible)
            self.assertTrue(widget._fix_button.enabled)
            self.assertTrue(widget._clear_button.enabled)

            widget._validate()
            self.assertFalse(widget._analyze_button.visible)
            self.assertTrue(widget._cancel_button.visible)
            self.assertFalse(widget._fix_button.enabled)
            self.assertFalse(widget._clear_button.enabled)

            widget._cancel()
            self.assertTrue(widget._analyze_button.visible)
            self.assertFalse(widget._cancel_button.visible)
            self.assertTrue(widget._fix_button.enabled)
            self.assertTrue(widget._clear_button.enabled)
