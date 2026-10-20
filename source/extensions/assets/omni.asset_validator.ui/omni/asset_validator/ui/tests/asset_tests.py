# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest.mock as mock

import omni.kit.test
from omni.asset_validator.ui import (
    ApplicationModel,
    AssetMode,
    AssetWidget,
    ModeItemModel,
    ModeModel,
    PrimsModel,
    PrimsWidget,
    StageModel,
    UriModel,
)
from omni.kit import ui_test
from omni.ui import Window
from pxr import Sdf, Usd


class UriModelTest(omni.kit.test.AsyncTestCase):
    def test_set_value(self):
        model = UriModel()
        model.set_value("test/path")
        self.assertEqual(model.get_value_as_string(), "test/path")

    def test_value_changed_notification(self):
        model = UriModel()
        on_value_changed = mock.Mock()
        _subscription = model.subscribe_value_changed_fn(on_value_changed)

        model.set_value("new/path")
        self.assertTrue(on_value_changed.called)
        self.assertEqual(model.get_value_as_string(), "new/path")


class StageModelTest(omni.kit.test.AsyncTestCase):
    def test_set_value(self):
        model = StageModel()
        model.stage = omni.usd.get_context().get_stage()

        self.assertEqual(model.stage, omni.usd.get_context().get_stage())

    def test_value_changed_notification(self):
        model = StageModel()
        model.stage = omni.usd.get_context().get_stage()

        on_value_changed = mock.Mock()
        _subscription = model.subscribe_value_changed_fn(on_value_changed)

        stage = Usd.Stage.CreateInMemory()
        model.stage = stage
        self.assertTrue(on_value_changed.called)
        self.assertEqual(model.stage, stage)

    def test_get_value_as_string_none(self):
        model = StageModel()
        model.stage = None
        self.assertRegex(model.get_value_as_string(), r".*Current stage is not available.*")

    def test_get_value_as_string_anonymous(self):
        model = StageModel()
        model.stage = Usd.Stage.CreateInMemory()
        self.assertRegex(model.get_value_as_string(), r".*Anonymous stage.*")


class PrimsModelTest(omni.kit.test.AsyncTestCase):
    def test_set_value(self):
        model = PrimsModel()

        model.prims = [Sdf.Path("/World")]

        self.assertEqual(model.prims, [Sdf.Path("/World")])

    def test_value_changed_notification(self):
        model = PrimsModel()
        on_value_changed = mock.Mock()
        _subscription = model.subscribe_value_changed_fn(on_value_changed)

        model.prims = [Sdf.Path("/World")]

        self.assertTrue(on_value_changed.called)
        self.assertEqual(model.prims, [Sdf.Path("/World")])


class ModeModelTest(omni.kit.test.AsyncTestCase):
    def test_set_value(self):
        model = ModeModel()
        model.set_value(AssetMode.Stage.value)
        self.assertEqual(model.get_value_as_int(), AssetMode.Stage.value)

    def test_value_changed_notification(self):
        model = ModeModel()
        on_value_changed = mock.Mock()
        _subscription = model.subscribe_value_changed_fn(on_value_changed)

        model.set_value(AssetMode.Uri.value)
        self.assertTrue(on_value_changed.called)
        self.assertEqual(model.get_value_as_int(), AssetMode.Uri.value)


class ModeItemModelTest(omni.kit.test.AsyncTestCase):

    def test_init_ok(self):
        model = ModeModel()
        asset_mode_model = ModeItemModel(model)

        self.assertEqual(asset_mode_model.get_item_value_model(None, None), model)
        self.assertEqual(len(asset_mode_model.get_item_children(None)), 3)


class PrimsWidgetTest(omni.kit.test.AsyncTestCase):

    async def test_widget(self):
        model = PrimsModel()
        name = "Prims Widget Test"
        window = Window(name)
        with window.frame:
            PrimsWidget(model)
            await ui_test.human_delay()

            model.prims = [Sdf.Path("/World")]
            await ui_test.human_delay()


class AssetWidgetTest(omni.kit.test.AsyncTestCase):

    async def test_widget(self):
        model = ApplicationModel.create()
        name = "Asset Widget Test"
        window = Window(name)
        with window.frame:
            AssetWidget(model=model)

            await ui_test.human_delay()

            # Test URI mode
            model.mode = AssetMode.Uri
            await ui_test.human_delay()

            # Test Stage mode
            model.mode = AssetMode.Stage
            await ui_test.human_delay()

            # Test Prims mode
            model.mode = AssetMode.Prims
            await ui_test.human_delay()
