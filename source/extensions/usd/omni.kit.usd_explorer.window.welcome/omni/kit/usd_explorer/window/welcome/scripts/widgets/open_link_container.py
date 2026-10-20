# NOTE: this code borrows heavily from omni.kit.widget.live_session_management's JoinWithSessionLinkWindow.

import asyncio

import carb
import omni.kit.actions.core
import omni.kit.notification_manager as nm
import omni.ui as ui
import omni.usd
from omni.kit.window.file import register_open_stage_addon
from pxr import Usd

from .utils import get_icon_path

CONTENT_MARGIN = 32


class OpenLinkContainer:

    def __init__(self, window) -> None:
        self._window = window

        self._link_input_field = None
        self._link_input_hint = None
        self._link_begin_edit_cb = None
        self._link_end_edit_cb = None
        self._link_edit_cb = None

        self._open_link_button = None

        self._build_ui()

        self._open_stage_subscription = register_open_stage_addon(self._on_open_stage)

    def destroy(self):
        self._window = None
        self._open_stage_subscription = None

        self._link_input_field = None
        self._link_input_hint = None
        self._link_begin_edit_cb = None
        self._link_end_edit_cb = None
        self._link_edit_cb = None

        if self._open_link_button:
            self._open_link_button.set_clicked_fn(None)
            self._open_link_button = None

    def _build_ui(self):

        button_style = {"margin": 0, "padding": 0}
        image_style = {"color": 0xFFFFC734}

        with ui.HStack(alignment=ui.Alignment.CENTER, height=0):
            ui.Spacer(width=CONTENT_MARGIN)
            with ui.ZStack():
                self._link_input_field = ui.StringField(name="new_session_link_field")
                self._link_input_hint = ui.Label(
                    "   Paste URL Link Here to Open File",
                    alignment=ui.Alignment.LEFT_CENTER,
                    style={"color": 0xFF3F3F3F},
                )

            ui.Spacer(width=20)
            # XXX hacking a button with an image + a label on top... but there must be a better way to do this
            # with just a button...
            with ui.ZStack(width=0):
                self._open_link_button = ui.Button(" ", style=button_style, name="open_link_button")
                with ui.HStack():
                    ui.Spacer(width=5)
                    ui.Image(get_icon_path("link_on.svg"), style=image_style, width=30)
                    ui.Spacer(width=5)
                    ui.Label("OPEN LINK", width=0)
                    ui.Spacer(width=5)
            # self._open_link_button = ui.Button("OPEN LINK", style = button_style, name="open_link_button", width=120, height=0)
            ui.Spacer(width=CONTENT_MARGIN)

        self._link_begin_edit_cb = self._link_input_field.model.subscribe_begin_edit_fn(self._on_link_begin_edit)
        self._link_end_edit_cb = self._link_input_field.model.subscribe_end_edit_fn(self._on_link_end_edit)
        self._link_edit_cb = self._link_input_field.model.subscribe_value_changed_fn(self._on_link_edit)
        self._open_link_button.set_clicked_fn(self._on_open_link)

    def _get_link_text(self):

        if self._link_input_field:
            link_text = self._link_input_field.model.get_value_as_string().strip()
        else:
            link_text = ""

        return link_text

    def _validate_link(self, link: str):
        return link and Usd.Stage.IsSupportedFile(link)

    def _on_link_begin_edit(self, model):
        self._update_link_status()

    def _on_link_end_edit(self, model):
        self._update_link_status()

    def _on_link_edit(self, model):
        self._update_link_status()

    def _update_link_status(self):
        if not self._link_input_field:
            return False

        link_text = self._get_link_text()
        link_text = link_text.strip()

        self._link_input_hint.visible = not link_text

        #        if not self._validate_link(link_text):
        #            return False

        return True

    def _on_open_stage(self):
        # If we opened a file, close the welcome window.
        if self._window:
            self._window.hide()

    def _on_open_link(self):
        if not self._update_link_status():
            return

        link_text = self._get_link_text()

        if not self._validate_link(link_text):
            self._target_notification = nm.post_notification(
                "Invalid file path.", hide_after_timeout=True, duration=3, status=nm.NotificationStatus.WARNING
            )
            return

        async def open_stage(path, window):
            # Adapted from omni.usd's open_stage_async
            is_stage_with_session = False
            try:
                import omni.kit.usd.layers as layers

                live_session_name = layers.get_live_session_name_from_shared_link(path)
                is_stage_with_session = live_session_name is not None
            except:
                pass

            if is_stage_with_session:
                # Try to open the stage with specified live session.
                success, error = await layers.get_live_syncing().open_stage_with_live_session_async(path)

                if success:
                    window.hide()
                else:
                    carb.log_error(f"Failed to open stage {path}: {error}.")
            else:
                # From OMFP-2198 we want the Progress window to appear while opening a file.
                # Opening the stage through the omni.kit.window.file action instead of through
                # omni.usd directly will get us that window.
                omni.kit.actions.core.execute_action("omni.kit.window.file", "open_stage", path)

        asyncio.ensure_future(open_stage(link_text, self._window))
