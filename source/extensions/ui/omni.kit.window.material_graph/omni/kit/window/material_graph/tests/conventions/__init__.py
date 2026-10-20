"""Tests for project conventions and policy enforcement.

This module tests convention guards that the codebase relies on: logging policy guards ensure
that logging is done through the approved helpers and that we do not leak sensitive data or
spam logs in hot paths. We test these so that refactors or new code cannot accidentally bypass
the policy and so that the test suite itself documents the expected logging behavior."""

from .test_action_coverage import TestActionCoverageContract  # noqa: F401
from .test_logging_policy_guards import TestLoggingPolicyGuards  # noqa: F401

__all__ = [
    "TestActionCoverageContract",
    "TestLoggingPolicyGuards",
]
