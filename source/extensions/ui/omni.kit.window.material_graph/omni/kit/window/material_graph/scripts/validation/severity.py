"""Validation severity levels."""

from enum import Enum


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"
