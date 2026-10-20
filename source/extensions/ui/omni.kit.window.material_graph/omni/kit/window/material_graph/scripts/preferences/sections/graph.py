"""Implement material graph extension logic for `preferences/sections/graph.py`."""

from omni.kit.window.preferences import SettingType

from ...settings.settings import Settings


class GraphSettingsSection:
    """Builds the Graph Settings preferences section."""

    def __init__(self, builder) -> None:
        """Initialize instance state for this material graph component."""

        self._builder = builder

    def build(self) -> None:
        """Execute build behavior for material graph workflows."""

        with self._builder.add_frame("Graph Settings"):
            with self._builder.indented_stack():
                self._builder.create_setting_widget(
                    "Confine NodeGraphs to Context",
                    Settings.CONFINE_NODEGRAPHS,
                    SettingType.BOOL,
                    tooltip="Only show NodeGraphs in the context where they have per-context positioning data.",
                )

                self._builder.create_setting_widget(
                    "Confine Backdrops to Context",
                    Settings.CONFINE_BACKDROPS,
                    SettingType.BOOL,
                    tooltip="Only show Backdrops in the context where they have per-context positioning data.",
                )

                self._builder.create_setting_widget(
                    "Default Backdrop Color",
                    Settings.BACKDROP_DEFAULT_COLOR,
                    SettingType.COLOR3,
                    tooltip="Default background color for new backdrops. Backdrops set to black will revert to this color.",
                )

                self._builder.create_setting_widget(
                    "Preview Texture Input",
                    Settings.PREVIEW_TEXTURE_INPUT,
                    SettingType.BOOL,
                    tooltip="Show a preview thumbnail from the shader's texture input when available.",
                )

                args = {
                    "tooltip": (
                        "Force nodegraph connections by ignoring property type and any metadata."
                        " Note this may result in broken materials"
                    )
                }
                self._builder.create_setting_widget("Force Connect", Settings.FORCE_CONNECT, SettingType.BOOL, **args)

                args = {
                    "tooltip": (
                        "Color connections using the port type color of the source port."
                        " When disabled, all connections are drawn in a neutral grey."
                    )
                }
                self._builder.create_setting_widget(
                    "Color Connections", Settings.COLOR_NOODLES, SettingType.BOOL, **args
                )
