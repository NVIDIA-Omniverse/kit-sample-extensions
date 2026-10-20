"""Validation framework for material graph context health.

This package owns the extension's context-scoped validation contract and runtime
orchestration. It is intentionally separated from UI/controller code so the same
rules can be reused at material load time, during edit-time revalidation, and in
tests without coupling to view state.

The package provides:

- Data contracts:
  - ``ValidationSeverity`` for severity levels.
  - ``ValidationIssue`` for individual validation findings.
  - ``ValidationResult`` for grouped per-context outcomes.
- Execution services:
  - ``MaterialValidator`` for orchestration, callback subscriptions, and
    ``can_connect`` compatibility caching.
  - ``validate_material_context`` pipeline logic for core graph checks plus
    plugin-provided rule extensions.
- Runtime wiring helpers:
  - validator registry helpers used by legacy callsites that still resolve a
    validator via USD context identity during migration.

Design goals:

- Context-aware traversal from material outputs so checks operate only on the
  active network rather than unrelated scene prims.
- Deterministic issue reporting that can drive both error and warning UI states.
- Extensible plugin hook points with a stable internal contract.
- Minimal defensive indirection in internal paths, with explicit typing and
  direct attribute access for known model/plugin interfaces.
"""

from .issue import ValidationIssue
from .result import ValidationResult
from .severity import ValidationSeverity

__all__ = [
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationResult",
]
