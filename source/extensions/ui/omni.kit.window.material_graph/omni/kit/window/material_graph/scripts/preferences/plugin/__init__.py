"""Plugin-preferences helpers for property widget construction.

This package provides the PluginPropertyWidgetFactory used to build
UI controls for plugin-specific settings (e.g., MDL search paths,
MaterialX options). The factory produces stack-based list editors
and binds them to plugin property models.

Architectural role: Plugin preferences are a leaf UI layer; they
depend on plugin property models and preferences constants but
are consumed by the preferences page builder.

Typical consumers: PluginSettingsSection, preferences page assembly,
and tests that verify plugin settings UI.
"""

from .factory import PluginPropertyWidgetFactory

__all__ = ["PluginPropertyWidgetFactory"]
