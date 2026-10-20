# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar

from omni.asset_validator.core import Issue, IssueGroupBy, Requirement
from omni.ui import SimpleStringModel

__all__ = ["GroupByModel", "GroupByOption", "GroupByRequirement", "GroupByRule"]


class GroupByOption(str, Enum):
    RULE = "rule"
    """
    Group by rule name.
    """
    REQUIREMENT = "requirement"
    """
    Group by requirement code.
    """


@dataclass(frozen=True)
class GroupByRule(IssueGroupBy):
    """
    Group by rule name.
    """

    NO_RULE: ClassVar[str] = "No rule"

    def __call__(self, issues: list[Issue]) -> list[tuple[Any, Issue]]:
        def map_fn(issue: Issue) -> tuple[str, Issue]:
            rule_name: str = issue.rule.__name__ if issue.rule else self.NO_RULE
            return rule_name, issue

        return list(map(map_fn, issues))


@dataclass(frozen=True)
class GroupByRequirement(IssueGroupBy):
    """
    Group by requirement code.
    """

    NO_REQUIREMENT: ClassVar[str] = "No requirement"

    def __call__(self, issues: list[Issue]) -> list[tuple[Any, Issue]]:
        def map_fn(issue: Issue) -> tuple[str, Issue]:
            requirement: Requirement | None = issue.requirement
            if requirement is None:
                return self.NO_REQUIREMENT, issue
            requirement_name: str = requirement.display_name or requirement.code
            return requirement_name, issue

        return list(map(map_fn, issues))


class GroupByModel(SimpleStringModel):
    def __init__(self):
        super().__init__(GroupByOption.RULE.value)

    @property
    def rule(self) -> bool:
        return self.get_value_as_string() == GroupByOption.RULE.value

    @rule.setter
    def rule(self, value: bool) -> None:
        self.set_value(GroupByOption.RULE.value if value else GroupByOption.REQUIREMENT.value)

    @property
    def requirement(self) -> bool:
        return self.get_value_as_string() == GroupByOption.REQUIREMENT.value

    @requirement.setter
    def requirement(self, value: bool) -> None:
        self.set_value(GroupByOption.REQUIREMENT.value if value else GroupByOption.RULE.value)

    @property
    def group_by(self) -> IssueGroupBy:
        return GroupByRule() if self.rule else GroupByRequirement()
