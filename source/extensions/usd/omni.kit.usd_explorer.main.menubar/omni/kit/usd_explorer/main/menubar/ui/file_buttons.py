import weakref
from typing import Optional

import carb
import omni.kit.actions
import omni.kit.app
import omni.kit.usd.layers as layers
import omni.ui as ui
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.widgets.custom import COLORS, DarkColors

from .controls import MENUBAR_HEIGHT
from .file_share_window import FileShareWindow

SETTINGS_ROOT = "/exts/omni.kit.usd_explorer.main.menubar/"
MODULE_PATH = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)

BUTTON_SIZE = MENUBAR_HEIGHT - 4


class FileButton:
    def __init__(self, icon_file_name, tooltip_text) -> None:
        self._tooltip_text = tooltip_text
        style = {
            "image_url": f"{MODULE_PATH}/icons/{icon_file_name}",
            "Button": {"background_color": COLORS.TRANSPARENT, "margin": 2, "padding": 2},
            "Button.Image": {"color": 0xFFA8A8A8},
        }
        self._button = ui.Button(
            clicked_fn=self._on_click,
            tooltip=tooltip_text,
            style=style,
            height=BUTTON_SIZE,
            width=BUTTON_SIZE,
            image_width=BUTTON_SIZE,
            image_height=BUTTON_SIZE,
        )

    def _on_click(self, *args) -> None:
        pass

    def destroy(self) -> None:
        self._button.destroy()


class OpenButton(FileButton):
    def __init__(self) -> None:
        super().__init__("browse_dark.svg", "Open a new stage.")

    def _on_click(self, *args) -> None:
        omni.kit.actions.core.execute_action("omni.kit.window.file", "open")


class NewButton:  # pragma: no cover -- unused
    def __init__(self) -> None:
        tooltip_text = "Creates a new stage"
        style = {
            "image_url": f"{MODULE_PATH}/icons/newfile_color.svg",
            "Button": {"background_color": COLORS.TRANSPARENT},
        }
        self._button = ui.Button(
            clicked_fn=self._on_click,
            tooltip=tooltip_text,
            style=style,
            height=BUTTON_SIZE,
            width=BUTTON_SIZE,
            image_width=BUTTON_SIZE,
            image_height=BUTTON_SIZE,
        )

    def _on_click(self, *args) -> None:
        omni.kit.actions.core.execute_action("omni.kit.window.file", "new")


class SaveButton(FileButton):  # pragma: no cover -- unused
    def __init__(self) -> None:
        super().__init__("save_dark.svg", "Save")

    def _on_click(self, *args) -> None:
        omni.kit.actions.core.execute_action("omni.kit.window.file", "save")


class ImportButton(FileButton):  # pragma: no cover -- unused
    def __init__(self) -> None:
        super().__init__("import_dark.svg", "Import an asset")

    def _on_click(self, *args) -> None:
        omni.kit.actions.core.execute_action("omni.kit.tool.asset_importer", "import")


class WeakMethod(weakref.WeakMethod):
    def __call__(self, *args, **kwargs):
        obj = weakref.ref.__call__(self)
        func = self._func_ref()
        if obj is None or func is None:
            return None
        return func(obj, *args, **kwargs)


class ShareButton(FileButton):
    def __init__(self) -> None:
        self._window: Optional[FileShareWindow] = None
        super().__init__("share.svg", "Get URL to share stage with others.")
        self._context = omni.usd.get_context()
        self._set_enabled()

        self._stage_event_sub = get_eventdispatcher().observe_event(
            observer_name="omni.kit.usd_explorer.main.menubar:ShareButton",
            event_name=self._context.stage_event_name(omni.usd.StageEventType.OPENED),
            on_event=WeakMethod(self._on_stage_event),
        )
        self._layers_interface = layers.get_layers(self._context)

    def _is_stage_shareable(self) -> bool:
        return self._context.get_stage_url().startswith("omniverse://")

    def _on_click(self, *args) -> None:
        if self._window is None:
            self._window = FileShareWindow()

        live_syncing = self._layers_interface.get_live_syncing()
        current_session = live_syncing.get_current_live_session()
        if not current_session:
            self._window.url = self._context.get_stage_url()
        else:
            self._window.url = current_session.shared_link
        self._window.visible = True

    def _set_enabled(self) -> None:
        enabled = self._is_stage_shareable()
        self._button.enabled = enabled
        self._button.tooltip = (
            "Get URL to share stage with others."
            if enabled
            else 'Get URL to share stage with others.\nSharing is possible only for USD stages located in "omniverse://"'
        )

    def _on_stage_event(self, event):
        self._set_enabled()

    def destroy(self) -> None:
        super().destroy()
        self._stage_event_sub = None

    def __del__(self) -> None:
        self.destroy()
