"""Toolbar action registration and invocation helpers for material graph commands."""

from functools import partial
from typing import Any, Callable, Dict

import carb.settings
from omni.kit.actions.core import get_action_registry


class ToolbarActionRegistry:
    """Registers toolbar actions and hotkeys."""

    def __init__(self, ext_name: str, window_name: str, ext_manager: Any, callbacks: Dict[str, Callable]) -> None:
        """Initialize toolbar action registry and bind command handlers for each action."""
        self._ext_name = ext_name
        self._window_name = window_name
        self._ext_manager = ext_manager
        self._callbacks = callbacks
        self._action_registry = get_action_registry()

    def setup_actions_and_hotkeys(self) -> None:
        """Register actions and hotkeys."""
        self.clear_actions_and_hotkeys()

        hotkey_registry = None
        hotkey_filter = None
        settings = carb.settings.get_settings()
        is_test_run = bool(settings.get("/app/isTestRun")) if settings else False
        if self._ext_manager.is_extension_enabled("omni.kit.hotkeys.core") and not is_test_run:
            import omni.kit.hotkeys.core as hotkeys

            hotkey_registry = hotkeys.get_hotkey_registry()
            hotkey_filter = hotkeys.HotkeyFilter(windows=[self._window_name])

        actions = [
            ("delete_nodes", self._callbacks["delete_nodes"], "Delete selected nodes", "DEL"),
            ("focus_nodes", self._callbacks["focus_nodes"], "Fit Graph View to Selected Nodes or All Nodes", "F"),
            ("layout_nodes", self._callbacks["layout_nodes"], "Layout Graph Nodes", "CTRL+L"),
            ("group_nodes", self._callbacks["group_nodes"], "Group selected nodes into a NodeGraph", "CTRL+G"),
            ("ungroup_nodegraph", self._callbacks["ungroup_nodegraph"], "Ungroup selected NodeGraph", "CTRL+U"),
            ("expand_nodes", partial(self._callbacks["expansion_state"], "open"), "Expand Graph Nodes", "KEY_1"),
            (
                "minimize_nodes",
                partial(self._callbacks["expansion_state"], "minimized"),
                "Minimize Graph Nodes",
                "KEY_2",
            ),
            ("close_nodes", partial(self._callbacks["expansion_state"], "closed"), "Close Graph Nodes", "KEY_3"),
            (
                "toggle_material_compilation",
                self._callbacks["toggle_pause"],
                "Toggle the material compilation lock state.",
                "SPACE",
            ),
            (
                "material_unpause_and_pause",
                self._callbacks["unpause_and_pause"],
                "Unpause material, allow it to compile and then pause.",
                "CTRL+R",
            ),
        ]

        existing_ids = {action.id for action in self._action_registry.get_all_actions_for_extension(self._ext_name)}
        add_action = self._action_registry.register_action
        for action_id, func, description, hotkey in actions:
            if action_id not in existing_ids:
                add_action(
                    self._ext_name,
                    action_id,
                    func,
                    display_name=action_id.replace("_", " ").title(),
                    description=description,
                    tag="Material Graph Actions",
                )
                existing_ids = {
                    action.id for action in self._action_registry.get_all_actions_for_extension(self._ext_name)
                }

            if hotkey_registry and hotkey and action_id in existing_ids:
                add_hotkey = hotkey_registry.register_hotkey
                add_hotkey(
                    hotkey_ext_id=self._ext_name,
                    key=hotkey,
                    action_ext_id=self._ext_name,
                    action_id=action_id,
                    filter=hotkey_filter,
                )

    def clear_actions_and_hotkeys(self) -> None:
        """Deregister hotkeys for the extension."""
        if self._ext_manager.is_extension_enabled("omni.kit.hotkeys.core"):
            import omni.kit.hotkeys.core as hotkeys

            hotkey_registry = hotkeys.get_hotkey_registry()
            clear_hotkeys = hotkey_registry.deregister_all_hotkeys_for_extension
            clear_hotkeys(self._ext_name)
