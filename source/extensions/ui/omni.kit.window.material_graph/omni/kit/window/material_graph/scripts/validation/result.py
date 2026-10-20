"""Validation result model."""

from dataclasses import dataclass, field
from typing import List

from .issue import ValidationIssue
from .severity import ValidationSeverity


@dataclass
class ValidationResult:
    """Container for all validation issues produced in one validation pass."""

    context_name: str
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Return whether this result contains error-level issues."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)

    @property
    def has_warnings(self) -> bool:
        """Return whether this result contains warning-level issues."""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)

    @property
    def is_valid(self) -> bool:
        """Return True when no error-level issues are present."""
        return not self.has_errors

    @classmethod
    def ok(cls, context_name: str) -> "ValidationResult":
        """Return an empty successful validation result."""
        return cls(context_name=context_name, issues=[])

    def format_messages(self) -> List[str]:
        """Return user-facing issue lines."""
        lines = []
        for issue in self.issues:
            if issue.prim_path:
                lines.append(f"{issue.message} ({issue.prim_path})")
            else:
                lines.append(issue.message)
        return lines
