# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from unittest.mock import Mock

import omni.kit.test
from omni.asset_validator.core import ExtentsChecker
from omni.asset_validator.ui import (
    CapabilitiesModel,
    CategoriesModel,
    FeaturesModel,
    OptionGroup,
    OptionMode,
    OptionModel,
    OptionModeModel,
    OptionModeViewsWidget,
    OptionsDelegate,
    OptionsItemModel,
    OptionsModel,
    OptionsWidget,
    ProfilesModel,
)
from omni.capabilities import Requirements
from omni.kit import ui_test
from omni.ui import Label, Window


class OptionModeModelTest(omni.kit.test.AsyncTestCase):
    def test_set_value(self):
        model = OptionModeModel()
        model.mode = OptionMode.CAPABILITIES
        self.assertEqual(model.mode, OptionMode.CAPABILITIES)

    def test_value_changed_notification(self):
        model = OptionModeModel()
        on_value_changed = Mock()
        _subscription = model.subscribe_value_changed_fn(on_value_changed)

        model.mode = OptionMode.FEATURES
        self.assertTrue(on_value_changed.called)
        self.assertEqual(model.mode, OptionMode.FEATURES)


class OptionModeViewsWidgetTest(omni.kit.test.AsyncTestCase):

    async def test_widget(self):
        model = OptionModeModel()
        name = "OptionModeViewsWidget Test"
        window = Window(name)
        with window.frame:
            OptionModeViewsWidget(model, build_fn=lambda mode: Label(mode.name))
            await ui_test.human_delay()

            model.mode = OptionMode.FEATURES
            await ui_test.human_delay()


class OptionModelTest(omni.kit.test.AsyncTestCase):
    def test_init(self):
        model = OptionModel(
            value="test_value", name="test_name", description="test_desc", url="test_url", selected=True, enabled=True
        )
        self.assertEqual(model.value, "test_value")
        self.assertEqual(model.name, "test_name")
        self.assertEqual(model.description, "test_desc")
        self.assertEqual(model.url, "test_url")
        self.assertEqual(model.selected, True)
        self.assertEqual(model.enabled, True)

    def test_selected_setter(self):
        model = OptionModel(value="test", name="test", enabled=True)
        model.selected = True
        self.assertTrue(model.selected)

        model = OptionModel(value="test", name="test", enabled=False)
        model.selected = True
        self.assertFalse(model.selected)


class OptionGroupTest(omni.kit.test.AsyncTestCase):
    def test_init(self):
        group = OptionGroup("test_name", "test_url")
        self.assertEqual(group.name, "test_name")
        self.assertEqual(group.url, "test_url")
        self.assertEqual(len(group), 0)

    def test_append_and_len(self):
        group = OptionGroup("test")
        option1 = OptionModel(value="test1", name="test1")
        option2 = OptionModel(value="test2", name="test2")

        group.append(option1)
        self.assertEqual(len(group), 1)

        group.append(option2)
        self.assertEqual(len(group), 2)

    def test_getitem(self):
        group = OptionGroup("test")
        option1 = OptionModel(value="test1", name="test1")
        option2 = OptionModel(value="test2", name="test2")

        group.append(option1)
        group.append(option2)

        self.assertEqual(group[0], option1)
        self.assertEqual(group[1], option2)

    def test_get(self):
        group = OptionGroup("test")
        option1 = OptionModel(value="test1", name="test1")
        option2 = OptionModel(value="test2", name="test2")

        group.append(option1)
        group.append(option2)

        self.assertEqual(group.get("test1"), option1)
        self.assertEqual(group.get("test2"), option2)
        self.assertIsNone(group.get("nonexistent"))


