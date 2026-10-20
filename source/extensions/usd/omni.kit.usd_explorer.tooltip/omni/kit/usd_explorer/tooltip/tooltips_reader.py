import json

import carb

from .common import DATA_PATH


def singleton(cls):
    _instance = {}

    def inner():
        if cls not in _instance:
            _instance[cls] = cls()
        return _instance[cls]

    return inner


@singleton
class TooltipsReader(object):
    def __init__(self):
        self._all_tooltips = None
        self.load()

    def load(self):
        tooltips_file_path = f"{DATA_PATH}/tooltips.json"
        try:
            with open(tooltips_file_path, "r") as f:
                self._all_tooltips = json.load(f)
        except Exception as ex:
            carb.log_warn(f"Failed to read tooltips file. {ex}")
            self._all_tooltips = None

    def get_tooltip_by_name(self, tooltip_name):
        if self._all_tooltips:
            for tooltip in self._all_tooltips["tooltips"]:
                name = tooltip.get("name", "")
                if name == tooltip_name:
                    return (
                        tooltip.get("shortcut", ""),
                        tooltip.get("text_desc", ""),
                        tooltip.get("docs", ""),
                        tooltip.get("image_desc", ""),
                    )
        return None
