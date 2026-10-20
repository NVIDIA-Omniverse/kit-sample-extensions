# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest.mock as mock

import omni.capabilities as cap
import omni.kit.test
from omni.asset_validator.core import (
    AnchoredAssetPathsChecker,
    EditTargetId,
    EditTargetIdList,
    Issue,
    IssuePredicates,
    IssueSeverity,
    LayerId,
    PrimId,
)
from omni.asset_validator.ui import (
    AssetResultsModel,
    GroupByRequirement,
    GroupByRule,
    GroupResultsModel,
    IssueModel,
    ResultsModel,
)
from pxr import Sdf, Usd


class IssueModelTest(omni.kit.test.AsyncTestCase):
    def setUp(self):
        self.path = Sdf.Path("/test")
        self.target_id = EditTargetId(layer_id=LayerId(identifier="layer1"), path=Sdf.Path("/layer1/test"))
        self.target_id2 = EditTargetId(layer_id=LayerId(identifier="layer2"), path=Sdf.Path("/layer2/test"))
        self.prim_id = PrimId(
            stage_id=None, path=self.path, spec_ids=EditTargetIdList([self.target_id, self.target_id2])
        )
        self.issue = Issue(
            message="Test message",
            severity=IssueSeverity.FAILURE,
            at=self.prim_id,
        )
        self.model = IssueModel(self.issue)

    def test_issue_properties(self):
        self.assertEqual(self.model.selected, False)
        self.assertEqual(self.model.issue, self.issue)

    def test_fix_model(self):
        self.assertIsNotNone(self.model.as_fix)
        self.assertEqual(self.model.fix_at, self.target_id)

    def test_value_changed_notification(self):
        on_value_changed = mock.Mock()
        _subscription = self.model.as_fix.subscribe_value_changed_fn(on_value_changed)

        self.model.as_fix.set_value(1)
        self.assertTrue(on_value_changed.called)

    def test_fix_status(self):
        # Test default fix_status when not provided
        model = IssueModel(self.issue)
        self.assertEqual(model.fix_status, "")

        # Test fix_status when provided in constructor
        test_status = "In Progress"
        model_with_status = IssueModel(self.issue, fix_status=test_status)
        self.assertEqual(model_with_status.fix_status, test_status)


class GroupResultsModelTest(omni.kit.test.AsyncTestCase):
    def setUp(self):
        self.path = Sdf.Path("/test")
        self.target_id = EditTargetId(layer_id=LayerId(identifier="layer1"), path=self.path)
        self.prim_id = PrimId(stage_id=None, path=self.path, spec_ids=EditTargetIdList([self.target_id]))
        self.issue = Issue(
            message="Test message",
            at=self.prim_id,
            severity=IssueSeverity.FAILURE,
        )
        self.issue_model = IssueModel(self.issue)
        self.group_model = GroupResultsModel("test_group")

    def test_group_properties(self):
        self.assertEqual(self.group_model.selected, False)
        self.assertEqual(self.group_model.name, "test_group")
        self.assertEqual(len(self.group_model.issues), 0)

    def test_set_issues(self):
        issues = [self.issue_model]
        self.group_model.issues = issues
        self.assertEqual(self.group_model.issues, issues)

    def test_find_issue(self):
        issues = [self.issue_model]
        self.group_model.issues = issues

        # Should find existing issue
        found = self.group_model.find_issue(self.issue)
        self.assertEqual(found, self.issue_model)

        # Should return None for non-existent issue
        other_issue = Issue(message="Other message", severity=IssueSeverity.FAILURE, at=self.prim_id)
        not_found = self.group_model.find_issue(other_issue)
        self.assertIsNone(not_found)

    def test_value_changed_notification(self):
        on_value_changed = mock.Mock()
        _subscription = self.group_model.subscribe_value_changed_fn(on_value_changed)

        self.group_model.issues = [self.issue_model]
        self.assertTrue(on_value_changed.called)

    def test_issues_property(self):
        self.assertEqual(len(self.group_model.issues), 0)

        issues = [self.issue_model]
        self.group_model.issues = issues
        self.assertEqual(len(self.group_model.issues), 1)
        self.assertEqual(self.group_model.issues[0], self.issue_model)

    def test_selected_issues(self):
        self.assertEqual(len(self.group_model.selected_issues), 0)
        self.group_model.issues = [self.issue_model]
        self.assertEqual(len(self.group_model.selected_issues), 0)
        self.issue_model.selected = True
        self.assertEqual(len(self.group_model.selected_issues), 1)

    def test_filter_by(self):
        self.group_model.issues = [self.issue_model]
        self.assertEqual(len(self.group_model.issues), 1)

        self.group_model.filter_by = IssuePredicates.IsFailure()
        self.assertEqual(len(self.group_model.issues), 1)

        self.group_model.filter_by = IssuePredicates.IsWarning()
        self.assertEqual(len(self.group_model.issues), 0)

        self.group_model.filter_by = IssuePredicates.Any()
        self.assertEqual(len(self.group_model.issues), 1)

    def test_notification_on_filter_change(self):
        on_value_changed = mock.Mock()
        _subscription = self.group_model.subscribe_value_changed_fn(on_value_changed)

        self.group_model.issues = [self.issue_model]
        on_value_changed.reset_mock()

        # Should notify when filter changes
        self.group_model.filter_by = IssuePredicates.IsFailure()
        self.assertTrue(on_value_changed.called)

        # Should not notify when setting same filter
        on_value_changed.reset_mock()
        self.group_model.filter_by = IssuePredicates.IsFailure()
        self.assertFalse(on_value_changed.called)


