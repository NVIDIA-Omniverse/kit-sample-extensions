# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from collections import namedtuple
from unittest.mock import Mock

import omni.kit.test
import omni.ui as ui
from omni.asset_validator.core import (
    BaseRuleChecker,
    Capability,
    Requirement,
    register_capability,
    register_requirements,
    unregister_capability,
    unregister_requirements,
)
from omni.asset_validator.ui import CapabilitiesModel, CapabilitiesWidget
from omni.kit import ui_test


class CapabilitiesModelTest(omni.kit.test.AsyncTestCase):

    async def test_init(self):
        model = CapabilitiesModel()
        self.assertGreater(len(model), 0)

        for capability in model:
            self.assertGreater(len(capability), 0)

    async def test_reset(self):
        model = CapabilitiesModel()
        # Set some requirements as selected
        for capability in model:
            for requirement in capability:
                if requirement.enabled:
                    requirement.selected = True

        # Reset should set all to False
        model.reset()
        for capability in model:
            for requirement in capability:
                if requirement.enabled:
                    self.assertFalse(requirement.selected)

    async def test_add_callback(self):
        model = CapabilitiesModel()
        capabilities_count = len(model)
        requirements_count = sum(len(capability) for capability in model)

        self.requirement = Mock(spec=Requirement)
        self.requirement.code = "REQ001"
        self.requirement.version = "1.0.0"
        self.requirement.display_name = "Test Requirement"
        self.requirement.message = "Test Message"
        self.requirement.path = "/req001"

        self.capability = Mock(spec=Capability)
        self.capability.id = "CAP001"
        self.capability.version = "1.0.0"
        self.capability.path = "/cap001"
        self.capability.requirements = [self.requirement]

        class TestRule(BaseRuleChecker): ...

        register_requirements(self.requirement)(TestRule)
        register_capability(self.capability)
        try:
            self.assertEqual(len(model), capabilities_count + 1)
            self.assertEqual(sum(len(capability) for capability in model), requirements_count + 1)
        finally:
            unregister_requirements(TestRule)
            unregister_capability(self.capability)

    async def test_add_callback_with_requirement_ref(self):
        model = CapabilitiesModel()
        capabilities_count = len(model)
        requirements_count = sum(len(capability) for capability in model)

        requirement = Mock(spec=Requirement)
        requirement.code = "REQ_REF_001"
        requirement.version = "1.0.0"
        requirement.display_name = "Test Requirement Ref"
        requirement.message = "Test Message"
        requirement.path = "/req_ref_001"

        RequirementRef = namedtuple("RequirementRef", ["code", "version"])

        capability = Mock(spec=Capability)
        capability.id = "CAP_REF_001"
        capability.version = "1.0.0"
        capability.path = "/cap_ref_001"
        capability.requirements = [RequirementRef(requirement.code, requirement.version)]

        class TestRule(BaseRuleChecker): ...

        register_requirements(requirement)(TestRule)
        register_capability(capability)
        try:
            self.assertEqual(len(model), capabilities_count + 1)
            self.assertEqual(sum(len(capability) for capability in model), requirements_count + 1)
            self.assertIsNotNone(model.get(requirement))
        finally:
            unregister_requirements(TestRule)
            unregister_capability(capability)


class CapabilitiesWidgetTest(omni.kit.test.AsyncTestCase):

    async def test_widget(self):
        model = CapabilitiesModel()
        window = ui.Window(__name__)
        with window.frame:
            CapabilitiesWidget(model)

            await ui_test.human_delay()
            button = ui_test.find(f"{__name__}//Frame/VStack[0]/HStack[0]/Button[0]")
            await button.click()
            for capability in model:
                for requirement in capability:
                    if requirement.enabled:
                        self.assertTrue(requirement.selected)

            button = ui_test.find(f"{__name__}//Frame/VStack[0]/HStack[0]/Button[1]")
            await button.click()
            for capability in model:
                for requirement in capability:
                    if requirement.enabled:
                        self.assertFalse(requirement.selected)
