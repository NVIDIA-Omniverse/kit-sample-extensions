"""Implement material graph extension logic for `preferences/sections/export.py`."""

import carb.settings
from omni.kit.window.preferences import SettingType

from ...settings.settings import Settings
from ...settings.utils import COMPOUND_DEFAULT_PATH


class ExportSettingsSection:
    """Builds the Export Settings preferences section."""

    def __init__(self, builder) -> None:
        """Initialize instance state for this material graph component."""

        self._builder = builder

    def build(self) -> None:
        """Execute build behavior for material graph workflows."""

        settings = carb.settings.get_settings()
        value = settings.get(Settings.COMPOUND_DEFAULT_EXPORT_PATH)
        if value is None or (isinstance(value, str) and "${" in value):
            settings.set_string(Settings.COMPOUND_DEFAULT_EXPORT_PATH, COMPOUND_DEFAULT_PATH)
        with self._builder.add_frame("Export Settings"):
            with self._builder.indented_stack():
                self._builder.create_setting_widget(
                    "Compound Default Export Path",
                    Settings.COMPOUND_DEFAULT_EXPORT_PATH,
                    SettingType.ASSET,
                    tooltip="Default directory used when exporting compound graphs.",
                )