class AssetResultsModelTest(omni.kit.test.AsyncTestCase):
    def setUp(self):
        self.asset = "test_asset"
        self.model = AssetResultsModel(self.asset)
        self.issue = Issue(
            message="Asset references should use anchored paths",
            severity=IssueSeverity.FAILURE,
            rule=AnchoredAssetPathsChecker,
            requirement=cap.Requirements.AA_001,
        )

    def test_asset_property(self):
        self.assertEqual(self.model.selected, False)
        self.assertEqual(self.model.asset, "test_asset")

    def test_asset_name_at(self):
        model = AssetResultsModel("stage.usd@Cube")
        self.assertEqual(model.asset_name, "Cube")

    def test_asset_name_at_empty(self):
        model = AssetResultsModel("stage.usd@")
        self.assertEqual(model.asset_name, "stage.usd@")

    def test_asset_name_no_at(self):
        self.assertEqual(self.model.asset_name, "test_asset")

    def test_asset_name_url(self):
        model = AssetResultsModel("omniverse://localhost/NVIDIA/Samples/Astronaut/Astronaut.usd")
        self.assertEqual(model.asset_name, "Astronaut.usd")

    def test_asset_name_url_empty(self):
        model = AssetResultsModel("omniverse://localhost/NVIDIA/Samples/Astronaut/")
        self.assertEqual(model.asset_name, "omniverse://localhost/NVIDIA/Samples/Astronaut/")

    def test_progress_property(self):
        # Test default progress
        self.assertEqual(self.model.progress, 0.0)

        # Test setting progress
        self.model.progress = 0.5
        self.assertEqual(self.model.progress, 0.5)

        # Test progress model
        self.assertEqual(self.model.as_progress.get_value_as_float(), 0.5)

    def test_value_changed_notification(self):
        on_value_changed = mock.Mock()
        _subscription = self.model.subscribe_value_changed_fn(on_value_changed)

        self.model.issues = [IssueModel(self.issue)]
        self.assertTrue(on_value_changed.called)

    def test_progress_model_notification(self):
        on_progress_changed = mock.Mock()
        _subscription = self.model.as_progress.subscribe_value_changed_fn(on_progress_changed)

        self.model.progress = 0.25
        self.assertTrue(on_progress_changed.called)

    def test_clear(self):
        # Set up initial state
        self.model.issues = [IssueModel(self.issue)]
        self.model.progress = 0.5

        # Verify initial state
        self.assertEqual(len(self.model.groups), 1)
        self.assertEqual(self.model.progress, 0.5)

        # Clear the model
        self.model.clear()

        # Verify cleared state
        self.assertEqual(len(self.model.groups), 0)
        self.assertEqual(self.model.progress, 0.0)

    def test_clear_notification(self):
        on_value_changed = mock.Mock()
        _subscription = self.model.subscribe_value_changed_fn(on_value_changed)

        self.model.clear()
        self.assertTrue(on_value_changed.called)

    def test_issues(self):
        self.model.issues = [IssueModel(self.issue)]

        issues = self.model.issues
        self.assertGreater(len(issues), 0)
        # Check that we have an issue model with the same issue
        self.assertTrue(any(issue.issue == self.issue for issue in issues))

    def test_selected_issues(self):
        self.model.issues = [IssueModel(self.issue)]

        self.assertEqual(len(self.model.selected_issues), 0)

        self.model.issues[0].selected = True
        selected = self.model.selected_issues
        self.assertEqual(len(selected), 1)

    def test_filter_by(self):
        self.model.issues = [IssueModel(self.issue)]

        self.model.filter_by = IssuePredicates.IsFailure()
        self.assertEqual(len(self.model.issues), 1)

        self.model.filter_by = IssuePredicates.IsWarning()
        self.assertEqual(len(self.model.issues), 0)

    def test_group_by(self):
        self.model.issues = [IssueModel(self.issue)]

        self.model.group_by = GroupByRule()
        self.assertEqual(len(self.model.groups), 1)
        self.assertEqual(self.model.groups[0].name, AnchoredAssetPathsChecker.__name__)
        self.assertEqual(len(self.model.groups[0].issues), 1)
        self.assertEqual(len(self.model.issues), 1)

        self.model.group_by = GroupByRequirement()
        self.assertEqual(len(self.model.groups), 1)
        self.assertEqual(self.model.groups[0].name, cap.Requirements.AA_001.display_name)
        self.assertEqual(len(self.model.groups[0].issues), 1)
        self.assertEqual(len(self.model.issues), 1)

    def test_notification_on_filter_change(self):
        self.model.issues = [IssueModel(self.issue)]

        on_value_changed = mock.Mock()
        _subscription = self.model.subscribe_value_changed_fn(on_value_changed)
        self.model.filter_by = IssuePredicates.IsFailure()
        self.assertTrue(on_value_changed.called)

        on_value_changed.reset_mock()
        self.model.filter_by = IssuePredicates.IsFailure()
        self.assertFalse(on_value_changed.called)


