import omni.ext
from omni.kit.widgets.custom import WindowExtension

from .geojson_converter_window_base import GeoJSONWindow

EXTENSION_NAME = "GeoJSON Converter (beta)"
_geojson_instance = None  # Singleton approach


# Use extension entry points to acquire and release interface.
class Extension(omni.ext.IExt, WindowExtension):
    TOOL_NAME = "GeoJSONConverter"

    def on_startup(self, ext_id):
        super().on_startup(menu_path=f"Window/{EXTENSION_NAME}", appear_after="Stage", use_editor_menu=True)
        global _geojson_instance  # needed for proper startup and shutdown
        _geojson_instance = self

    def on_shutdown(self):
        super().on_shutdown()
        global _geojson_instance
        _geojson_instance = None

    def _create_window(self):
        self._geojson_window = GeoJSONWindow()
        return self._geojson_window


def get_instance():
    global _geojson_instance
    return _geojson_instance
