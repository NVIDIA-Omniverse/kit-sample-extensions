"""Typed result payload for export operations and diagnostics."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ExportResult:
    """Structured export result for graph export operations, including status and optional payload details."""

    success: bool
    message: str
    source_path: Optional[str] = None
    target_path: Optional[str] = None
