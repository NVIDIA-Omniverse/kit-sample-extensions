import asyncio

import carb.settings
import omni.ext
import omni.kit.app
import omni.kit.menu.utils
import omni.ui
from omni.kit.actions.core import get_action_registry


class Extension(omni.ext.IExt, omni.kit.menu.utils.MenuHelperExtension):
    MENU_NAME = "Developer"
    DEBUG_SETTINGS_VISIBILITY_SETTINGS_PATH = "exts/omni/kit/debug/settings/visibility"

    ACTION_TAG = "Developer Utilities Actions"
    DEBUG_SETTINGS_ACTION_ID = "Show Debug Settings"

    def on_startup(self, ext_id: str) -> None:
        self._ext_name = omni.ext.get_extension_name(ext_id)
        self._settings = carb.settings.get_settings()

        self._vsc_link_window = omni.ui.Workspace.get_window("VS Code Link")

        self._register_actions()

        self._sub_id = self._settings.subscribe_to_node_change_events(
            self.DEBUG_SETTINGS_VISIBILITY_SETTINGS_PATH, self._debug_settings_visibility_setting_node_callback
        )

        # Creating a menu entry for Debug Settings, as it does not create one itself.
        self._debug_menu_item = omni.kit.menu.utils.MenuItemDescription(
            "Debug Settings",
            enabled=True,
            ticked=False,
            ticked_value=False,
            ticked_fn=self._debug_settings_menu_tick_change,
            onclick_action=(self._ext_name, self.DEBUG_SETTINGS_ACTION_ID),
        )

        # TODO: How to put the MenuItemDescription items in the add_layout() block below and not have to do this
        # song and dance of adding them and then moving them?
        omni.kit.menu.utils.add_menu_items([self._debug_menu_item], self.MENU_NAME, 0)

        self._menu_layout = [
            omni.kit.menu.utils.MenuLayout.Menu(
                self.MENU_NAME,
                [
                    # The Extensions extension adds a menu separator below its menu item. AFAIK this
                    # cannot be removed outside of editing that extension's code. I moved the menu entry
                    # to the top to minimize the visual incongruity of the separator.
                    omni.kit.menu.utils.MenuLayout.Item("Extensions", source="Window/Extensions"),
                    omni.kit.menu.utils.MenuLayout.Item("Commands", source="Window/Commands"),
                    omni.kit.menu.utils.MenuLayout.Item("Script Editor", source="Window/Script Editor"),
                    omni.kit.menu.utils.MenuLayout.Item("VS Code Link", source=f"Window/VS Code Link"),
                    omni.kit.menu.utils.MenuLayout.Item("Debug Settings", source=f"{self.MENU_NAME}/Debug Settings"),
                ],
            ),
        ]
        omni.kit.menu.utils.add_layout(self._menu_layout)

        self._window_visibility_changed_id = omni.ui.Workspace.set_window_visibility_changed_callback(
            self._window_visibility_changed
        )
        omni.kit.menu.utils.rebuild_menus()

    def _register_actions(self):
        action_registry = get_action_registry()
        action_registry.register_action(
            self._ext_name,
            "Show Debug Settings",
            self.debug_settings_vis_toggle,
            display_name="Debug Settings",
            description="Show the Debug Settings window",
            tag=self.ACTION_TAG,
        )

    def _debug_settings_visibility_setting_node_callback(self, *args):
        vis = self._settings.get_as_bool(self.DEBUG_SETTINGS_VISIBILITY_SETTINGS_PATH)
        self._debug_menu_item.ticked = vis
        omni.kit.menu.utils.refresh_menu_items(self.MENU_NAME)

    def _debug_settings_menu_tick_change(self, *args):
        return self._settings.get_as_bool(self.DEBUG_SETTINGS_VISIBILITY_SETTINGS_PATH)

    def on_shutdown(self):
        self._settings.unsubscribe_to_change_events(self._sub_id)
        omni.ui.Workspace.remove_window_visibility_changed_callback(self._window_visibility_changed_id)
        self._window_visibility_changed_id = None
        omni.kit.menu.utils.remove_menu_items([self._debug_menu_item], self.MENU_NAME, 0)
        omni.kit.menu.utils.remove_layout(self._menu_layout)
        self._menu_layout = None
        get_action_registry().deregister_all_actions_for_extension(self._ext_name)
        self._settings = None
        self._vsc_link_window = None

    def debug_settings_vis_toggle(self, *args):
        self._settings.set_bool(
            self.DEBUG_SETTINGS_VISIBILITY_SETTINGS_PATH,
            (not self._settings.get_as_bool(self.DEBUG_SETTINGS_VISIBILITY_SETTINGS_PATH)),
        )

    # TODO: Because moving a menu item under a new group does not update the menu group the item should refresh
    # when closing the window manually, this function is the catch all until the API is updated for regrouping.
    def _window_visibility_changed(self, window_name: str, _: bool):
        async def update():
            await omni.kit.app.get_app().next_update_async()
            omni.kit.menu.utils.refresh_menu_items(self.MENU_NAME)

        if window_name in ["Debug Settings", "VS Code Link", "Extensions", "Commands", "Script Editor"]:
            asyncio.ensure_future(update())
