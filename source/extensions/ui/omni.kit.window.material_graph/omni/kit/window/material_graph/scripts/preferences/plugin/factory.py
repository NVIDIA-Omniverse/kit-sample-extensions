"""Implement material graph extension logic for `preferences/plugin/factory.py`."""

from typing import Any, Dict, List, Optional

# pylint: disable=no-member
import omni.ui
from omni.kit.window.preferences import SettingType

from ...config.logging import logger
from ...settings.settings import Settings
from ..core.constants import BUTTON_WIDTH
from ..ui.lists import get_list_height


class PluginPropertyWidgetFactory:
    """Builds plugin property widgets and manages their state."""

    def __init__(self, builder) -> None:
        """Initialize the widget factory with a preference builder."""
        self._builder = builder
        self._list_stacks: Dict[str, Dict[str, Any]] = {}
        self._builders = {
            "bool": self._build_bool,
            "string": self._build_string,
            "string_list": self._build_string_list,
        }

    def build(self, definitions: List[Dict[str, Any]]) -> None:
        """Build UI for plugin-defined properties."""
        for definition in definitions:
            properties = definition.get("properties", [])
            if not properties:
                continue
            with self._builder.add_frame(definition["display_name"]):
                with omni.ui.VStack():
                    for prop in properties:
                        self._build_property(definition["name"], prop)

    def _build_property(self, plugin_name: str, prop: Dict[str, Any]) -> None:
        """Dispatch property construction to the appropriate builder."""
        if plugin_name == "mdl" and prop.get("key") == "modules":
            self._build_mdl_modules(plugin_name, prop)
            return
        prop_type = prop.get("type", "string")
        builder = self._builders.get(prop_type)
        if builder:
            builder(plugin_name, prop)
        else:
            logger.warning("unknown plugin property type: %s.%s type=%s", plugin_name, prop.get("key"), prop_type)

    def _get_setting_key(self, plugin_name: str, key: str) -> Optional[str]:
        """Return the plugin property setting key or log when missing."""
        setting_key = Settings.get_plugin_property_key(plugin_name, key)
        if not setting_key:
            logger.warning("missing plugin setting key: %s.%s", plugin_name, key)
        return setting_key

    def _build_bool(self, plugin_name: str, prop: Dict[str, Any]) -> None:
        """Build a boolean setting widget."""
        key = prop["key"]
        label = prop.get("label", key)
        tooltip = prop.get("description", "")
        setting_key = self._get_setting_key(plugin_name, key)
        if not setting_key:
            return
        self._builder.create_setting_widget(
            label,
            setting_key,
            SettingType.BOOL,
            tooltip=tooltip,
        )

    def _build_string(self, plugin_name: str, prop: Dict[str, Any]) -> None:
        """Build a string setting widget."""
        key = prop["key"]
        label = prop.get("label", key)
        tooltip = prop.get("description", "")
        setting_key = self._get_setting_key(plugin_name, key)
        if not setting_key:
            return
        self._builder.create_setting_widget(
            label,
            setting_key,
            SettingType.STRING,
            tooltip=tooltip,
        )

    def _build_string_list(self, plugin_name: str, prop: Dict[str, Any]) -> None:
        """Build a list-of-strings setting widget."""
        key = prop["key"]
        stack_key = f"{plugin_name}:{key}"
        label = prop.get("label", key)
        frame = self._builder.add_frame(label)
        tooltip = prop.get("description", "")
        if tooltip:
            set_tooltip = getattr(frame, "set_tooltip", None)
            if callable(set_tooltip):
                set_tooltip(tooltip)
        with frame:
            stack = omni.ui.VStack(height=0)
        self._list_stacks[stack_key] = {"frame": frame, "stack": stack, "plugin": plugin_name, "prop": prop}
        self._refresh_list_property(stack_key)

    def _build_mdl_modules(self, plugin_name: str, prop: Dict[str, Any]) -> None:
        """Build the MDL modules list widget."""
        key = prop["key"]
        stack_key = f"{plugin_name}:{key}"
        frame = self._builder.add_frame("Modules")
        tooltip = prop.get("description", "")
        if tooltip:
            set_tooltip = getattr(frame, "set_tooltip", None)
            if callable(set_tooltip):
                set_tooltip(tooltip)
        with frame:
            stack = omni.ui.VStack(height=0)
        self._list_stacks[stack_key] = {
            "frame": frame,
            "stack": stack,
            "plugin": plugin_name,
            "prop": prop,
            "kind": "mdl_modules",
        }
        self._refresh_mdl_modules(stack_key)

    def _refresh_list_property(self, stack_key: str) -> None:
        """Rebuild the list UI for a list-valued setting."""
        entry = self._list_stacks.get(stack_key)
        if not entry:
            return
        if entry.get("kind") == "mdl_modules":
            self._refresh_mdl_modules(stack_key)
            return
        stack = entry["stack"]
        plugin_name = entry["plugin"]
        prop = entry["prop"]
        key = prop["key"]
        default = prop.get("default")
        current = Settings.get_plugin_property(plugin_name, key, default) or []
        if entry.get("current") == current:
            return
        entry["current"] = list(current)
        stack.clear()
        with stack:
            with omni.ui.HStack():
                indent = getattr(self._builder, "indent", 0)
                if indent:
                    omni.ui.Spacer(width=indent)
                with omni.ui.VStack(height=0, spacing=self._builder.item_spacing):
                    new_path_model = omni.ui.SimpleStringModel("")
                    with omni.ui.HStack():
                        omni.ui.StringField(new_path_model, height=self._builder.row_height)
                        omni.ui.Button(
                            "Add",
                            clicked_fn=lambda m=new_path_model, k=stack_key: self._on_add_list_item(k, m),
                            height=self._builder.row_height,
                            width=BUTTON_WIDTH,
                        )
                    omni.ui.Spacer(height=self._builder.item_spacing)
                    for item in current:
                        with omni.ui.HStack():
                            omni.ui.Label(str(item))
                            omni.ui.Button(
                                "Remove",
                                clicked_fn=lambda v=item, k=stack_key: self._on_remove_list_item(k, v),
                                height=self._builder.row_height,
                                width=BUTTON_WIDTH,
                            )

    def _refresh_mdl_modules(self, stack_key: str) -> None:
        """Rebuild the MDL module list UI."""
        entry = self._list_stacks.get(stack_key)
        if not entry:
            return
        stack = entry["stack"]
        current = Settings.get_mdl_catalog_modules()
        if entry.get("current") == current:
            return
        entry["current"] = list(current)
        stack.clear()
        with stack:
            with omni.ui.VStack(height=0, spacing=self._builder.item_spacing):
                new_path_model = omni.ui.SimpleStringModel("")
                with omni.ui.HStack(height=self._builder.row_height):
                    omni.ui.StringField(new_path_model, height=self._builder.row_height)
                    omni.ui.Button(
                        "Add",
                        clicked_fn=lambda m=new_path_model, k=stack_key: self._on_add_list_item(k, m),
                        height=self._builder.row_height,
                        width=BUTTON_WIDTH,
                    )
                list_height = get_list_height(self._builder, len(current))
                with omni.ui.ScrollingFrame(
                    height=list_height,
                    vertical_scrollbar_policy=omni.ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                    horizontal_scrollbar_policy=omni.ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                ):
                    with omni.ui.VStack(height=0, spacing=self._builder.item_spacing):
                        for item in current:
                            with omni.ui.HStack(height=self._builder.row_height):
                                omni.ui.Label(str(item), height=self._builder.row_height, width=0)
                                omni.ui.Spacer()
                                omni.ui.Button(
                                    "Remove",
                                    clicked_fn=lambda v=item, k=stack_key: self._on_remove_list_item(k, v),
                                    height=self._builder.row_height,
                                    width=BUTTON_WIDTH,
                                )

    def _on_add_list_item(self, stack_key: str, model: Any) -> None:
        """Add a new list item from the provided text model."""
        entry = self._list_stacks.get(stack_key)
        if not entry:
            return
        if entry.get("kind") == "mdl_modules":
            self._on_add_mdl_module(stack_key, model)
            return
        plugin_name = entry["plugin"]
        prop = entry["prop"]
        key = prop["key"]
        default = prop.get("default")
        value = model.get_value_as_string().strip()
        if not value:
            return
        current = Settings.get_plugin_property(plugin_name, key, default) or []
        existing = {str(item).strip().lower() for item in current}
        if value.lower() not in existing:
            current.append(value)
            Settings.set_plugin_property(plugin_name, key, current)
        model.set_value("")
        self._builder.schedule_refresh(lambda: self._refresh_list_property(stack_key))

    def _on_remove_list_item(self, stack_key: str, value: Any) -> None:
        """Remove a list item for a given setting."""
        entry = self._list_stacks.get(stack_key)
        if not entry:
            return
        if entry.get("kind") == "mdl_modules":
            self._on_remove_mdl_module(stack_key, value)
            return
        plugin_name = entry["plugin"]
        prop = entry["prop"]
        key = prop["key"]
        default = prop.get("default")
        current = Settings.get_plugin_property(plugin_name, key, default) or []
        if value in current:
            current.remove(value)
            Settings.set_plugin_property(plugin_name, key, current)
        self._builder.schedule_refresh(lambda: self._refresh_list_property(stack_key))

    def _on_add_mdl_module(self, stack_key: str, model: Any) -> None:
        """Add a MDL module path from the input model."""
        value = model.get_value_as_string().strip()
        if not value:
            return
        before = set(Settings.get_mdl_catalog_modules())
        Settings.add_mdl_catalog_module(value)
        after = set(Settings.get_mdl_catalog_modules())
        if value not in after and value not in before:
            logger.warning("mdl module rejected: %s", value)
        model.set_value("")
        self._builder.schedule_refresh(lambda: self._refresh_mdl_modules(stack_key))

    def _on_remove_mdl_module(self, stack_key: str, value: Any) -> None:
        """Remove a MDL module path."""
        Settings.remove_mdl_catalog_module(str(value))
        self._builder.schedule_refresh(lambda: self._refresh_mdl_modules(stack_key))
