"""Dataclass model describing a discoverable compound source asset and prim."""

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class CompoundSource:
    """Metadata for a compound source file and prim."""

    source_asset: str
    identifier: str
    display_name: str
    description: str
    category: str
    icon: str
    ui_order: Optional[int]
    context_visibility: Sequence[str]
