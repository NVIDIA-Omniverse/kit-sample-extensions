# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import omni.kit.test
from omni.asset_validator.core import AssetType, BaseRuleChecker, IssuePredicate
from omni.asset_validator.tests import (
    AsyncioValidationTestCaseMixin,
    Failure,
    IsAFailure,
    IsAnError,
    IsAnIssue,
    IsAWarning,
    ValidationTestCaseMixin,
)

__all__ = ["Failure", "IsAFailure", "IsAWarning", "IsAnError", "ValidationRuleTestCase"]


class ValidationRuleTestCase(omni.kit.test.AsyncTestCase, ValidationTestCaseMixin):
    """
    Specific implementation of ValidationTestCaseMixin for core tests.
    """

    def assertRule(
        self,
        *,
        rule: type[BaseRuleChecker],
        asserts: list[IsAnIssue],
        asset: AssetType | None = None,
        url: str | None = None,
    ) -> None:
        """
        Args:
            rule: The rule to use for validation.
            asserts: A list of assertions.
            asset: The asset to validate.
            url: (Deprecated) Use asset instead.
        """
        super().assertRule(asset=asset or url, rule=rule, asserts=asserts)

    def assertRuleFailures(
        self,
        *,
        rule: type[BaseRuleChecker],
        expectedFailures: list[IsAFailure],
        asset: AssetType | None = None,
        url: str | None = None,
    ) -> None:
        """
        Args:
            rule: The rule to use for validation.
            expectedFailures: A list of expected failures.
            asset: The asset to validate.
            url: (Deprecated) Use asset instead.
        """
        super().assertRuleFailures(asset=asset or url, rule=rule, expectedFailures=expectedFailures)

    def assertSuggestion(
        self,
        *,
        rule: type[BaseRuleChecker],
        predicate: IssuePredicate | None = None,
        asset: AssetType | None = None,
        url: str | None = None,
    ) -> None:
        """
        Args:
            rule: The rule to use for validation.
            predicate: The predicate to use for validation.
            asset: The asset to validate.
            url: (Deprecated) Use asset instead.
        """
        super().assertSuggestion(asset=asset or url, rule=rule, predicate=predicate)


class AsyncValidationRuleTestCase(omni.kit.test.AsyncTestCase, AsyncioValidationTestCaseMixin):
    """
    Specific implementation of AsyncioValidationTestCaseMixin for core tests.
    """
