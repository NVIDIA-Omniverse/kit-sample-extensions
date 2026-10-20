from typing import Optional

import carb
import carb.settings
import carb.tokens
import omni.ext
import omni.kit.app
import omni.ui as ui
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.async_engine import run_coroutine
from omni.kit.markup.core import get_instance as get_markup_instance
from omni.kit.markup.core.widgets.list_window import MarkupListWindow as ListWindow
from omni.kit.viewport.navigation.core import IMAGE_SIZE, ViewportNavigationButton, get_navigation_bar

__all__ = ["Extension"]

SETTINGS_ROOT = "/exts/omni.kit.viewport.navigation.markup/"
SETTING_PERSISTENT = "/persistent"
SETTINGS_MARKUP_ROOT = "/exts/omni.kit.markup.core/"
SETTINGS_MARKUP_ACTIVE = SETTINGS_MARKUP_ROOT + "active_markup"
SETTINGS_MARKUP_EDITING = SETTINGS_MARKUP_ROOT + "editing_markup"
WINDOW_TITLE = "Markups"
LIST_WINDOW_VIS_PATH = "/exts/omni.kit.viewport.menubar.markup/list_window_visible"


class Extension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id):
        sections = ext_id.split("-")
        self._ext_name = sections[0]

        navigation_bar = get_navigation_bar()

        self._settings = carb.settings.get_settings()

        tokens = carb.tokens.get_tokens_interface()
        icon_path = tokens.resolve(f"${{{self._ext_name}}}/icons/")
        true_image = icon_path + "navMarkup_active_dark.svg"
        false_image = icon_path + "navMarkup_dark.svg"
        order_setting = SETTINGS_ROOT + "order"
        visible_setting = SETTINGS_ROOT + "visible"
        name = "markup"
        style = {
            "Navigation.Button.Image::" + f"{name}": {"image_url": f"{false_image}"},
            "Navigation.Button.Image::" + f"{name}:checked": {"image_url": f"{true_image}"},
        }
        with navigation_bar:
            self._button = ViewportNavigationButton(
                name,
                IMAGE_SIZE,
                visible_setting_path=visible_setting,
                order_setting_path=order_setting,
                clicked_fn=self._on_click,
                build_tooltip_fn=self._build_tooltip,
                style=style,
                has_triangle=False,
            )
            self._button.set_state(False)

        self._markup_instance = get_markup_instance()
        self._list_window_instance: Optional[ListWindow] = None
        self._active_markup_setting_changed_sub = self._settings.subscribe_to_node_change_events(
            SETTINGS_MARKUP_ACTIVE, self._on_markup_setting_changed
        )
        self._editing_markup_setting_changed_sub = self._settings.subscribe_to_node_change_events(
            SETTINGS_MARKUP_EDITING, self._on_markup_setting_changed
        )
        self._stage_sub = get_eventdispatcher().observe_event(
            observer_name="omni.kit.viewport.navigation.markup:extension",
            event_name=omni.usd.get_context().stage_event_name(omni.usd.StageEventType.OPENED),
            on_event=self._on_stage,
        )

        def window_vis_changed(title: str, state: bool) -> None:
            if self._list_window_instance and self._list_window_instance.title == title:
                self._settings.set_bool(LIST_WINDOW_VIS_PATH, state)
                self._button.state = state

        ui.Workspace.set_show_window_fn(WINDOW_TITLE, self._show_window)
        self._window_vis_changed_id = ui.Workspace.set_window_visibility_changed_callback(window_vis_changed)

    def _build_tooltip(self):
        TOOLTIP_SIDE_SPACE = 5
        with ui.VStack():
            ui.Spacer(height=TOOLTIP_SIDE_SPACE)
            with ui.HStack(height=0):
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
                ui.Label("Markup", alignment=ui.Alignment.CENTER, name="shortcut")
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
        return (85, 32)

    def on_shutdown(self):
        self._button.destroy()
        self._button = None

        self.destroy()

    def destroy(self):
        self._markup_instance = None
        self._settings.unsubscribe_to_change_events(self._active_markup_setting_changed_sub)
        self._settings.unsubscribe_to_change_events(self._editing_markup_setting_changed_sub)
        self._active_markup_setting_changed_sub = None
        self._editing_markup_setting_changed_sub = None
        self._stage_sub = None
        ui.Workspace.set_show_window_fn(WINDOW_TITLE, lambda *x: None)
        ui.Workspace.remove_window_visibility_changed_callback(self._window_vis_changed_id)

    def _on_stage(self, stage_event):
        # Delay 2 frames to wait for markup.core to refresh markups
        run_coroutine(self._delay_check_markups())

    async def _delay_check_markups(self):
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        if self._markup_instance is None:
            return
        self._show_window(False)

    def _on_click(self, *_):
        self._show_window(self._button.state)

    def _show_window(self, state: bool) -> None:
        if not self._list_window_instance:
            # if ui.Workspace check is None it will make and use ListWindow()
            self._list_window_instance = ui.Workspace.get_window(WINDOW_TITLE) or ListWindow()
        self._list_window_instance.visible = state

    def _on_markup_setting_changed(self, item, event_type):
        markup_editing_name = self._settings.get(SETTINGS_MARKUP_EDITING)
        self.checked = bool(markup_editing_name)
