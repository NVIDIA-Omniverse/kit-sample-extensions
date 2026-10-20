"""Validation issue model."""

from dataclasses import dataclass
from typing import Optional

from .severity import ValidationSeverity


@dataclass(frozen=True)
class ValidationIssue:
    """Represents one validation issue discovered for a context/material."""

    code: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    prim_path: Optional[str] = None
    context_name: Optional[str] = None
    source_path: Optional[str] = None
    target_path: Optional[str] = None
    root_path: Optional[str] = None

    def with_context(self, context_name: str) -> "ValidationIssue":
        """Return a copy of this issue annotated with context name."""
        return ValidationIssue(
            code=self.code,
            message=self.message,
            severity=self.severity,
            prim_path=self.prim_path,
            context_name=context_name,
            source_path=self.source_path,
            target_path=self.target_path,
            root_path=self.root_path,
        )
