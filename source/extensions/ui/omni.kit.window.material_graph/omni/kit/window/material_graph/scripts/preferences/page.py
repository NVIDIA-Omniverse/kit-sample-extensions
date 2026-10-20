"""Implement material graph extension logic for `preferences/page.py`."""

import carb

# pylint: disable=no-member
import omni.ui
from omni.kit.window.preferences import PreferenceBuilder

from ..settings.settings import Settings
from .core.builder import PreferencesBuilderBase
from .sections import (
    CatalogSettingsSection,
    ExportSettingsSection,
    GeneralSettingsSection,
    GraphSettingsSection,
    PluginSettingsSection,
)


class MaterialGraphPreferences(PreferenceBuilder, PreferencesBuilderBase):
    """Builds the preferences UI for the material graph."""

    _TOP_LEVEL_FRAMES = {
        "General Settings",
        "Graph Settings",
        "Catalog Settings",
        "Plugin Settings",
        "Export Settings",
    }

    def __init__(self, window_name: str) -> None:
        """Initialize preferences builder state."""
        PreferenceBuilder.__init__(self, window_name)
        self._initialize_builder_state()

        self._general_section = GeneralSettingsSection(self)
        self._graph_section = GraphSettingsSection(self)
        self._catalog_section = CatalogSettingsSection(self)
        self._plugin_section = PluginSettingsSection(self)
        self._export_section = ExportSettingsSection(self)

    def build(self) -> None:
        """Build the preferences UI."""
        with omni.ui.VStack(height=0, spacing=self._section_spacing):
            self._general_section.build()
            self._graph_section.build()
            self._catalog_section.build()
            self._plugin_section.build()
            self._export_section.build()
        self._subscribe_settings()

    def destroy(self) -> None:
        """Release settings subscriptions and clear retained controller references during teardown."""
        if self._lifecycle:
            self._lifecycle.cleanup()
            self._lifecycle = None
        for section_name in (
            "_general_section",
            "_graph_section",
            "_catalog_section",
            "_plugin_section",
            "_export_section",
        ):
            section = getattr(self, section_name, None)
            if section:
                destroy = getattr(section, "destroy", None)
                if callable(destroy):
                    destroy()
            setattr(self, section_name, None)

    def add_frame(self, name: str) -> omni.ui.CollapsableFrame:
        """Create a UI collapsable frame."""
        collapsed = name not in self._TOP_LEVEL_FRAMES
        return omni.ui.CollapsableFrame(
            title=name,
            identifier=f"preferences_builder_{name}",
            height=0,
            collapsed=collapsed,
        )

    def _subscribe_settings(self) -> None:
        """Subscribe to settings changes that drive preference UI refreshes."""
        if not self._lifecycle or self._subscribed:
            return
        settings = carb.settings.get_settings()
        sub = settings.subscribe_to_tree_change_events(
            Settings.COMPOUND_PATHS, self._catalog_section.on_compound_paths_changed
        )
        self._lifecycle.add_unsubscribe(sub, "unsubscribe_to_tree_change_events")
        self._subscribed = True

    def get_plugin_property_factory(self):
        """Return the plugin property factory."""
        return self._plugin_section.property_factory
