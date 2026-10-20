from typing import Any, List, Optional

import carb.settings
import omni.ui as ui
from carb.dictionary import ItemType


class SettingPathItem(ui.AbstractItem):
    """Represent a setting path"""

    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.name = path.split("/")[-1]
        self.children = []
        self._count: Optional[int] = None

    @property
    def count(self) -> int:
        if self._count is None:
            count = 0
            for child in self.children:
                if isinstance(child, SettingPathItem):
                    count += child.count
                elif child.visible:
                    count += 1
            self._count = count
        return self._count

    def refresh(self) -> None:
        self._count = None


class SettingValueItem(ui.AbstractItem):
    """Represent a setting with path and value"""

    def __init__(self, path: str, setting_type: ItemType, value: Any):
        super().__init__()
        self.path = path
        self.setting_type = setting_type
        self.value = value
        self.name = path.split("/")[-1]
        self.children = []
        self.visible = True

        self.value_models = []
        self.value_subs = []

    def create_sub_value_models(self) -> List[ui.AbstractValueModel]:
        for sub_value in self.value:
            if isinstance(sub_value, str):
                value_model = ui.SimpleStringModel(sub_value)
            elif isinstance(sub_value, int):
                value_model = ui.SimpleIntModel(sub_value)
            elif isinstance(sub_value, float):
                value_model = ui.SimpleFloatModel(sub_value)
            elif isinstance(sub_value, bool):
                value_model = ui.SimpleBoolModel(sub_value)
            else:
                carb.log_warn(f" Unknown value {type(sub_value)}: {sub_value} from {self.path}")
            self.value_models.append(value_model)
            self.value_subs.append(value_model.subscribe_value_changed_fn(self._on_sub_value_changed))

        return self.value_models

    def _on_sub_value_changed(self, *args) -> None:
        self.value = []
        for model in self.value_models:
            if isinstance(model, ui.SimpleStringModel):
                self.value.append(model.as_string)
            elif isinstance(model, ui.SimpleIntModel):
                self.value.append(model.as_int)
            elif isinstance(model, ui.SimpleFloatModel):
                self.value.append(model.as_float)
            elif isinstance(model, ui.SimpleBoolModel):
                self.value.append(model.as_bool)

        carb.settings.get_settings().set(self.path, self.value)


class SettingsModel(ui.AbstractItemModel):
    """Model for all settings"""

    def __init__(self):
        super().__init__()

        self._settings = carb.settings.get_settings()
        self._dictionary = carb.dictionary.get_dictionary()
        self._items = None

        self._filter_path = None
        self.filter_suggestions = []
        self.max_suggestions = 10

    def get_item_children(self, item: Optional[ui.AbstractItem] = None) -> List[ui.AbstractItem]:
        if self._items is None:
            self.__settings_dict = self._settings.get_settings_dictionary("")
            self.__populate_settings(None, self.__settings_dict.get_dict())

        return self._items if item is None else item.children

    def get_item_value_model_count(self, item) -> int:
        return 2

    def get_item_value_model(self, item, column) -> ui.AbstractValueModel:
        if column == 0:
            return ui.SimpleStringModel(item.name)
        else:
            return ui.SimpleIntModel(item.setting_type) if isinstance(item, SettingValueItem) else None

    def filter_settings(self, path: Optional[str]) -> None:
        self._filter_path = path
        self._refresh()

    def update_setting(self, path: str, value: str) -> None:
        prev_value = self._settings.get(path)
        if isinstance(prev_value, bool):
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            else:
                try:
                    value = bool(value)
                except ValueError:
                    carb.log_warn(f"Cannot convert {value} to bool for {path}")
                    return
        elif isinstance(prev_value, int):
            try:
                value = int(value)
            except ValueError:
                carb.log_warn(f"Cannot convert {value} to integer for {path}")
                return
        elif isinstance(prev_value, float):
            try:
                value = float(value)
            except ValueError:
                carb.log_warn(f"Cannot convert {value} to float for {path}")
                return

        self._settings.set(path, value)

        if prev_value is None:
            self._refresh()

    def _refresh(self):
        self._items = None
        self.filter_suggestions = []
        self._item_changed(None)

    def __populate_settings(self, item, item_dict) -> None:
        children = []
        path = "" if item is None else item.path
        for key, value in sorted(item_dict.items()):
            full_path = path + "/" + key
            if isinstance(value, dict) and value.items():
                path_item = SettingPathItem(full_path)
                self.__populate_settings(path_item, value)
                if path_item.children:
                    children.append(path_item)
            else:
                if (
                    self._filter_path
                    and (self._filter_path not in full_path and full_path not in self._filter_path)
                    and item is not None
                ):
                    continue
                setting_type = self._get_setting_type(full_path)
                if isinstance(value, tuple) or isinstance(value, list):
                    has_tuple_in_children = False
                    has_dict_in_children = False
                    # If children are still tuple, split into several settings such as {$path}/0, {$path}/1
                    for index, sub_value in enumerate(value):
                        if isinstance(sub_value, tuple) or isinstance(sub_value, list):
                            has_tuple_in_children = True
                            break
                        if isinstance(sub_value, dict):
                            has_dict_in_children = True
                    if has_tuple_in_children:
                        # /app/key = ["a", "b"]
                        # Two items:
                        # /app/key/0: "a"
                        # /app/key/1: "b"
                        path_item = SettingPathItem(full_path)
                        children.append(path_item)
                        for index, sub_value in enumerate(value):
                            if isinstance(sub_value, tuple) or isinstance(sub_value, list):
                                sub_path = full_path + f"/{index}"
                                setting_type = self._get_setting_type(sub_path)
                                self._add_suggestion(path)
                                path_item.children.append(SettingValueItem(path, setting_type, sub_value))
                    elif has_dict_in_children:
                        # /app/key = [{"a": "b", "c": "d"}]
                        # Two items:
                        # /app/key/0/a: "b"
                        # /app/key/0/c: "d"
                        path_item = SettingPathItem(full_path)
                        children.append(path_item)
                        for index, sub_value in enumerate(value):
                            if isinstance(sub_value, dict):
                                sub_path = full_path + f"/{index}"
                                sub_path_item = SettingPathItem(sub_path)
                                path_item.children.append(sub_path_item)
                                for _key, _value in sub_value.items():
                                    _sub_path = sub_path + f"/{_key}"
                                    setting_type = self._get_setting_type(_sub_path)
                                    self._add_suggestion(_sub_path)
                                    sub_path_item.children.append(SettingValueItem(_sub_path, setting_type, _value))
                    else:
                        children.append(SettingValueItem(full_path, setting_type, value))
                else:
                    if not self._filter_path or self._filter_path in full_path:
                        self._add_suggestion(full_path)
                        children.append(SettingValueItem(full_path, setting_type, value))

        def sort_path_first(item):
            return not isinstance(item, SettingPathItem)

        children.sort(key=sort_path_first)
        if item is None:
            self._items = children
        else:
            item.children = children

    def _get_sanitized_path(self, path: str) -> str:
        if path is not None and len(path) > 0 and path[0] == "/":
            return path[1:]
        return ""

    def _get_setting_type(self, path: str) -> ItemType:
        path = self._get_sanitized_path(path)
        item = self._dictionary.get_item(self.__settings_dict, path)
        return self._dictionary.get_item_type(item)

    def _add_suggestion(self, path: str) -> None:
        if (
            self._filter_path
            and path.startswith(self._filter_path)
            and len(self.filter_suggestions) < self.max_suggestions
        ):
            self.filter_suggestions.append(path)
