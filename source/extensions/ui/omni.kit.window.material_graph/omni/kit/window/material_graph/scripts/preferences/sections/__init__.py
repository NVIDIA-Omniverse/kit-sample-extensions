"""Preferences section builders for the Material Graph settings page.

This package provides section builders for general settings, graph settings,
catalog visibility, plugin options, and export defaults. Each section binds
UI controls to persistent settings and is composed into the
preferences page.

Architectural role: Section builders sit between the preferences
page layout and the settings/catalog/plugin layers. They translate
settings keys into UI controls and handle change callbacks.

Typical consumers: MaterialGraphPreferences page assembly and
tests that verify preferences persistence.
"""

from .catalog import CatalogSettingsSection
from .export import ExportSettingsSection
from .general import GeneralSettingsSection
from .graph import GraphSettingsSection
from .plugin import PluginSettingsSection

__all__ = [
    "CatalogSettingsSection",
    "ExportSettingsSection",
    "GeneralSettingsSection",
    "GraphSettingsSection",
    "PluginSettingsSection",
]
