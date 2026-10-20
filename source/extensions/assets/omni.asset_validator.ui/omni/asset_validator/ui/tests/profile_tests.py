# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from unittest.mock import Mock

import omni.kit.test
import omni.ui as ui
from omni.asset_validator.core import (
    BaseRuleChecker,
    Capability,
    Profile,
    Requirement,
    RequirementsRegistry,
    register_profile,
    register_requirements,
    unregister_profile,
    unregister_requirements,
)
from omni.asset_validator.ui import ProfilesModel, ProfilesWidget
from omni.capabilities import Profiles
from omni.kit import ui_test


class ProfilesModelTest(omni.kit.test.AsyncTestCase):

    async def test_init(self):
        model = ProfilesModel()
        self.assertGreaterEqual(len(model), len(Profiles))

        registry = RequirementsRegistry()
        for profile in model:
            self.assertGreater(len(profile), 0)
            for capability in profile:
                self.assertFalse(capability.selected)
                self.assertEqual(capability.enabled, bool(registry.get_validators(capability.value.requirements)))

    async def test_reset(self):
        model = ProfilesModel()
        # Set some capabilities as selected
        for profile in model:
            for capability in profile:
                if capability.enabled:
                    capability.selected = True

        # Reset should set all to False
        model.reset()
        for profile in model:
            for capability in profile:
                if capability.enabled:
                    self.assertFalse(capability.selected)

    async def test_add_callback(self):
        model = ProfilesModel()
        profiles_count = len(model)

        requirement: Requirement = Mock(spec=Requirement)
        requirement.code = "test_requirement"
        requirement.version = "0.1.0"
        requirement.display_name = "Test Requirement"
        requirement.message = "Test Message"
        requirement.path = "/test_requirement"

        class TestRule(BaseRuleChecker): ...

        capability: Capability = Mock(spec=Capability)
        capability.id = "test_capability"
        capability.version = "1.0.0"
        capability.path = "/test_capability"
        capability.requirements = [requirement]

        profile: Profile = Mock(spec=Profile)
        profile.id = "test_profile"
        profile.version = "1.0.0"
        profile.path = "/test_profile"
        profile.capabilities = [capability]

        register_requirements(requirement)(TestRule)
        register_profile(profile)
        try:
            self.assertEqual(len(model), profiles_count + 1)
        finally:
            unregister_requirements(TestRule)
            unregister_profile(profile)


class ProfilesWidgetTest(omni.kit.test.AsyncTestCase):

    async def test_widget(self):
        model = ProfilesModel()
        window = ui.Window(__name__)
        with window.frame:
            ProfilesWidget(model)

            await ui_test.human_delay()

            # Test select all button
            button = ui_test.find(f"{__name__}//Frame/VStack[0]/HStack[0]/Button[0]")
            await button.click()
            for profile in model:
                for capability in profile:
                    if capability.enabled:
                        self.assertTrue(capability.selected)

            # Test clear all button
            button = ui_test.find(f"{__name__}//Frame/VStack[0]/HStack[0]/Button[1]")
            await button.click()
            for profile in model:
                for capability in profile:
                    if capability.enabled:
                        self.assertFalse(capability.selected)
