import carb
import omni.ui as ui

from .controls import MENUBAR_HEIGHT, SETTINGS_APPLICATION_MODE_PATH
from .file_buttons import BUTTON_SIZE, SETTINGS_ROOT, ImportButton, NewButton, OpenButton, SaveButton, ShareButton

# these settings are set by application mode, but they may be controlled individually too
SETTINGS_OPEN_VISIBLE = SETTINGS_ROOT + "open_visible"
SETTINGS_NEW_VISIBLE = SETTINGS_ROOT + "new_visible"
SETTINGS_SAVE_VISIBLE = SETTINGS_ROOT + "save_visible"
SETTINGS_IMPORT_VISIBLE = SETTINGS_ROOT + "import_visible"
SETTINGS_SHARE_VISIBLE = SETTINGS_ROOT + "share_visible"

BUTTONS_WIDTH = BUTTON_SIZE * 5 + 60


class FileMenu:
    def __init__(self) -> None:
        self._settings = carb.settings.acquire_settings_interface()
        self._settings.subscribe_to_node_change_events(
            SETTINGS_APPLICATION_MODE_PATH, self._on_application_mode_changed
        )
        self._on_application_mode_changed()
        self._settings.subscribe_to_node_change_events(SETTINGS_OPEN_VISIBLE, self._rebuild)
        self._settings.subscribe_to_node_change_events(SETTINGS_SAVE_VISIBLE, self._rebuild)
        self._settings.subscribe_to_node_change_events(SETTINGS_IMPORT_VISIBLE, self._rebuild)
        self._settings.subscribe_to_node_change_events(SETTINGS_SHARE_VISIBLE, self._rebuild)
        self._buttons = []

        with ui.VStack(width=BUTTONS_WIDTH, height=MENUBAR_HEIGHT):
            self._button_frame = ui.Frame(build_fn=self._build_buttons)
            with self._button_frame:
                self._build_buttons()

    # singleton model, to ensure set once , use in everywhere
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def _build_buttons(self):
        for button in self._buttons:
            button.destroy()
        self._buttons = []
        ui.Spacer(width=5)
        with ui.VStack(width=BUTTONS_WIDTH, height=MENUBAR_HEIGHT):
            with ui.HStack(spacing=0, width=BUTTONS_WIDTH, height=MENUBAR_HEIGHT):
                if self._settings.get(SETTINGS_OPEN_VISIBLE):
                    self._buttons.append(OpenButton())
                if self._settings.get(SETTINGS_NEW_VISIBLE):
                    self._buttons.append(NewButton())
                if self._settings.get(SETTINGS_SAVE_VISIBLE):
                    self._buttons.append(SaveButton())
                if self._settings.get(SETTINGS_IMPORT_VISIBLE):
                    self._buttons.append(ImportButton())
                if self._settings.get(SETTINGS_SHARE_VISIBLE):
                    self._buttons.append(ShareButton())

    def _on_application_mode_changed(self, *args) -> None:
        mode = self._settings.get_as_string(SETTINGS_APPLICATION_MODE_PATH)
        if mode == "present":
            self._settings.set(SETTINGS_OPEN_VISIBLE, True)
            self._settings.set(SETTINGS_NEW_VISIBLE, False)
            self._settings.set(SETTINGS_SAVE_VISIBLE, False)
            self._settings.set(SETTINGS_IMPORT_VISIBLE, False)
            self._settings.set(SETTINGS_SHARE_VISIBLE, True)
        elif mode == "review":
            self._settings.set(SETTINGS_OPEN_VISIBLE, True)
            self._settings.set(SETTINGS_NEW_VISIBLE, False)
            self._settings.set(SETTINGS_SAVE_VISIBLE, True)
            self._settings.set(SETTINGS_IMPORT_VISIBLE, False)
            self._settings.set(SETTINGS_SHARE_VISIBLE, True)
        else:
            self._settings.set(SETTINGS_OPEN_VISIBLE, False)
            self._settings.set(SETTINGS_NEW_VISIBLE, False)
            self._settings.set(SETTINGS_SAVE_VISIBLE, False)
            self._settings.set(SETTINGS_IMPORT_VISIBLE, False)
            self._settings.set(SETTINGS_SHARE_VISIBLE, False)

    def _rebuild(self, *args) -> None:
        self._button_frame.rebuild()
