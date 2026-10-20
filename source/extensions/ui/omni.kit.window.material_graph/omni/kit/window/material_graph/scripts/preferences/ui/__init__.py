"""Shared UI helpers for preferences sections.

This package provides reusable UI builders (build_path_list, get_list_height)
used across preferences sections. These helpers reduce duplication when
building list-based settings controls.

Architectural role: Preferences UI helpers are leaf utilities; they
produce omni.ui widgets and are consumed by section builders.

Typical consumers: CatalogSettingsSection, PluginSettingsSection,
ExportSettingsSection, and tests that verify preferences UI layout.
"""

from .lists import build_path_list, get_list_height

__all__ = [
    "build_path_list",
    "get_list_height",
]
