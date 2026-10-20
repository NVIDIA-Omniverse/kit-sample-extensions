# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from collections import namedtuple

import omni.capabilities as cap
import omni.kit.test
from omni.asset_validator.core import (
    AnchoredAssetPathsChecker,
    AssetProgress,
    Issue,
    IssueSeverity,
    IssuesList,
    Results,
    TypeChecker,
)
from omni.asset_validator.ui import (
    ApplicationModel,
    AssetResultsModel,
    GroupResultsModel,
    IssueModel,
    ValidateFn,
    ValidatorOptions,
)
from pxr import Usd


class ValidatorOptionsTest(omni.kit.test.AsyncTestCase):

    def test_compute_successful_issues_enabled_rule(self):
        options = ValidatorOptions(
            enabled_rules=[TypeChecker],
            enabled_requirements=[],
            enabled_capabilities=[],
        )
        issues = IssuesList([])

        successful_issues = options.compute_successful_issues(issues)

        self.assertEqual(len(successful_issues), 1)
        self.assertEqual(successful_issues[0].severity, IssueSeverity.NONE)
        self.assertEqual(successful_issues[0].rule, TypeChecker)
        self.assertIsNone(successful_issues[0].requirement)

    def test_compute_successful_issues_enabled_rule_with_requirement(self):
        options = ValidatorOptions(
            enabled_rules=[AnchoredAssetPathsChecker],
            enabled_requirements=[],
            enabled_capabilities=[],
        )
        issues = IssuesList([])

        successful_issues = options.compute_successful_issues(issues)

        self.assertEqual(len(successful_issues), 1)
        self.assertEqual(successful_issues[0].severity, IssueSeverity.NONE)
        self.assertEqual(successful_issues[0].rule, AnchoredAssetPathsChecker)
        self.assertEqual(successful_issues[0].requirement.code, cap.Requirements.AA_001.code)

    def test_compute_successful_issues_enabled_requirement(self):
        options = ValidatorOptions(
            enabled_rules=[],
            enabled_requirements=[cap.Requirements.AA_001],
            enabled_capabilities=[],
        )
        issues = IssuesList([])

        successful_issues = options.compute_successful_issues(issues)

        self.assertEqual(len(successful_issues), 1)
        self.assertEqual(successful_issues[0].severity, IssueSeverity.NONE)
        self.assertEqual(successful_issues[0].rule, AnchoredAssetPathsChecker)
        self.assertEqual(successful_issues[0].requirement, cap.Requirements.AA_001)

    def test_compute_successful_issues_enabled_rule_and_requirement(self):
        options = ValidatorOptions(
            enabled_rules=[AnchoredAssetPathsChecker],
            enabled_requirements=[cap.Requirements.AA_001],
            enabled_capabilities=[],
        )
        issues = IssuesList([])

        successful_issues = options.compute_successful_issues(issues)

        self.assertEqual(len(successful_issues), 1)
        self.assertEqual(successful_issues[0].severity, IssueSeverity.NONE)
        self.assertEqual(successful_issues[0].rule, AnchoredAssetPathsChecker)
        self.assertEqual(successful_issues[0].requirement.code, cap.Requirements.AA_001.code)

    def test_compute_successful_issues_enabled_rule_with_issue(self):
        failed_issue = Issue(
            message="Test failure",
            severity=IssueSeverity.FAILURE,
            rule=TypeChecker,
        )
        options = ValidatorOptions(
            enabled_rules=[TypeChecker],
            enabled_requirements=[],
            enabled_capabilities=[],
        )
        issues = IssuesList([failed_issue])

        successful_issues = options.compute_successful_issues(issues)

        self.assertEqual(len(successful_issues), 0)

    def test_compute_successful_issues_enabled_rule_with_requirement_with_issue(self):
        failed_issue = Issue(
            message="Test failure",
            severity=IssueSeverity.FAILURE,
            rule=AnchoredAssetPathsChecker,
            requirement=cap.Requirements.AA_001,
        )
        options = ValidatorOptions(
            enabled_rules=[AnchoredAssetPathsChecker],
            enabled_requirements=[],
            enabled_capabilities=[],
        )
        issues = IssuesList([failed_issue])

        successful_issues = options.compute_successful_issues(issues)

        self.assertEqual(len(successful_issues), 0)

    def test_compute_not_implemented_issues_implemented_requirement(self):
        options = ValidatorOptions(
            enabled_rules=[],
            enabled_requirements=[cap.Requirements.AA_001],
            enabled_capabilities=[],
        )

        not_implemented_issues = options.compute_not_implemented_issues()

        self.assertEqual(len(not_implemented_issues), 0)

    def test_compute_not_implemented_issues_unimplemented_requirement(self):
        Requirement = namedtuple("Requirement", ["code", "version"])
        unimplemented = Requirement(code="TEST.001", version="1.0.0")
        options = ValidatorOptions(
            enabled_rules=[],
            enabled_requirements=[unimplemented],
            enabled_capabilities=[],
        )

        not_implemented_issues = options.compute_not_implemented_issues()

        self.assertEqual(len(not_implemented_issues), 1)
        self.assertEqual(not_implemented_issues[0].severity, IssueSeverity.INFO)
        self.assertEqual(not_implemented_issues[0].requirement, unimplemented)
        self.assertEqual(not_implemented_issues[0].message, "Not implemented. Consider validating manually.")

    def test_compute_not_implemented_issues_unimplemented_capability(self):
        Requirement = namedtuple("Requirement", ["code", "version"])
        unimplemented = Requirement(code="TEST.002", version="1.0.0")
        Capability = namedtuple("Capability", ["requirements"])
        capability = Capability(requirements=[unimplemented])
        options = ValidatorOptions(
            enabled_rules=[],
            enabled_requirements=[],
            enabled_capabilities=[capability],
        )

        not_implemented_issues = options.compute_not_implemented_issues()

        self.assertEqual(len(not_implemented_issues), 1)
        self.assertEqual(not_implemented_issues[0].severity, IssueSeverity.INFO)
        self.assertEqual(not_implemented_issues[0].requirement, unimplemented)


