# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from omni.asset_validator.core import (
    AssetType,
    EditTargetId,
    Issue,
    IssueGroupBy,
    IssuePredicate,
    IssuePredicates,
    IssuesList,
    Results,
    ResultsList,
    Suggestion,
    ValidationEngine,
)
from omni.ui import AbstractValueModel, SimpleBoolModel

from ._fix import FixAtModel, SuggestionModel
from ._group_by import GroupByRule
from ._progress import ProgressModel

__all__ = [
    "AssetResultsModel",
    "GroupResultsModel",
    "HasFilterBy",
    "HasGroupBy",
    "HasSelectedModel",
    "IssueModel",
    "ResultsModel",
]


class HasFilterBy(AbstractValueModel):
    def __init__(self):
        super().__init__()
        self._filter_by: IssuePredicate = IssuePredicates.Any()

    @property
    def filter_by(self) -> IssuePredicate:
        return self._filter_by

    @filter_by.setter
    def filter_by(self, filter_by: IssuePredicate) -> None:
        if self._filter_by != filter_by:
            self._filter_by = filter_by
            self._on_filter_by_changed(filter_by)
            self._value_changed()

    def _on_filter_by_changed(self, filter_by: IssuePredicate) -> None: ...

    def apply_filter(self, filter_by: IssuePredicate) -> None:
        """Deprecated method. Use filter_by property instead."""
        self.filter_by = filter_by


class HasGroupBy(AbstractValueModel):
    def __init__(self):
        super().__init__()
        self._group_by: IssueGroupBy = GroupByRule()

    @property
    def group_by(self) -> IssueGroupBy:
        return self._group_by

    @group_by.setter
    def group_by(self, group_by: IssueGroupBy) -> None:
        if self._group_by != group_by:
            self._group_by = group_by
            self._on_group_by_changed(group_by)
            self._value_changed()

    def _on_group_by_changed(self, group_by: IssueGroupBy) -> None: ...


class HasSelectedModel(AbstractValueModel):
    def __init__(self):
        super().__init__()
        self._selected = SimpleBoolModel(False)

    @property
    def selected(self) -> bool:
        return self._selected.as_bool

    @selected.setter
    def selected(self, value) -> None:
        self._selected.as_bool = value

    @property
    def selected_model(self) -> SimpleBoolModel:
        return self._selected


class IssueModel(HasSelectedModel):
    def __init__(self, issue: Issue, fix_status: str | None = None):
        super().__init__()
        self._issue = issue
        self._fix_status = fix_status or ""
        self._suggestion_model = SuggestionModel(issue.suggestions)
        self._fix_at = FixAtModel(issue.all_fix_sites)
        self._suggestion_subscription = self._suggestion_model.subscribe_value_changed_fn(self._on_suggestion_changed)

    def _on_suggestion_changed(self, _) -> None:
        """Recompute fix sites for the newly selected suggestion.

        Each suggestion may have different layer constraints (suggestion.at),
        so valid fix sites differ per suggestion.
        """
        suggestion = self._suggestion_model.suggestion
        self._fix_at.reset(self._issue.fix_sites_for(suggestion))

    @property
    def issue(self) -> Issue:
        return self._issue

    @property
    def fix_status(self) -> str:
        return self._fix_status

    @fix_status.setter
    def fix_status(self, value: str) -> None:
        self._fix_status = value
        self._value_changed()

    @property
    def fix_at(self) -> EditTargetId | None:
        return self._fix_at.fix_site

    @property
    def as_fix(self) -> FixAtModel:
        return self._fix_at

    @property
    def selected_suggestion(self) -> Suggestion | None:
        return self._suggestion_model.suggestion

    @property
    def as_suggestion(self) -> SuggestionModel:
        return self._suggestion_model


class HasIssuesModel(AbstractValueModel):
    def __init__(self):
        super().__init__()
        self._issues: list[IssueModel] = []

    @property
    def issues(self) -> list[IssueModel]:
        return [issue for issue in self._issues if self.filter_by(issue.issue)]

    @issues.setter
    def issues(self, issues: list[IssueModel]) -> None:
        self._issues = issues
        self._value_changed()

    @property
    def selected_issues(self) -> list[IssueModel]:
        return [issue for issue in self.issues if issue.selected]

    def find_issue(self, issue: Issue) -> IssueModel | None:
        return next((model for model in self.issues if model.issue == issue), None)


