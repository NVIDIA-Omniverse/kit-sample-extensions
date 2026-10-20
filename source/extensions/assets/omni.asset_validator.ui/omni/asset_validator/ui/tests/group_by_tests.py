# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import omni.capabilities as cap
import omni.kit.test
import omni.ui as ui
from omni.asset_validator.core import AnchoredAssetPathsChecker, Issue, IssueSeverity
from omni.asset_validator.ui import ApplicationModel, GroupByModel, GroupByRequirement, GroupByRule, GroupByWidget
from omni.kit import ui_test


class GroupByRuleTest(omni.kit.test.AsyncTestCase):
    def test_group_by_rule(self):
        issue1 = Issue("Test message", rule=AnchoredAssetPathsChecker, severity=IssueSeverity.FAILURE)
        issue2 = Issue("Test message", rule=None, severity=IssueSeverity.FAILURE)

        group_by = GroupByRule()
        groups = group_by([issue1, issue2])

        self.assertEqual(groups[0][0], AnchoredAssetPathsChecker.__name__)
        self.assertEqual(groups[0][1], issue1)
        self.assertEqual(groups[1][0], GroupByRule.NO_RULE)
        self.assertEqual(groups[1][1], issue2)


class GroupByRequirementTest(omni.kit.test.AsyncTestCase):
    def test_group_by_requirement(self):
        issue1 = Issue(
            "Test message",
            rule=AnchoredAssetPathsChecker,
            requirement=cap.Requirements.AA_001,
            severity=IssueSeverity.FAILURE,
        )
        issue2 = Issue("Test message", rule=AnchoredAssetPathsChecker, requirement=None, severity=IssueSeverity.FAILURE)

        group_by = GroupByRequirement()
        groups = group_by([issue1, issue2])

        self.assertEqual(groups[0][0], cap.Requirements.AA_001.display_name)
        self.assertEqual(groups[0][1], issue1)
        self.assertEqual(groups[1][0], GroupByRequirement.NO_REQUIREMENT)
        self.assertEqual(groups[1][1], issue2)


class GroupByModelTest(omni.kit.test.AsyncTestCase):
    def test_group_by_model(self):
        model = GroupByModel()
        self.assertTrue(model.rule)
        self.assertIsInstance(model.group_by, GroupByRule)

        model.requirement = True
        self.assertTrue(model.requirement)
        self.assertIsInstance(model.group_by, GroupByRequirement)

        model.rule = True
        self.assertTrue(model.rule)
        self.assertIsInstance(model.group_by, GroupByRule)


class GroupByWidgetTest(omni.kit.test.AsyncTestCase):
    async def test_widget(self):
        model = ApplicationModel.create()
        window = ui.Window(__name__)
        with window.frame:
            GroupByWidget(model)
            await ui_test.human_delay()

            self.assertIsInstance(model.results.group_by, GroupByRule)

            model.group_by_model.requirement = True
            self.assertIsInstance(model.results.group_by, GroupByRequirement)

            model.group_by_model.rule = True
            self.assertIsInstance(model.results.group_by, GroupByRule)