class ValidateFnTest(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self.model = ApplicationModel.create()

        self.model.categories_model.get(TypeChecker).selected = True
        self.model.asset = Usd.Stage.CreateInMemory()
        self.model.asset.DefinePrim("/World", "Xform")

    async def test_validate_fn_adds_task(self):
        validate_fn = ValidateFn(model=self.model)

        validate_fn.apply()

        self.assertTrue(self.model.has_tasks())
        await self.model.wait_tasks()

    async def test_asset_located_fn_clears_existing_asset(self):
        validate_fn = ValidateFn(model=self.model)
        asset_results = AssetResultsModel(self.model.asset)
        self.model.results.add_asset(asset_results)

        issue = Issue(message="Test", severity=IssueSeverity.FAILURE)
        asset_results.issues = [IssueModel(issue)]
        asset_results.progress = 1.0

        validate_fn._asset_located_fn(self.model.asset)

        self.assertEqual(len(asset_results.groups), 0)
        self.assertEqual(asset_results.progress, 0)

    async def test_asset_located_fn_adds_new_asset(self):
        validate_fn = ValidateFn(model=self.model)

        validate_fn._asset_located_fn(self.model.asset)

        self.assertEqual(len(self.model.results.assets), 1)
        self.assertEqual(self.model.results.assets[0].asset, self.model.asset)

    async def test_asset_progress_fn_updates_progress(self):
        validate_fn = ValidateFn(model=self.model)
        asset_results = AssetResultsModel(self.model.asset)
        self.model.results.add_asset(asset_results)

        progress = AssetProgress(self.model.asset, 0.5)
        validate_fn._asset_progress_fn(progress)

        self.assertEqual(asset_results.progress, 0.5)

    async def test_asset_validated_fn_no_issues(self):
        validate_fn = ValidateFn(model=self.model)
        asset_results = AssetResultsModel(self.model.asset)
        self.model.results.add_asset(asset_results)

        results = Results(self.model.asset, [])
        validate_fn._asset_validated_fn(results)

        self.assertEqual(len(asset_results.groups), 0)

    async def test_asset_validated_fn_updates_groups(self):
        validate_fn = ValidateFn(model=self.model)
        asset_results = AssetResultsModel(self.model.asset)
        self.model.results.add_asset(asset_results)

        issue = Issue(message="Hi", severity=IssueSeverity.FAILURE, rule=TypeChecker)
        results = Results(self.model.asset, [issue])
        validate_fn._asset_validated_fn(results)

        self.assertEqual(len(asset_results.groups), 1)
        self.assertIsInstance(asset_results.groups[0], GroupResultsModel)
