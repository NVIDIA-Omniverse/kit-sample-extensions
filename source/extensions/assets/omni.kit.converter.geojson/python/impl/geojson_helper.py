from omni.kit.converter.geojson import _geojson_converter


# helper for plugin
class GeoJSONHelper:
    # opens module
    def __init__(self):
        self._geojson_interface = _geojson_converter.acquire_interface()

    # closes module
    def destroy(self):
        if self._geojson_interface:
            _geojson_converter.release_interface(self._geojson_interface)
            self._geojson_interface = None

    # calls extension.py
    def convert_geojson_python(self, stage_url: str, download_url: str, recursive: bool):
        # checks for user input
        return self._geojson_interface.convert_geojson_python(stage_url, download_url, recursive)
