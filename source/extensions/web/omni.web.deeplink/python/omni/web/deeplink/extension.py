"""Extension module for creating and applying deep links to share USD scene states."""

__all__ = []

import asyncio

import carb
import omni.ext
import omni.kit.clipboard
import omni.kit.menu.utils
import omni.kit.widget.context_menu
import omni.ui as ui
import omni.usd
from omni.kit.menu.utils import MenuItemDescription

from .actions import deregister_actions, register_actions
from .encoder import Base64URLEncoder
from .link_applier import LinkApplier
from .link_generator import LinkGenerator
from .ui.deeplink_apply_window import DeeplinkApplyWindow
from .ui.deeplink_generate_window import DeeplinkGenerateWindow
from .ui.notification import post_notification


class DeepLinkExtension(omni.ext.IExt):
    """Main extension class for Deeplink functionality."""

    _MENU_GROUP = "File"

    def __init__(self):
        """Initializes the DeepLinkExtension with default values for menu lists and UI windows."""
        super().__init__()
        self._deeplink_window_menu_list = []
        self._deeplink_context_menu_list = []
        self._ext_id = ""
        self._generate_window = None
        self._apply_window = None
        self.__apply_link_task = None
        self._dispatcher = None
        self._subscription = None

    def _is_cloud_deployment(self):
        """Check if running in OVC deployment environment.

        Returns:
            bool: True if running in OVC deployment environment, False otherwise.
        """
        return carb.settings.get_settings().get_as_bool("/app/ovc_deployment")

    def on_startup(self, ext_id):
        """Initialize extension on startup
        - Set up event listeners
        - Initialize services

        Args:
            ext_id (str): Extension identifier for action registration.
        """
        self._ext_id = ext_id
        self._setup_deep_link_receiver()
        register_actions(self, "omni.web.deeplink")
        if carb.settings.get_settings().get_as_bool("/exts/omni.web.deeplink/add_context_menus"):
            self._register_context_menu_items()
        if carb.settings.get_settings().get_as_bool("/exts/omni.web.deeplink/add_file_menus"):
            self._register_window_menu_items("omni.web.deeplink")

    def on_shutdown(self):
        """Clean up on shutdown
        - Clean up listeners
        - Clean up services
        """
        if self._generate_window:
            self._generate_window.destroy()
            self._generate_window = None
        if self._apply_window:
            self._apply_window.destroy()
            self._apply_window = None
        if self.__apply_link_task:
            self.__apply_link_task.cancel()
            self.__apply_link_task = None

        self._destroy_deep_link_receiver()
        deregister_actions("omni.web.deeplink")
        self._deregister_context_menu_items()
        self._deregister_window_menu_items()

    def _register_context_menu_items(self):
        """Register right-click context menu items"""
        # setup context menus
        menus = [
            {"header": "", "name": "", "glyph": "", "onclick_fn": None},
            {
                "name": "Create Deeplink",
                "glyph": "menu_flow.svg",
                "onclick_fn": lambda o: self._generate_link_clicked(),
            },
        ]

        if not self._is_cloud_deployment():
            menus.append(
                {
                    "name": "Apply Deeplink",
                    "glyph": "menu_flow.svg",
                    "onclick_fn": lambda o: self._apply_link_clicked(),
                }
            )

        for menu in menus:
            self._deeplink_context_menu_list.append(omni.kit.widget.context_menu.add_menu(menu, "MENU"))

    def _register_window_menu_items(self, ext_id):
        """Register window menu items"""
        self._deeplink_window_menu_list = [
            MenuItemDescription(
                name="Create Deeplink",
                onclick_action=(ext_id, "generate_link_clicked"),
                appear_after="Add Payload",
                glyph="menu_flow.svg",
                header="",
            )
        ]
        if not self._is_cloud_deployment():
            self._deeplink_window_menu_list.append(
                MenuItemDescription(
                    name="Apply Deeplink",
                    onclick_action=(ext_id, "apply_link_clicked"),
                    appear_after="Create Deeplink",
                    glyph="menu_flow.svg",
                )
            )

        omni.kit.menu.utils.add_menu_items(self._deeplink_window_menu_list, self._MENU_GROUP)

    def _deregister_context_menu_items(self):
        """Deregister right-click context menu items"""
        omni.kit.widget.context_menu.close_menu()  # this should be fixed in master
        self._deeplink_context_menu_list = []

    def _deregister_window_menu_items(self):
        """Deregister window menu items"""
        omni.kit.menu.utils.remove_menu_items(self._deeplink_window_menu_list, self._MENU_GROUP)
        self._deeplink_window_menu_list = []

    def _setup_deep_link_receiver(self):
        """Set up listener for incoming Deeplink data from portal.

        ``apply_deeplink_request`` is an incoming event sent by the web portal
        through ``omni.kit.livestream.messaging``. Inbound livestream events are
        re-dispatched by that extension via ``carb.eventdispatcher`` under their
        original event name, so we only need to observe the event name directly
        — no ``register_event_type_to_send`` call is required (that helper is
        for outgoing events only).
        """
        self._dispatcher = carb.eventdispatcher.get_eventdispatcher()
        self._subscription = self._dispatcher.observe_event(
            observer_name="omni.web.deeplink",
            event_name="apply_deeplink_request",
            on_event=self._handle_apply_deeplink_request,
        )

    def _destroy_deep_link_receiver(self):
        """Destroy listener for incoming Deeplink data from portal"""
        if self._subscription is not None:
            self._subscription.reset()
            self._subscription = None

    def _handle_apply_deeplink_request(self, event: carb.eventdispatcher.Event):
        """Processes incoming deeplink application requests from the event dispatcher.

        Extracts deeplink data from the event payload, validates it, and applies the deeplink
        to the current scene using LinkApplier.

        Args:
            event (carb.eventdispatcher.Event): Event containing deeplink payload data.
        """
        # NOTE: payload data has already had padding removed and is just encoded data
        if event.payload:
            link_data = event.payload["data"]
            if not Base64URLEncoder.can_decode_link(link_data, remove_padding=False, use_crc=True):
                post_notification(f"URL is not a valid deep link.", info=False, duration=3)
                return

            try:
                decoded = Base64URLEncoder.decode(link_data, remove_padding=False, use_crc=True)
                link_applier = LinkApplier()
                self.__apply_link_task = asyncio.ensure_future(link_applier.apply_deep_link(decoded))
            except ValueError as e:
                post_notification(f"Error applying deep link: {e}", info=False, duration=3)
            return

        carb.log_error("No deeplink data found")

    def _generate_link_clicked(self):
        """Handles the generate deeplink menu action.

        Creates a deeplink for the current scene with camera and time settings based on
        configuration. Opens the generation window or directly generates and copies the link
        to clipboard depending on settings.
        """
        if self._generate_window:
            self._generate_window.destroy()
            del self._generate_window
            self._generate_window = None

        usd_context = omni.usd.get_context()
        stage = usd_context.get_stage()
        if not stage or stage.GetRootLayer().anonymous:
            post_notification(f"No scene has been saved, cannot create a deep link.", info=False, duration=3)
            return

        show_generate_window = carb.settings.get_settings().get_as_bool("/exts/omni.web.deeplink/show_generate_window")
        if show_generate_window:
            self._generate_window = DeeplinkGenerateWindow()
            return

        include_camera = carb.settings.get_settings().get_as_bool("/exts/omni.web.deeplink/default_include_camera")
        include_time = carb.settings.get_settings().get_as_bool("/exts/omni.web.deeplink/default_include_time")
        copy_to_clipboard = carb.settings.get_settings().get_as_bool("/exts/omni.web.deeplink/clipboard_auto_copy")

        # generate deeplink
        link_generator = LinkGenerator(usd_context, stage)
        link = link_generator.generate_link(include_camera, include_time)
        if copy_to_clipboard:
            omni.kit.clipboard.copy(link)
            post_notification("Copied link to clipboard", info=True)
        link_generator.destroy()
        return

    def _apply_link_clicked(self):
        """Handles the apply deeplink menu action.

        Retrieves deeplink data from clipboard, validates it, and applies the deeplink to the
        current scene. Opens the apply window or directly applies the link depending on settings.
        """
        if self._apply_window:
            self._apply_window.destroy()
            del self._apply_window
            self._apply_window = None

        clipboard_content = omni.kit.clipboard.paste()
        clipboard_content = clipboard_content.rstrip("\r\n")
        if clipboard_content:
            if not Base64URLEncoder.can_decode_link(clipboard_content):
                post_notification(f"The clipboard content is not a valid deep link.", info=False, duration=3)
                return

            try:
                link_data = Base64URLEncoder.decode(clipboard_content)
            except ValueError as e:
                post_notification(f"Error applying deep link: {e}", info=False, duration=3)
                return

            if carb.settings.get_settings().get_as_bool("/exts/omni.web.deeplink/show_apply_window"):
                self._apply_window = DeeplinkApplyWindow(link_data)
                return

            link_applier = LinkApplier()
            self.__apply_link_task = asyncio.ensure_future(link_applier.apply_deep_link(link_data))
            return

        carb.log_error("No clipboard content found")
