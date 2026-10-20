"""A modal window interface for displaying and applying deeplink data to the current stage."""

import asyncio

import carb
import omni.ui as ui

from ..link_applier import LinkApplier
from ..ui.notification import post_notification
from .styles import get_style


class DeeplinkApplyWindow(ui.Window):
    """A modal window for displaying and applying deeplink data.

    This window presents deeplink information to users in a readable format
    and provides options to apply or cancel the deeplink operation. The window
    is non-resizable and modal, ensuring users must make a decision before
    proceeding with other operations.

    Args:
        link_data (dict): The deeplink data to display and potentially apply.
    """

    WINDOW_NAME = "Apply Deeplink"
    """str: The display name for the deeplink apply window."""

    def __init__(self, link_data: dict):
        """Initializes the deeplink application window with link data and sets up the UI."""
        self._link_data = link_data
        super().__init__(
            self.WINDOW_NAME,
            width=600,
            height=400,
            flags=ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_CLOSE
            | ui.WINDOW_FLAGS_MODAL,
        )
        self.set_visibility_changed_fn(self._visibility_changed_fn)
        self.frame.set_build_fn(self._build_ui)
        ui.Workspace.set_show_window_fn(self.WINDOW_NAME, lambda v, ld=self._link_data: self._show_apply_window(v, ld))
        ui.Workspace.show_window(self.WINDOW_NAME, True)

    def _visibility_changed_fn(self, visible):
        """Handles window visibility changes by destroying the window when it becomes invisible.

        Args:
            visible (bool): Whether the window is currently visible.
        """
        if not visible:
            self.destroy()

    def destroy(self):
        """Destroys the window and cleans up associated resources."""
        self.visible = False
        self.set_visibility_changed_fn(None)
        ui.Workspace.set_show_window_fn(self.WINDOW_NAME, None)
        super().destroy()

    def _build_ui(self):
        """Builds the UI components for displaying deeplink data and action buttons."""
        with self.frame:
            with ui.VStack(style=get_style()):
                with ui.ScrollingFrame(
                    width=ui.Percent(100),
                    height=320,
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                ):
                    with ui.VStack(height=0):
                        ui.Spacer(height=10)
                        for key, value in self._link_data.items():
                            if isinstance(value, dict):
                                ui.Label(key.title(), height=20)
                                for sub_key, sub_value in value.items():
                                    ui.Label("    " + sub_key.title() + ": " + str(sub_value), height=20)
                                ui.Spacer(height=10)
                                continue
                            ui.Label(key.title() + ": " + str(value), height=20)

                ui.Spacer(height=10)
                with ui.HStack(alignment=ui.Alignment.CENTER):
                    ui.Button("OK", clicked_fn=lambda: asyncio.ensure_future(self._on_ok_clicked_func()), height=40)
                    ui.Button(
                        "Cancel",
                        clicked_fn=lambda: asyncio.ensure_future(self._on_cancel_clicked_func()),
                        height=40,
                    )

    async def _on_ok_clicked_func(self):
        """Handles the OK button click to apply the deeplink and close the window."""
        self._on_apply_window_clicked(self._link_data)
        self.destroy()

    async def _on_cancel_clicked_func(self):
        """Handles the Cancel button click to close the window without applying changes."""
        self._on_apply_window_cancelled()
        self.destroy()

    def _show_apply_window(self, value, link_data):
        """Controls window visibility based on the provided value.

        Args:
            value (bool): Whether to show or hide the window.
            link_data (dict): The deeplink data associated with the window.
        """
        if value:
            self.visible = True
        else:
            self.destroy()

    def _on_apply_window_clicked(self, link_data):
        """Processes the deeplink application when the user confirms the action.

        Args:
            link_data (dict): The deeplink data to be applied.
        """
        self.destroy()

        try:
            link_applier = LinkApplier()
            asyncio.ensure_future(link_applier.apply_deep_link(link_data))
        except ValueError as e:
            post_notification(f"Error applying deep link: {e}", info=False, duration=3)
            return None

    def _on_apply_window_cancelled(self):
        """Handles window cancellation by destroying the window."""
        self.destroy()