class OptionsItemModelTest(omni.kit.test.AsyncTestCase):
    def test_init(self):
        # Create test data
        group = OptionGroup("Test Group")
        option1 = OptionModel(value="test1", name="test1")
        option2 = OptionModel(value="test2", name="test2")
        group.append(option1)
        group.append(option2)

        options_model = OptionsModel([group])
        model = OptionsItemModel(options_model)

        # Test root level items
        root_items = model.get_item_children(None)
        self.assertEqual(len(root_items), 1)
        self.assertEqual(root_items[0].model, group)

        # Test child items
        child_items = model.get_item_children(root_items[0])
        self.assertEqual(len(child_items), 2)
        self.assertEqual(child_items[0].model, option1)
        self.assertEqual(child_items[1].model, option2)

    def test_get_item_value_model(self):
        # Create test data
        group = OptionGroup("Test Group")
        option = OptionModel(value="test", name="test")
        group.append(option)

        options_model = OptionsModel([group])
        model = OptionsItemModel(options_model)

        # Get root and child items
        root_item = model.get_item_children(None)[0]
        child_item = model.get_item_children(root_item)[0]

        # Test value models
        self.assertEqual(model.get_item_value_model(root_item), group)
        self.assertEqual(model.get_item_value_model(child_item), option)


class OptionsWidgetTest(omni.kit.test.AsyncTestCase):
    async def test_widget_creation(self):
        # Create test data
        group = OptionGroup("Test Group", url="https://test.com")
        option1 = OptionModel(value="test1", name="test1", description="Test 1", url="https://test1.com", enabled=True)
        option2 = OptionModel(value="test2", name="test2", description="Test 2", enabled=False)
        group.append(option1)
        group.append(option2)

        options_model = OptionsModel([group])
        item_model = OptionsItemModel(options_model)

        # Create widget
        widget = OptionsWidget(item_model)

        # Test initial state
        root_items = item_model.get_item_children(None)
        child_items = item_model.get_item_children(root_items[0])

        self.assertEqual(len(root_items), 1)
        self.assertEqual(len(child_items), 2)

        # Test enable/disable all
        widget._toggle_option(enable=True)
        self.assertTrue(child_items[0].model.selected)
        self.assertFalse(child_items[1].model.selected)  # Should stay false since enabled=False

        widget._toggle_option(enable=False)
        self.assertFalse(child_items[0].model.selected)
        self.assertFalse(child_items[1].model.selected)

        # Test group enable/disable
        widget._toggle_option(enable=True, item=root_items[0])
        self.assertTrue(child_items[0].model.selected)
        self.assertFalse(child_items[1].model.selected)

        widget._toggle_option(enable=False, item=root_items[0])
        self.assertFalse(child_items[0].model.selected)
        self.assertFalse(child_items[1].model.selected)


class OptionsDelegateTest(omni.kit.test.AsyncTestCase):
    def setUp(self):
        self.categories_model = CategoriesModel()
        self.capabilities_model = CapabilitiesModel()
        self.features_model = FeaturesModel()
        self.profiles_model = ProfilesModel()

        self.delegate = OptionsDelegate(
            categories=self.categories_model,
            capabilities=self.capabilities_model,
            features=self.features_model,
            profiles=self.profiles_model,
        )

    def test_rule_sync_ok(self):
        rule_option = self.categories_model.get(ExtentsChecker)
        cap_req_option = self.capabilities_model.get(Requirements.VG_002)
        feat_req_option = self.features_model.get(Requirements.VG_002)

        rule_option.selected = True

        self.assertTrue(cap_req_option.selected)
        self.assertTrue(feat_req_option.selected)

    def test_capability_selection_ok(self):
        cap_req_option = self.capabilities_model.get(Requirements.VG_002)
        rule_option = self.categories_model.get(ExtentsChecker)
        feat_req_option = self.features_model.get(Requirements.VG_002)

        cap_req_option.selected = True

        self.assertTrue(rule_option.selected)
        self.assertTrue(feat_req_option.selected)

    def test_feature_selection_ok(self):
        feat_req_option = self.features_model.get(Requirements.VG_002)
        rule_option = self.categories_model.get(ExtentsChecker)
        cap_req_option = self.capabilities_model.get(Requirements.VG_002)

        feat_req_option.selected = True

        self.assertTrue(rule_option.selected)
        self.assertTrue(cap_req_option.selected)
