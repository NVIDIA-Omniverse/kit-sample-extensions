"""Welcome window implementation for the USD Explorer.

This module provides the main welcome window UI implementation for the USD
Explorer application. It includes both a modal and non-modal window variant
with customizable content and styling.
"""

import asyncio
from typing import Any, Optional

import carb
import carb.settings
import omni.appwindow
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni import ui
from omni.kit.widgets.custom import SimpleImageButton

from .styles import WELCOME_WINDOW_STYLE
from .widgets.action_button_container import ActionButtonContainer
from .widgets.open_link_container import OpenLinkContainer
from .widgets.utils import get_icon_path

# UI Content sizes
TITLEBAR_HEIGHT = 32
TITLEBAR_CLOSE_SIZE = 26
CONTENT_MARGIN = 32
WINDOW_WIDTH = 840
WINDOW_HEIGHT = 380
VISIBLE_PATH = "/exts/omni.kit.usd_explorer.window.welcome/visible"

# omni.ui does not have this flag exposed, but it exists in
# Dear Imgui which omni.ui is built upon. Sooo ....
WINDOW_NO_BRING_TO_FRONT_ON_FOCUS = 8192


class WelcomeWindowFakeModal(ui.Window):
    """A modal window wrapper for the welcome window.

    This class provides a modal-like behavior for the welcome window by
    creating a full-screen overlay with the actual welcome window centered
    on top.

    Attributes:
        _window: The actual welcome window instance
        visible: Whether the window is currently visible
    """

    def __init__(self, title: str) -> None:
        """Initialize the modal window wrapper.

        Args:
            connection: The connection object for the window
            title: The title to display in the window
        """
        app_width = ui.Workspace.get_main_window_width()
        app_height = ui.Workspace.get_main_window_height()

        super().__init__(
            f"{title} Fake Modal",
            padding_x=0,
            padding_y=0,
            width=app_width,
            height=app_height,
            flags=ui.WINDOW_FLAGS_NO_TITLE_BAR
            | ui.WINDOW_FLAGS_NO_MOVE
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_CLOSE,
        )

        self.visible = False
        self.frame.style = {"background_color": 0x80000000}

        self._window = WelcomeWindow(title)
        self._window.set_visibility_changed_fn(self._visibility_changed_fn)
        self.set_key_pressed_fn(self._window._on_key_pressed)

        asyncio.ensure_future(self._post_constructor())

    def destroy(self) -> None:
        """Clean up resources and destroy the window."""
        self._window.destroy()
        super().destroy()

    def show(self) -> None:
        """Display the welcome window."""
        self._window.show()

    def hide(self) -> None:
        """Hide the welcome window."""
        self._window.hide()

    def _visibility_changed_fn(self, visible: bool) -> None:
        """Handle visibility changes of the inner window.

        Args:
            visible: Whether the window is now visible
        """
        self.visible = visible

    async def _post_constructor(self) -> None:
        """Post-construction setup to ensure proper window display."""
        await omni.kit.app.get_app().next_update_async()
        self.flags |= WINDOW_NO_BRING_TO_FRONT_ON_FOCUS


