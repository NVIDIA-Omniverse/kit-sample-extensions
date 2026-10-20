import asyncio

import carb
import carb.settings
import omni.ext
import omni.kit.app
import omni.kit.menu.utils
import omni.usd
from omni import ui
from omni.kit.menu.utils import MenuItemDescription
from omni.kit.viewport.utility import get_active_viewport_window

from .actions import deregister_actions, register_actions
from .window import WelcomeWindowFakeModal

CURRENT_TOOL_PATH = "/app/viewport/currentTool"
MUTE_VIEWPORT_LAYERS = ("Axis", "Viewport HUD")

g_extension = None


def _iter_traverse_viewport_layers():
    vp = get_active_viewport_window()
    if hasattr(vp, "_find_viewport_layer"):
        for name in MUTE_VIEWPORT_LAYERS:
            layer = vp._find_viewport_layer(name)
            if layer:
                yield layer


def _mute_viewport_layers():
    original_visibility = {}
    for layer in _iter_traverse_viewport_layers():
        # record original visibility for the current layer
        original_visibility[layer.name] = layer.visible
        layer.visible = False
    return original_visibility


def _restore_viewport_layers(original_visibility):
    original_visibility = original_visibility or {}
    for layer in _iter_traverse_viewport_layers():
        # if not specified, restore to visible
        layer.visible = original_visibility.get(layer.name, True)


class WindowWelcomeExtension(omni.ext.IExt):

    WINDOW_NAME = "Welcome"
    MENU_PATH = f"Window/{WINDOW_NAME} Window"

    def on_startup(self, ext_id):
        self._ext_id = ext_id
        self._settings = carb.settings.get_settings()
        self._window = None
        self._stage_event_subscription = None
        self._app_name = self._settings.get_as_string("app/name")

        self.__register_menu()

        ui.Workspace.set_show_window_fn(WindowWelcomeExtension.WINDOW_NAME, self.show_window)

        # show welcome window on start up instead of on stage open
        if self._settings.get_as_bool("/app/window/showStartup"):
            # FIXME: Had to wait for one frame to show window, otherwise the viewport Axis layer visibility is turned
            #  back on for some reason (this only happend after updating kit to 104.0+release.96562.b2a4992e)
            async def _delay_show(n):
                for _ in range(n):
                    await omni.kit.app.get_app().next_update_async()
                self.show_window(True)

            asyncio.ensure_future(_delay_show(1))

        register_actions("omni.kit.usd_explorer.window.welcome", self)

        global g_extension
        g_extension = self

        self.__vp_layer_vis_store = {}

        # watch window visibility changed callback (mainly for watching the file importer from "Open" action button)
        self._visible_callback_id = ui.Workspace.set_window_visibility_changed_callback(self._on_window_visible_changed)

    def on_shutdown(self):  # pragma: no cover -- currently unused
        self.__deregister_menu()
        if self._stage_event_subscription:
            self._stage_event_subscription.reset()
            self._stage_event_subscription = None

        if self._window is not None:
            # skip visibility changed function to avoid destroying the window twice
            self._window.set_visibility_changed_fn(None)
            self._window.hide()
            self._window.destroy()
            self._window = None
        ui.Workspace.set_show_window_fn(WindowWelcomeExtension.WINDOW_NAME, None)

        deregister_actions("omni.kit.usd_explorer.window.welcome")  # , self)

        global g_extension
        g_extension = None

        self.__vp_layer_vis_store.clear()

        # remove wrindow visibility changed callback
        ui.Workspace.remove_window_visibility_changed_callback(self._visible_callback_id)

    def show_window(self, show):
        if show:
            # Destroying the window here is needed for the WelcomeWindowFakeModal background
            # Otherwise newer windows may sneak in front of it when the Welcome screen is re-opened
            if self._window is not None and not self._window.visible:
                self._window.destroy()
                self._window = None

            if self._window is None:
                self._window = WelcomeWindowFakeModal(WindowWelcomeExtension.WINDOW_NAME)
                self._window.set_visibility_changed_fn(self._visibility_changed_fn)
            self._window.show()

            # auto close window when stage opened
            self._stage_event_subscription = carb.eventdispatcher.get_eventdispatcher().observe_event(
                observer_name="omni.kit.usd_explorer.window.welcome",
                event_name=omni.usd.get_context().stage_event_name(omni.usd.StageEventType.OPENED),
                on_event=self._stage_opened,
            )
        else:
            if self._window is not None:
                self._window.hide()
                if self._stage_event_subscription:
                    self._stage_event_subscription.reset()
                    self._stage_event_subscription = None

    # -- Menu registration
    def __register_menu(self):
        self._menu_list = [
            MenuItemDescription(
                name="Welcome Window",
                ticked=False,
                onclick_action=("omni.kit.usd_explorer.window.welcome", "show_window"),
                appear_after="Sun Study",
            ),
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_list, "Window", -5)

    def __deregister_menu(self):
        omni.kit.menu.utils.remove_menu_items(self._menu_list, "Window")

    # -- event callbacks
    def _visibility_changed_fn(self, visible):
        from omni.kit.viewport.menubar.bottom import get_bottombar_name
        from omni.kit.viewport.menubar.core import get_instance as get_menubar_instance
        from omni.kit.viewport.menubar.core.viewport_menu_model import ViewportMenuModel

        # hide/show bottom menubar
        bottombar_name = get_bottombar_name()
        bottombar = get_menubar_instance().get_menubar(bottombar_name)
        bottombar.visible_model.as_bool = not visible
        ViewportMenuModel()._item_changed(None)

        # hide/show navigation bar - but not in USD Explorer
        if not self._app_name.lower().startswith("usd.explorer"):
            self._settings.set(CURRENT_TOOL_PATH, "welcome" if visible else "navigation")

        # handles viewport axis display and HUD visibility
        if visible:
            self.__vp_layer_vis_store = _mute_viewport_layers()
        else:
            _restore_viewport_layers(self.__vp_layer_vis_store)

    def _on_window_visible_changed(self, window_title: str, visible: bool):
        # we only care about the file open action, which opens up the "Open File" window
        if window_title not in ("Open File"):
            return

        # hide/show navigation bar - but not for USD Explorer
        if not self._app_name.lower().startswith("usd.explorer"):
            self._settings.set(CURRENT_TOOL_PATH, "welcome" if visible else "navigation")

    def _stage_opened(self, event):
        usd_context = omni.usd.get_context()
        stage = usd_context.get_stage()
        if stage and not stage.GetRootLayer().anonymous and usd_context.get_stage_url():
            self.show_window(False)


def get_instance():
    global g_extension
    return g_extension
