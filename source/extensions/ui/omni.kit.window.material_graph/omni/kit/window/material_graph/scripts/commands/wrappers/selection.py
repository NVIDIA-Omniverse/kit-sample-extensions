"""Selection command wrappers that return normalized structured command results."""

from typing import Optional, Sequence

from ..execution import execute_command_checked
from ..result import CommandResult


def SelectPrims(old: Optional[Sequence[str]], new: Optional[Sequence[str]]) -> CommandResult:
    """Update selection and return structured result."""
    return execute_command_checked(
        "SelectPrimsCommand",
        old_selected_paths=old,
        new_selected_paths=new,
        expand_in_stage=True,
    )