class ResultsModelTest(omni.kit.test.AsyncTestCase):
    def setUp(self):
        self.path = Sdf.Path("/test")
        self.target_id = EditTargetId(layer_id=LayerId(identifier="layer1"), path=self.path)
        self.prim_id = PrimId(stage_id=None, path=self.path, spec_ids=EditTargetIdList([self.target_id]))
        self.issue = Issue(
            message="Test message",
            at=self.prim_id,
            severity=IssueSeverity.FAILURE,
        )
        self.asset = "test_asset"
        self.model = ResultsModel()
        self.asset_model = AssetResultsModel(self.asset)

    def test_assets_property(self):
        # Test empty assets list
        self.assertEqual(self.model.selected, False)
        self.assertEqual(len(self.model.assets), 0)

        # Test adding asset
        self.model.add_asset(self.asset_model)
        self.assertEqual(len(self.model.assets), 1)
        self.assertEqual(self.model.assets[0], self.asset_model)

    def test_get_asset(self):
        self.model.add_asset(self.asset_model)

        # Should find existing asset
        found = self.model.get_asset(self.asset)
        self.assertEqual(found, self.asset_model)

        # Should return None for non-existent asset
        not_found = self.model.get_asset("non_existent")
        self.assertIsNone(not_found)

        # Test with Usd Stage
        stage = Usd.Stage.CreateInMemory()
        stage_model = AssetResultsModel(stage)
        self.model.add_asset(stage_model)

        # Should find existing stage asset
        found_stage = self.model.get_asset(stage)
        self.assertEqual(found_stage, stage_model)

    def test_clear(self):
        self.model.add_asset(self.asset_model)
        self.assertEqual(len(self.model.assets), 1)

        self.model.clear()
        self.assertEqual(len(self.model.assets), 0)

    def test_find_issue(self):
        self.asset_model.issues = [IssueModel(self.issue)]
        self.model.add_asset(self.asset_model)

        # Should find existing issue
        found = self.model.find_issue(self.issue)
        self.assertIsNotNone(found)
        self.assertEqual(found.issue, self.issue)

        # Should return None for non-existent issue
        other_issue = Issue(message="Other message", severity=IssueSeverity.FAILURE, at=self.prim_id)
        not_found = self.model.find_issue(other_issue)
        self.assertIsNone(not_found)

    def test_value_changed_notification(self):
        on_value_changed = mock.Mock()
        _subscription = self.model.subscribe_value_changed_fn(on_value_changed)

        self.model.add_asset(self.asset_model)
        self.assertTrue(on_value_changed.called)

        on_value_changed.reset_mock()
        self.model.clear()
        self.assertTrue(on_value_changed.called)

    def test_issues(self):
        self.asset_model.issues = [IssueModel(self.issue)]
        self.model.add_asset(self.asset_model)

        issues = self.model.issues
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue, self.issue)

        self.model.clear()
        self.assertEqual(len(self.model.issues), 0)

    def test_selected_issues(self):
        self.asset_model.issues = [IssueModel(self.issue)]
        self.model.add_asset(self.asset_model)

        self.assertEqual(len(self.model.selected_issues), 0)

        # Select the first issue
        issue_model = self.model.issues[0]
        issue_model.selected = True
        self.assertEqual(len(self.model.selected_issues), 1)
        self.assertEqual(self.model.selected_issues[0], issue_model)

        issue_model.selected = False
        self.assertEqual(len(self.model.selected_issues), 0)

    def test_as_results_single_issue(self):
        self.asset_model.issues = [IssueModel(self.issue)]
        self.model.add_asset(self.asset_model)

        results = self.model.as_results

        self.assertEqual(len(results), 1)
        result = results[0]

        self.assertEqual(result.asset, self.asset_model.asset)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].severity, self.issue.severity)
        self.assertEqual(result.issues[0].message, self.issue.message)
        self.assertEqual(result.issues[0].at, self.issue.at)
        self.assertEqual(result.issues[0].rule, self.issue.rule)
        self.assertEqual(result.issues[0].suggestion, self.issue.suggestion)
        self.assertEqual(result.issues[0].rule, self.issue.rule)

    def test_filter_by(self):
        self.asset_model.issues = [IssueModel(self.issue)]
        self.model.add_asset(self.asset_model)

        self.assertEqual(len(self.model.issues), 1)

        self.model.filter_by = IssuePredicates.IsFailure()
        self.assertEqual(len(self.model.issues), 1)

        self.model.filter_by = IssuePredicates.IsWarning()
        self.assertEqual(len(self.model.issues), 0)

        self.model.filter_by = IssuePredicates.Any()
        self.assertEqual(len(self.model.issues), 1)

    def test_notification_on_filter_change(self):
        self.asset_model.issues = [IssueModel(self.issue)]
        self.model.add_asset(self.asset_model)

        on_value_changed = mock.Mock()
        _subscription = self.model.subscribe_value_changed_fn(on_value_changed)

        # Should notify when filter changes
        self.model.filter_by = IssuePredicates.IsFailure()
        self.assertTrue(on_value_changed.called)

        # Should not notify when setting same filter
        on_value_changed.reset_mock()
        self.model.filter_by = IssuePredicates.IsFailure()
        self.assertFalse(on_value_changed.called)
