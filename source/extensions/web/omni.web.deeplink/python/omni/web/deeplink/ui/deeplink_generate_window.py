"""This module provides a modal window interface for generating deeplinks to the current USD stage with customizable camera and time options."""

import asyncio

import carb
import omni.ui as ui
import omni.usd

from ..link_generator import LinkGenerator
from ..ui.notification import post_notification
from .styles import get_style


class DeeplinkGenerateWindow(ui.Window):
    """A modal window interface for generating deeplinks to the current USD stage.

    This window provides a user interface for creating deeplinks that can be used to share and access specific states of a USD stage. The window presents options to include camera properties and time information in the generated deeplink, allowing users to customize what aspects of the current scene state are captured in the link.

    The window includes:
    - Checkbox option to include camera properties in the deeplink
    - Checkbox option to include time information in the deeplink
    - OK button to generate the deeplink with selected options
    - Cancel button to close the window without generating a link

    When the OK button is clicked, the window generates a deeplink based on the current USD stage and selected options. If the auto-copy setting is enabled, the generated link is automatically copied to the clipboard and a notification is displayed. The window requires a saved USD stage to generate deeplinks and will display an error if attempting to create a link from an unsaved or anonymous stage.

    The window automatically destroys itself when closed or after successful deeplink generation, and integrates with the Omni UI workspace system for proper window management.
    """

    WINDOW_NAME = "Generate Deeplink"
    """str: The display name for the deeplink generation window."""

    def __init__(self):
        """Initializes the deeplink generation window with checkboxes for camera and time inclusion options."""
        self._camera_checkbox = None
        self._time_checkbox = None
        super().__init__(
            self.WINDOW_NAME,
            width=400,
            height=180,
            flags=ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_CLOSE
            | ui.WINDOW_FLAGS_MODAL,
        )
        self.set_visibility_changed_fn(self._visibility_changed_fn)
        self.frame.set_build_fn(self._build_ui)
        ui.Workspace.set_show_window_fn(self.WINDOW_NAME, lambda v: self._show_generate_window(v))
        ui.Workspace.show_window(self.WINDOW_NAME, True)

    def _visibility_changed_fn(self, visible):
        """Handles window visibility changes by destroying the window when hidden.

        Args:
            visible (bool): Whether the window is visible or hidden.
        """
        if not visible:
            self.destroy()

    def destroy(self):
        """Destroys the window and cleans up UI components and workspace references."""
        self.visible = False
        self.set_visibility_changed_fn(None)

        if self._camera_checkbox:
            self._camera_checkbox.destroy()
        if self._time_checkbox:
            self._time_checkbox.destroy()

        self._camera_checkbox = None
        self._time_checkbox = None
        ui.Workspace.set_show_window_fn(self.WINDOW_NAME, None)
        super().destroy()

    def _build_ui(self):
        """Builds the user interface with checkboxes for camera and time options and OK/Cancel buttons."""
        with self.frame:
            with ui.VStack(style=get_style()):
                ui.Spacer(height=10)
                with ui.HStack(height=20):
                    url = carb.settings.get_settings().get_as_string("/exts/omni.web.deeplink/portal_base_url")
                    if "?" in url:
                        url = url.split("?", 1)[0]

                    ui.Spacer(width=10)
                    ui.Label(f"Portal URL: {url}", height=20)

                with ui.HStack(height=20):
                    app_id = carb.settings.get_settings().get_as_string("/exts/omni.web.deeplink/application_id")
                    ui.Spacer(width=10)
                    ui.Label(f"Application ID: {app_id}", height=20)

                ui.Spacer(height=10)
                with ui.HStack(height=20):
                    ui.Spacer(width=10)
                    self._camera_checkbox = ui.CheckBox(width=20)
                    ui.Label("Include Camera Properties", height=20)

                with ui.HStack(height=20):
                    ui.Spacer(width=10)
                    self._time_checkbox = ui.CheckBox(width=20)
                    ui.Label("Include Time")

                ui.Spacer(height=10)
                with ui.HStack(alignment=ui.Alignment.CENTER):
                    ui.Button("OK", clicked_fn=lambda: asyncio.ensure_future(self._on_ok_clicked_func()), height=40)
                    ui.Button(
                        "Cancel",
                        clicked_fn=lambda: asyncio.ensure_future(self._on_cancel_clicked_func()),
                        height=40,
                    )

        if carb.settings.get_settings().get_as_bool("/exts/omni.web.deeplink/default_include_camera"):
            self._camera_checkbox.model.as_bool = True

        if carb.settings.get_settings().get_as_bool("/exts/omni.web.deeplink/default_include_time"):
            self._time_checkbox.model.as_bool = True

    async def _on_ok_clicked_func(self):
        """Handles OK button click by generating a deeplink with selected options and optionally copying to clipboard."""
        copy_to_clipboard = carb.settings.get_settings().get_as_bool("/exts/omni.web.deeplink/clipboard_auto_copy")
        include_camera = self._camera_checkbox.model.as_bool
        include_time = self._time_checkbox.model.as_bool

        usd_context = omni.usd.get_context()
        stage = usd_context.get_stage()
        if not stage or stage.GetRootLayer().anonymous:
            carb.log_error("No scene has been saved, cannot create a deep link.")
            self.destroy()
            return

        # generate deeplink
        link_generator = LinkGenerator(usd_context, stage)
        link = link_generator.generate_link(include_camera, include_time)
        if copy_to_clipboard:
            omni.kit.clipboard.copy(link)
            post_notification("Copied link to clipboard", info=True)
        link_generator.destroy()
        self.destroy()

    async def _on_cancel_clicked_func(self):
        """Handles Cancel button click by closing the deeplink generation window."""
        self.destroy()

    def _show_generate_window(self, value):
        """Shows or hides the deeplink generation window based on the provided value.

        Args:
            value (bool): Whether to show or hide the window.
        """
        if value:
            self.visible = True
        else:
            self.destroy()
