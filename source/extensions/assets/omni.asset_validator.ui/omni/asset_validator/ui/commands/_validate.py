# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from dataclasses import dataclass, replace
from functools import partial
from itertools import filterfalse

from omni.asset_validator.core import (
    AssetProgress,
    AssetType,
    BaseRuleChecker,
    Capability,
    Issue,
    IssueSeverity,
    IssuesList,
    Requirement,
    RequirementsRegistry,
    Results,
)

from ..models._results import AssetResultsModel, IssueModel, ResultsModel
from ._base import CommandFn

__all__ = ["NOT_IMPLEMENTED_MESSAGE", "ValidateFn", "ValidatorOptions"]

NOT_IMPLEMENTED_MESSAGE = "Not implemented. Consider validating manually."
"""Message to display for not implemented requirements."""


@dataclass(frozen=True)
class ValidatorOptions:
    enabled_rules: list[type[BaseRuleChecker]]
    enabled_requirements: list[Requirement]
    enabled_capabilities: list[Capability]

    @property
    def all_requirements(self) -> list[Requirement]:
        requirements: list[Requirement] = list(self.enabled_requirements)
        registry = RequirementsRegistry()
        for rule in self.enabled_rules:
            if rule_requirements := registry.get_requirements(rule):
                requirements.extend(rule_requirements)
        for capability in self.enabled_capabilities:
            requirements.extend(capability.requirements)
        requirements = {(requirement.code, requirement.version): requirement for requirement in requirements}
        return list(requirements.values())

    @property
    def implemented_requirements(self) -> list[Requirement]:
        registry = RequirementsRegistry()
        return list(filter(registry.is_implemented, self.all_requirements))

    @property
    def not_implemented_requirements(self) -> list[Requirement]:
        registry = RequirementsRegistry()
        return list(filterfalse(registry.is_implemented, self.all_requirements))

    def _create_successful_rules(self, issues: IssuesList) -> list[Issue]:
        enabled_rules = set(self.enabled_rules)
        failed_rules = set(issue.rule for issue in issues if issue.rule is not None)
        registry = RequirementsRegistry()
        issues = [
            replace(Issue.none(), rule=rule)
            for rule in enabled_rules - failed_rules
            if not registry.get_requirements(rule)
        ]
        return issues

    def _create_successful_requirements(self, issues: IssuesList) -> list[Issue]:
        enabled_requirements = {
            (requirement.code, requirement.version): requirement for requirement in self.implemented_requirements
        }
        failed_requirements = {
            (requirement.code, requirement.version): requirement
            for issue in issues
            if (requirement := issue.requirement)
        }
        registry = RequirementsRegistry()
        issues = [
            replace(Issue.none(), rule=registry.get_validator(requirement), requirement=requirement)
            for key in enabled_requirements.keys() - failed_requirements.keys()
            if (requirement := enabled_requirements.get(key))
        ]
        return issues

    def compute_successful_issues(self, issues: IssuesList) -> list[Issue]:
        results: list[Issue] = []
        results.extend(self._create_successful_rules(issues))
        results.extend(self._create_successful_requirements(issues))
        return results

    def compute_not_implemented_issues(self) -> list[Issue]:
        return [
            Issue(message=NOT_IMPLEMENTED_MESSAGE, requirement=requirement, severity=IssueSeverity.INFO)
            for requirement in self.not_implemented_requirements
        ]


@dataclass
class ValidateFn(CommandFn):
    asset: AssetType | None = None

    def _asset_located_fn(self, asset: AssetType) -> None:
        results: ResultsModel = self.model.results
        if asset_results := results.get_asset(asset):
            asset_results.clear()  # Re calculation
            asset_results.group_by = self.model.group_by
            asset_results.filter_by = self.model.filters_model.predicate
        else:
            results.add_asset(AssetResultsModel(asset))

    def _asset_progress_fn(self, progress: AssetProgress) -> None:
        results: ResultsModel = self.model.results
        if asset_results := results.get_asset(progress.asset):
            asset_results.progress = progress.progress
            if progress.results:
                if len(progress.results) != len(asset_results.issues):  # avoid very frequent updates
                    asset_results.issues = [IssueModel(issue) for issue in progress.results]

    def _asset_validated_fn(self, results: Results, options: ValidatorOptions | None = None) -> None:
        issues: list[Issue] = list(results.issues)
        if options:
            issues.extend(options.compute_successful_issues(results.issues))
            issues.extend(options.compute_not_implemented_issues())

        model: ResultsModel = self.model.results
        if asset_results := model.get_asset(results.asset):
            asset_results.issues = [IssueModel(issue) for issue in issues]

    async def apply_async(self) -> None:
        engine = self.model.create_engine()
        if self.asset is None:
            self.model.results.clear()
            self.model.results.filter_by = self.model.filters_model.predicate
        options = ValidatorOptions(
            engine.enabled_rules,
            engine.enabled_requirements,
            engine.enabled_capabilities,
        )
        await engine.validate_with_callbacks(
            asset=self.asset or self.model.asset,
            asset_located_fn=self._asset_located_fn,
            asset_progress_fn=self._asset_progress_fn,
            asset_validated_fn=partial(self._asset_validated_fn, options=options),
        )
