# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from collections import namedtuple
from unittest.mock import Mock

import omni.kit.test
import omni.ui as ui
from omni.asset_validator.core import (
    BaseRuleChecker,
    Feature,
    Requirement,
    register_feature,
    register_requirements,
    unregister_feature,
    unregister_requirements,
)
from omni.asset_validator.ui import FeaturesModel, FeaturesWidget
from omni.kit import ui_test


class FeaturesModelTest(omni.kit.test.AsyncTestCase):

    async def test_init(self):
        model = FeaturesModel()
        self.assertGreater(len(model), 0)

        for feature in model:
            self.assertGreater(len(feature), 0)

    async def test_reset(self):
        model = FeaturesModel()
        # Set some requirements as selected
        for feature in model:
            for requirement in feature:
                if requirement.enabled:
                    requirement.selected = True

        # Reset should set all to False
        model.reset()
        for feature in model:
            for requirement in feature:
                if requirement.enabled:
                    self.assertFalse(requirement.selected)

    async def test_add_feature_callback(self):
        model = FeaturesModel()
        features_count = len(model)

        requirement: Requirement = Mock(spec=Requirement)
        requirement.code = "test_requirement"
        requirement.version = "0.1.0"
        requirement.display_name = "Test Requirement"
        requirement.message = "Test Message"
        requirement.path = "/test_requirement"

        class TestRule(BaseRuleChecker): ...

        feature: Feature = Mock(spec=Feature)
        feature.id = "test_feature"
        feature.version = "1.0.0"
        feature.path = "/test_feature"
        feature.requirements = [requirement]

        register_requirements(requirement)(TestRule)
        register_feature(feature)
        try:
            self.assertEqual(len(model), features_count + 1)
        finally:
            unregister_requirements(TestRule)
            unregister_feature(feature)

    async def test_add_feature_callback_with_requirement_ref(self):
        model = FeaturesModel()
        features_count = len(model)

        requirement: Requirement = Mock(spec=Requirement)
        requirement.code = "test_requirement_ref"
        requirement.version = "0.1.0"
        requirement.display_name = "Test Requirement Ref"
        requirement.message = "Test Message"
        requirement.path = "/test_requirement_ref"

        class TestRule(BaseRuleChecker): ...

        RequirementRef = namedtuple("RequirementRef", ["code", "version"])

        feature: Feature = Mock(spec=Feature)
        feature.id = "test_feature_ref"
        feature.version = "1.0.0"
        feature.path = "/test_feature_ref"
        feature.requirements = [RequirementRef(requirement.code, requirement.version)]

        register_requirements(requirement)(TestRule)
        register_feature(feature)
        try:
            self.assertEqual(len(model), features_count + 1)
            self.assertIsNotNone(model.get(requirement))
        finally:
            unregister_requirements(TestRule)
            unregister_feature(feature)


class FeaturesWidgetTest(omni.kit.test.AsyncTestCase):

    async def test_widget(self):
        model = FeaturesModel()
        window = ui.Window("TestWindow")
        with window.frame:
            FeaturesWidget(model)

        await ui_test.human_delay()
        button = ui_test.find("TestWindow//Frame/VStack[0]/HStack[0]/Button[0]")
        await button.click()
        for feature in model:
            for requirement in feature:
                if requirement.enabled:
                    self.assertTrue(requirement.selected)

        button = ui_test.find("TestWindow//Frame/VStack[0]/HStack[0]/Button[1]")
        await button.click()
        for feature in model:
            for requirement in feature:
                if requirement.enabled:
                    self.assertFalse(requirement.selected)
