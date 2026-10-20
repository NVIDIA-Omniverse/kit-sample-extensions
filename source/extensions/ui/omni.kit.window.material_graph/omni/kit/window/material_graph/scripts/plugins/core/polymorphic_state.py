"""Implement material graph extension logic for `plugins/core/polymorphic_state.py`."""

from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class PolymorphicState:
    """Shared polymorphic state model for plugin/node coordination."""

    is_polymorphic: bool = False
    is_concrete: bool = True
    base_name: str = ""
    current_subidentifier: str = ""
    candidates: Tuple[str, ...] = tuple()

    def to_dict(self) -> Dict[str, Any]:
        """Execute to dict behavior for material graph workflows."""

        return {
            "is_polymorphic": self.is_polymorphic,
            "is_concrete": self.is_concrete,
            "base_name": self.base_name,
            "current_subidentifier": self.current_subidentifier,
            "candidates": self.candidates,
        }