class GroupResultsModel(HasSelectedModel, HasFilterBy, HasIssuesModel):
    def __init__(self, name):
        super().__init__()
        self._name = name

    @property
    def name(self) -> AssetType:
        return self._name


class AssetResultsModel(HasSelectedModel, HasFilterBy, HasGroupBy, HasIssuesModel):
    def __init__(self, asset: AssetType):
        super().__init__()
        self._asset = asset
        self._progress = ProgressModel()
        self._outdated: bool = False

    @property
    def asset(self) -> AssetType:
        return self._asset

    @property
    def asset_id(self) -> str:
        return ValidationEngine.describe(self.asset)

    @property
    def asset_name(self) -> str:
        asset_name: str = self.asset_id

        # url
        start = asset_name.rfind("/")
        if 0 < start < len(asset_name) - 1:
            return asset_name[start + 1 :]

        # stage
        start = asset_name.find("@")
        if 0 < start < len(asset_name) - 1:
            return asset_name[start + 1 :]

        return asset_name

    @property
    def progress(self) -> float:
        return self._progress.get_value_as_float()

    @progress.setter
    def progress(self, value) -> None:
        self._progress.set_value(value)

    @property
    def finished(self) -> bool:
        return self.progress >= 1

    @property
    def as_progress(self) -> ProgressModel:
        return self._progress

    @property
    def outdated(self) -> bool:
        return self._outdated

    @outdated.setter
    def outdated(self, value: bool) -> None:
        if self._outdated != value:
            self._outdated = value
            self._value_changed()

    @property
    def groups(self) -> list[GroupResultsModel]:
        issue_to_model: dict[int, IssueModel] = {id(issue.issue): issue for issue in self._issues}
        groups: list[GroupResultsModel] = []
        issues_list = IssuesList([issue.issue for issue in self._issues])
        for group in issues_list.group_by(self.group_by):
            issues: list[IssueModel]
            if group.issues:
                issues = [issue_to_model[id(issue)] for issue in group.issues]
            elif group.success:
                issues = [issue_to_model[id(group.success[0])]]
            else:
                issues = [IssueModel(Issue.none())]
            group_result = GroupResultsModel(group.name)
            group_result.issues = issues
            group_result.filter_by = self.filter_by
            if group_result.issues:
                groups.append(group_result)
        groups.sort(key=lambda group: group.name or "")
        return groups

    def clear(self) -> None:
        self.selected = False
        self._progress.set_value(0)
        self._issues.clear()
        self._outdated = False
        self._value_changed()


class ResultsModel(HasSelectedModel, HasFilterBy, HasGroupBy):
    def __init__(self):
        super().__init__()
        self._assets = {}

    @property
    def assets(self) -> list[AssetResultsModel]:
        return list(self._assets.values())

    def add_asset(self, model: AssetResultsModel) -> None:
        model.group_by = self._group_by
        model.filter_by = self._filter_by
        self._assets[model.asset_id] = model
        self._value_changed()

    def get_asset(self, asset: AssetType) -> AssetResultsModel | None:
        asset_id = ValidationEngine.describe(asset)
        return self._assets.get(asset_id)

    def _on_filter_by_changed(self, filter_by: IssuePredicate) -> None:
        for asset in self.assets:
            asset.filter_by = filter_by

    def _on_group_by_changed(self, group_by: IssueGroupBy) -> None:
        for asset in self.assets:
            asset.group_by = group_by

    def clear(self) -> None:
        self._assets.clear()
        self._value_changed()

    @property
    def issues(self) -> list[IssueModel]:
        issues = []
        for asset in self.assets:
            issues.extend(asset.issues)
        return issues

    @property
    def as_results(self) -> list[Results]:
        results = []
        for asset in self.assets:
            results.append(Results.create(asset.asset, [issue.issue for issue in asset.issues]))
        return ResultsList(results)

    @property
    def selected_issues(self) -> list[IssueModel]:
        issues = []
        for asset in self.assets:
            issues.extend(asset.selected_issues)
        return issues

    def find_issue(self, issue: Issue) -> IssueModel | None:
        for asset in self.assets:
            if model := asset.find_issue(issue):
                return model
        return None
