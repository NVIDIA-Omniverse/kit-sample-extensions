import carb
import omni.ui as ui


class FileShareWindow(ui.Window):
    def __init__(self, copy_button_text="Copy Path to Clipboard", copy_button_fn=None, modal=True):
        self._title = "Share Omniverse USD Path"
        self._copy_button_text = copy_button_text
        self._copy_button_fn = copy_button_fn
        self._status_text = "Copy and paste this path to another user to share the location of this USD file."
        self._stage_url = ""
        self._stage_string_box = None

        super().__init__(self._title, visible=False, width=600, height=140, dockPreference=ui.DockPreference.DISABLED)
        self.flags = (
            ui.WINDOW_FLAGS_NO_COLLAPSE
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_MOVE
        )
        if modal:
            self.flags = self.flags | ui.WINDOW_FLAGS_MODAL

        self.frame.set_build_fn(self._build_ui)

    def _build_ui(self):
        with self.frame:
            with ui.VStack():
                ui.Spacer(height=10)
                with ui.HStack(height=0):
                    ui.Spacer()
                    self._status_label = ui.Label(self._status_text, width=0)
                    ui.Spacer()
                ui.Spacer(height=10)
                with ui.HStack(height=0):
                    ui.Spacer()
                    self._stage_string_box = ui.StringField(width=550)
                    self._stage_string_box.model.set_value(self._stage_url)
                    ui.Spacer()
                ui.Spacer(height=5)
                with ui.HStack(height=0):
                    ui.Spacer()
                    copy_button = ui.Button(self._copy_button_text, width=165, name="share_button")
                    copy_button.set_clicked_fn(self._on_copy_button_fn)
                    ui.Spacer()
                ui.Spacer(height=10)

    def _on_copy_button_fn(self):
        self.visible = False
        if self._stage_string_box:
            try:
                import omni.kit.clipboard  # type: ignore

                try:
                    omni.kit.clipboard.copy(self._stage_string_box.model.as_string)
                except:  # pragma: no cover
                    carb.log_warn("clipboard copy failed")
            except ImportError:  # pragma: no cover
                carb.log_warn("Could not import omni.kit.clipboard. Cannot copy scene URL to the clipboard.")

    @property
    def url(self):
        return self._stage_url

    @url.setter
    def url(self, value: str) -> None:
        self._stage_url = value
        if self._stage_string_box:
            self._stage_string_box.model.set_value(value)
