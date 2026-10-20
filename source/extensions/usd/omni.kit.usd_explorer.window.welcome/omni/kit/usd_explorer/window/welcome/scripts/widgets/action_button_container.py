import asyncio
import webbrowser

import carb.settings
import omni.client
import omni.kit.actions.core
import omni.kit.app
import omni.kit.window.file
import omni.usd
from omni import ui
from omni.kit.window.about import get_instance as get_about_instance

from ..styles import ACTION_BUTTON_STYLE, ACTION_LABEL_STYLE
from .utils import get_icon_path

# XXX this string constant is duplicated between here and omni.kit.usd_explorer.main.menubar
SETTINGS_APPLICATION_MODE_PATH = "/app/application_mode"


class ActionButtonItem:
    """A single action button item"""

    def __init__(self, name, icon_name, clicked_fn, identifier, width=ui.Fraction(1)) -> None:
        self._button = self._build_item(name, icon_name, clicked_fn, identifier, width=width)

    def destroy(self):
        self._button = None

    def _build_item(self, name, icon_name, clicked_fn, identifier, width=0):
        with ui.VStack(width=width):
            with ui.ZStack(style=ACTION_BUTTON_STYLE):
                button = ui.Rectangle(
                    style_type_name_override="Button",
                    name=name,
                    mouse_released_fn=lambda x, y, b, a, c=clicked_fn: b == 0 and c(),
                    identifier=identifier,
                )
                ui.ImageWithProvider(
                    get_icon_path(icon_name),
                    style_type_name_override="Button",
                    name=name,
                )
            ui.Spacer(height=5)
            with ui.HStack(height=0):
                ui.Spacer()
                ui.Label(name, width=ui.Percent(100), elided_text=True, style=ACTION_LABEL_STYLE)
                ui.Spacer()
        return button


class ActionButtonContainer:
    """A container containing action button items."""

    def __init__(self, window) -> None:
        self._items = []
        self._window = window
        self._docs_url = carb.settings.get_settings().get_as_string("exts/omni.kit.usd_explorer.window.welcome/docsURL")
        if self._docs_url:
            self._docs_url = f"https://docs.omniverse.nvidia.com/{self._docs_url}"
        self._build_ui()

        self._open_stage_subscription = omni.kit.window.file.register_open_stage_addon(self._on_open_stage)

    def destroy(self):
        for item in self._items:
            item.destroy()
        self._items.clear()
        self._window = None
        self._open_stage_subscription = None

    def _build_ui(self):
        with ui.HStack(height=ui.Percent(60)):
            ui.Spacer(width=ui.Percent(20))
            self._items = [
                ActionButtonItem("Open", "Open.png", self._on_browse_fn, "welcome_window_open_action_btn"),
                # ActionButtonItem("About", "nvidia-omniverse-viewer-icon-256x256.png", self._on_about_fn, "welcome_window_about_action_btn"),
                ActionButtonItem("New", "Modify.png", self._on_new_fn, "welcome_window_modify_action_btn"),
            ]
            if self._docs_url:
                self._items.insert(
                    1, ActionButtonItem("Learn", "Learn.png", self._on_learn_fn, "welcome_window_learn_action_btn")
                )
            ui.Spacer(width=ui.Percent(20))

    def _on_open_stage(self):
        # If we opened a file, close the welcome window.
        if self._window:
            self._window.hide()

    def _on_browse_fn(self):
        # NOTE: this function will not hide the welcome window, but _on_open_stage will
        # in the event that the user opens a file from the dialog launched by this action.
        omni.kit.actions.core.execute_action("omni.kit.window.file", "open")

    def _on_learn_fn(self):
        # FIXME: Do we want to hide the welcome window after clicking on Learn?
        webbrowser.open(self._docs_url)

    def _on_about_fn(self):  # pragma: no cover -- currently unused
        async def __prevent_window_collapse(about_window_ext):
            await omni.kit.app.get_app().next_update_async()  # type: ignore

            if about_window_ext._window is not None:
                about_window_ext._window.flags |= ui.WINDOW_FLAGS_NO_COLLAPSE

        if self._window:
            self._window.hide()

        about_window_ext = get_about_instance()
        asyncio.ensure_future(__prevent_window_collapse(about_window_ext))

        if about_window_ext:
            about_window_ext.toggle_window()

    def _on_new_fn(self):
        settings = carb.settings.get_settings()
        layout_mode = "layout"
        current_mode = settings.get_as_string(SETTINGS_APPLICATION_MODE_PATH).lower()

        if current_mode != layout_mode:
            settings.set_string(SETTINGS_APPLICATION_MODE_PATH, layout_mode)

        omni.kit.window.file.new()

        if self._window:
            self._window.hide()
