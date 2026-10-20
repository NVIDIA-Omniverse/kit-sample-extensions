"""Shared structured command-result type used across command wrappers."""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class CommandResult:
    """Structured command execution result."""

    success: bool
    payload: Any = None
    message: Optional[str] = None
    error_code: Optional[str] = None
    command_name: Optional[str] = None
    target_paths: Optional[Tuple[str, ...]] = None
    validation: Optional[Dict[str, Any]] = None
    warnings: Optional[Tuple[str, ...]] = None

    @property
    def ok(self) -> bool:
        """Alias for success to improve call-site readability."""
        return self.success
