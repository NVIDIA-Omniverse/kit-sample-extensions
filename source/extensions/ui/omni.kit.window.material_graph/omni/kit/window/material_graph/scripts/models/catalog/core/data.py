"""Implement material graph extension logic for `models/catalog/core/data.py`."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogItemData:
    """Lightweight catalog item metadata."""

    name: str
    info: str
    icon: str
    tooltip: str
