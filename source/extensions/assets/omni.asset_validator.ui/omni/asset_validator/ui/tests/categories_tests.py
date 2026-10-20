# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import omni.kit.test
import omni.ui as ui
from omni.asset_validator.core import BaseRuleChecker, ValidationRulesRegistry, registerRule
from omni.asset_validator.ui import CategoriesModel, CategoriesWidget
from omni.kit import ui_test
from pxr import Usd


class CategoriesModelTest(omni.kit.test.AsyncTestCase):

    async def test_init(self):
        model = CategoriesModel()
        self.assertGreater(len(model), 0)
        self.assertEqual(model[0].name, "Usd:Schema")

        for category in model:
            self.assertGreater(len(category), 0)

    async def test_register_rule(self):
        model = CategoriesModel()
        categories_count = len(model)

        @registerRule(category="TestCategory")
        class TestRule(BaseRuleChecker):
            def CheckPrim(self, prim: Usd.Prim): ...

        self.assertEqual(len(model), categories_count + 1)
        self.assertTrue(any(category.name == "TestCategory" for category in model))

        ValidationRulesRegistry.deregisterRule(TestRule)
        self.assertEqual(len(model), categories_count)
        self.assertFalse(any(category.name == "TestCategory" for category in model))


class CategoriesWidgetTest(omni.kit.test.AsyncTestCase):

    async def test_widget(self):
        model = CategoriesModel()
        window = ui.Window(__name__)
        with window.frame:
            CategoriesWidget(model)

            await ui_test.human_delay()
            button = ui_test.find(f"{__name__}//Frame/VStack[0]/HStack[0]/Button[0]")
            await button.click()
            for category in model:
                for rule in category:
                    self.assertTrue(rule.selected)

            button = ui_test.find(f"{__name__}//Frame/VStack[0]/HStack[0]/Button[1]")
            await button.click()
            for category in model:
                for rule in category:
                    self.assertFalse(rule.selected)