class WelcomeWindow(ui.Window):
    """The main welcome window implementation.

    This class implements the core welcome window UI with customizable
    content, styling, and behavior.

    Attributes:
        _close_button: The close button widget
        _settings: Application settings
        _always_closable: Whether the window can always be closed
        _closable: Whether the window can be closed in current state
        _action_button_container: Container for action buttons
        _open_link_container: Container for external links
    """

    def __init__(self, title: str) -> None:
        """Initialize the welcome window.

        Args:
            connection: The connection object for the window
            title: The title to display in the window
        """
        self._close_button: Optional[SimpleImageButton] = None
        self._settings = carb.settings.get_settings()
        # OM-83318: Factory Explorer wants the close button always visible.
        self._always_closable = (
            self._settings.get_as_bool("/exts/omni.kit.usd_explorer.window.welcome/alwaysClosable") or False
        )
        # OM-67658: should only build close button if it a file is loaded
        is_new_stage = omni.usd.get_context().is_new_stage()
        self._closable = not is_new_stage or self._always_closable

        self._action_button_container: Optional[ActionButtonContainer] = None
        self._open_link_container: Optional[OpenLinkContainer] = None
        self._build_startup_content_page(title)

        # start off invisible
        self.visible = False

        # OM-76493: subscribe to main app window resize
        self._app_window_resize_sub = get_eventdispatcher().observe_event(
            observer_name="omni.kit.usd_explorer.window.welcome:WelcomeWindow",
            event_name=omni.appwindow.GLOBAL_EVENT_WINDOW_RESIZE,
            on_event=self._on_app_window_resized,
        )

    def destroy(self) -> None:
        """Clean up resources and destroy the window."""
        self.visible = False
        self.set_key_pressed_fn(None)
        self._app_window_resize_sub = None

        if self._action_button_container:
            self._action_button_container.destroy()
            self._action_button_container = None
        if self._open_link_container is not None:
            self._open_link_container.destroy()
            self._open_link_container = None
        if self._close_button is not None:
            self._close_button.clicked_fn = None
            self._close_button.destroy()
            self._close_button = None

        super().destroy()

    def show(self) -> None:
        """Display the welcome window and update its content."""
        # OM-63261: Re-position welcome window to center;
        # After updating to kit 104 the welcome window will not be positioned
        # at the center of the screen on startup;
        self._center_window()
        self.visible = True
        self._settings.set(VISIBLE_PATH, True)

    def hide(self) -> None:
        """Hide the welcome window."""
        self.visible = False
        self._settings.set(VISIBLE_PATH, False)

    def _center_window(self) -> None:
        """Center the window on the screen."""
        app_width = ui.Workspace.get_main_window_width()
        app_height = ui.Workspace.get_main_window_height()
        pos_x = (app_width - self.width) / 2.0
        pos_y = (app_height - self.height) / 2.0
        self.setPosition(pos_x, pos_y)

    def _on_key_pressed(self, key: int, mod: int, pressed: bool) -> None:
        """Handle keyboard input events.

        Args:
            key: The key that was pressed
            mod: Any modifier keys that were held
            pressed: Whether the key was pressed or released
        """
        if not pressed:
            return
        if mod in (0, ui.Widget.FLAG_WANT_CAPTURE_KEYBOARD) and key == int(carb.input.KeyboardInput.ESCAPE):
            self.hide()

    def _on_app_window_resized(self, event: Any) -> None:
        """Handle application window resize events.

        Args:
            event: The resize event object
        """
        self._center_window()

    def _build_startup_content_page(self, title: str) -> None:
        """Build the initial content of the welcome window.

        Args:
            title: The title to display in the window
        """
        super().__init__(
            title,
            padding_x=0,
            padding_y=0,
            style=WELCOME_WINDOW_STYLE,
            # limit the window width and height
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            # NOTE: for OMFP-2112 this window is no longer modal so that
            # a File->Open popup may appear above the welcome window
            flags=ui.WINDOW_FLAGS_NO_TITLE_BAR | ui.WINDOW_FLAGS_NO_MOVE | ui.WINDOW_FLAGS_NO_RESIZE,
        )
        self.frame.set_build_fn(self._build_content)
        # OM-65870: set the modal window overlay shade to transparent
        self.frame.set_style(
            {
                "Window": {"secondary_background_color": 0x0},
            }
        )

    def _build_content(self) -> None:
        """Build the main content of the window."""
        with self.frame:
            with ui.VStack():
                self._build_title_bar()
                self._build_content_main_body()

    def _build_title_bar(self) -> None:
        """Build the title bar section of the window."""
        with ui.ZStack(height=TITLEBAR_HEIGHT, style=WELCOME_WINDOW_STYLE):
            ui.Rectangle(name="titlebar")
            with ui.HStack():
                ui.Spacer()
                # build image icon and window title
                with ui.HStack(width=0, spacing=5):
                    ui.Image(
                        get_icon_path("nvidia-omniverse-viewer-icon-32x32.png"),
                        width=TITLEBAR_HEIGHT,
                        height=TITLEBAR_HEIGHT,
                        style={"margin": 3},
                    )
                    ui.Label(
                        ("WELCOME TO OMNIVERSE"),
                        name="titlebar_dark",
                        width=0,
                        height=TITLEBAR_HEIGHT,
                        alignment=ui.Alignment.V_CENTER,
                    )
                ui.Spacer()
                # OM-67658: should only build close button if it a file
                # is loaded
                if self._closable:
                    # build close button
                    with ui.VStack(width=0, style={"margin": 1}):
                        self._close_button = SimpleImageButton(
                            get_icon_path("Close.svg"),
                            TITLEBAR_CLOSE_SIZE,
                            clicked_fn=self.hide,
                            style=WELCOME_WINDOW_STYLE,
                            padding=4,
                        )
                    # add ESC key event to close
                    self.set_key_pressed_fn(self._on_key_pressed)

    def _build_content_main_body(self) -> None:
        """Build the main content body of the window."""
        with ui.ZStack(style=WELCOME_WINDOW_STYLE):
            ui.Rectangle(name="content_body")
            with ui.VStack():
                # build action buttons
                ui.Spacer(height=ui.Percent(4))
                self._action_button_container = ActionButtonContainer(self)
                ui.Spacer(height=ui.Percent(10))
                # build link container
                self._open_link_container = OpenLinkContainer(self)
