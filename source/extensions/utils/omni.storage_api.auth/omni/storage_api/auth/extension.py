"""
USD Storage API Authentication Extension

This extension handles communication between the web portal and Client Library
regarding USD Storage API authentication using omni.kit.livestream.messaging.
"""

__all__ = ["StorageAuthExtension", "get_instance"]

import asyncio
from typing import Optional, Tuple

import carb
import carb.events
import carb.settings
import omni.ext
import omni.kit.app
from carb.eventdispatcher import get_eventdispatcher

from .auth_handler import StorageAuthHandler

_extension_instance: Optional["StorageAuthExtension"] = None

# Event dispatched by omni.kit.livestream.core when a streaming client connects.
CLIENT_CONNECTED_EVENT = "omni.kit.livestream.client_connected:immediate"


def get_instance() -> Optional["StorageAuthExtension"]:
    """Return the StorageAuthExtension instance if enabled, else None."""
    return _extension_instance


class StorageAuthExtension(omni.ext.IExt):
    """
    Extension for handling USD Storage API authentication via livestream messaging.

    This extension listens for authentication requests from the web portal and
    responds with authentication status and tokens.
    """

    def _init_attrs(self):
        """Initialize instance attributes (also called from on_startup for hot-reload safety)."""
        self._auth_handler: Optional[StorageAuthHandler] = None
        self._client_connected_sub = None
        self._discovery_removed_sub = None
        self._mount_task = None
        self._skip_current_url: Optional[asyncio.Event] = None
        self._current_auth_url: Optional[str] = None
        self._main_loop = None
        self._progress_dialog = None
        self._timeout_dialog = None
        self._error_dialog = None

    def __init__(self):
        super().__init__()
        self._init_attrs()

    def on_startup(self, ext_id: str):
        """Called when the extension is enabled."""
        self._init_attrs()
        self._main_loop = asyncio.get_event_loop()

        global _extension_instance
        _extension_instance = self

        self._auth_handler = StorageAuthHandler()
        self._auth_handler.on_auth_started = self._on_auth_started
        self._auth_handler.on_auth_succeeded = self._on_auth_succeeded
        self._auth_handler.on_auth_timeout = self._on_auth_timeout
        self._auth_handler.on_auth_error = self._on_auth_error

        self._subscribe_to_discovery_removed()

        preconfigured = StorageAuthHandler.get_preconfigured_urls()
        if preconfigured:
            self._subscribe_to_client_connected(preconfigured)

    def _subscribe_to_discovery_removed(self):
        """Clean up our state when a discovery server is removed via connection_manager."""
        try:
            from omni.kit.widget.connection_manager import DISCOVERY_SERVER_REMOVED_EVENT
        except ImportError:
            return

        ed = get_eventdispatcher()
        self._discovery_removed_sub = ed.observe_event(
            observer_name="omni.storage_api.auth:discovery_removed",
            event_name=DISCOVERY_SERVER_REMOVED_EVENT,
            on_event=self._on_discovery_removed,
        )

    def _on_discovery_removed(self, event):
        """Release auth state for a discovery URL removed from Content Browser."""
        url = event.payload.get("url")
        if not url or not self._auth_handler:
            return

        self._auth_handler.unregister_handler(url)
        self._auth_handler._request_handles.pop(url, None)
        carb.log_info(f"[omni.storage_api.auth] Released auth state for removed discovery {url!r}")

    def _subscribe_to_client_connected(self, preconfigured: set):
        """Subscribe to the client_connected event to trigger preconfigured URL mounting."""
        omni.kit.app.register_event_alias(
            carb.events.type_from_string(CLIENT_CONNECTED_EVENT),
            CLIENT_CONNECTED_EVENT,
        )

        ed = get_eventdispatcher()
        self._client_connected_sub = ed.observe_event(
            observer_name="omni.storage_api.auth:client_connected",
            event_name=CLIENT_CONNECTED_EVENT,
            on_event=lambda event: self._on_client_connected(event, preconfigured),
        )
        carb.log_info(
            f"[omni.storage_api.auth] Waiting for streaming client before mounting "
            f"{len(preconfigured)} preconfigured URL(s)"
        )

    def _on_client_connected(self, event, preconfigured: set):
        """Called when a streaming client connects — mounts preconfigured URLs."""
        if self._mount_task is not None:
            carb.log_info("[omni.storage_api.auth] Mount already in progress or completed — skipping")
            return

        carb.log_info("[omni.storage_api.auth] Streaming client connected — starting preconfigured mount")
        self._mount_task = asyncio.run_coroutine_threadsafe(
            self._auto_mount_on_connect(preconfigured),
            loop=self._main_loop,
        )

    def _cancel_current_auth(self):
        """Cancel the in-flight auth (preconfigured mount skips current URL; interactive marks entry as ERROR)."""
        if self._skip_current_url:
            carb.log_info("[omni.storage_api.auth] User cancelled preconfigured URL mount")
            self._skip_current_url.set()
        elif self._current_auth_url and self._auth_handler:
            cancelled_url = self._current_auth_url
            carb.log_info(f"[omni.storage_api.auth] User cancelled auth for {cancelled_url!r}")
            self._auth_handler._cleanup_callback_auth(cancelled_url)
            self._mark_placeholders_as_disconnected([cancelled_url])
        self._current_auth_url = None

    async def _auto_mount_on_connect(self, preconfigured: set):
        """Mount preconfigured URLs sequentially; cancel skips the current one and moves on."""
        if not self._auth_handler:
            return

        # Let the UI settle after client_connected fires.
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        url_list = list(preconfigured)
        results = {}

        for url in url_list:
            self._skip_current_url = asyncio.Event()

            # NOTE: ``discover_and_register`` enforces its own auth-callback timeout
            # via ``_start_callback_auth_timeout`` (which reads the portal-supplied
            # value each invocation). The ``timeout`` here is a safety ceiling for
            # the whole discovery call, not the auth wait — use the default so a
            # slow ``register_storage_from_discovery_with_callback`` completion
            # isn't misreported as an auth timeout.
            discover_task = asyncio.ensure_future(self._auth_handler.discover_and_register(url))

            # Wait for either discovery to complete or the user to click Cancel.
            skip_task = asyncio.ensure_future(self._skip_current_url.wait())
            done, _ = await asyncio.wait([discover_task, skip_task], return_when=asyncio.FIRST_COMPLETED)

            if skip_task in done:
                # User cancelled — abort this URL's discovery and move on.
                discover_task.cancel()
                try:
                    await discover_task
                except (asyncio.CancelledError, Exception):
                    pass
                carb.log_info(f"[omni.storage_api.auth] Skipped {url} (user cancelled)")
                self._dismiss_progress_dialog()
                continue
            else:
                skip_task.cancel()

            try:
                addresses = discover_task.result()
                results[url] = addresses
                self._register_with_content_browser({url: addresses})
                carb.log_info(f"[omni.storage_api.auth] Mounted {url} with {len(addresses)} server(s)")
            except Exception as e:
                carb.log_error(f"[omni.storage_api.auth] Failed to mount {url}: {e}")

            self._dismiss_progress_dialog()

        self._skip_current_url = None

        # Add placeholders for any URLs that were not successfully mounted.
        failed = {url: () for url in url_list if url not in results}
        if failed:
            self._register_with_content_browser(failed)
            self._mark_placeholders_as_disconnected(list(failed.keys()))

    def _register_with_content_browser(self, results: dict):
        """Register servers with the Content Browser (real addresses transfer our handle; empty = placeholder)."""
        try:
            from omni.kit.widget.connection_manager import get_instance as get_connection_manager

            mgr = get_connection_manager()
            if not mgr:
                carb.log_warn("[omni.storage_api.auth] ConnectionManager not available")
                return

            for discovery_url, addresses in results.items():
                addr_list = list(addresses)
                mgr.registry.add_discovery_server(
                    name=discovery_url,
                    discovery_url=discovery_url,
                    cached_addresses=addr_list,
                )
                # Transfer handle so connection_manager won't re-run discovery.
                if addr_list and self._auth_handler:
                    request_handle = self._auth_handler._request_handles.get(discovery_url)
                    if request_handle:
                        internal = mgr.registry._get_discovery_entry_by_url(discovery_url)
                        if internal:
                            from omni.kit.widget.connection_manager import ConnectionStatus

                            internal.registration_handle = request_handle
                            internal.state.cached_addresses = addr_list
                            internal.state.status = ConnectionStatus.CONNECTED
                            internal.discovery_event.set()
                carb.log_info(
                    f"[omni.storage_api.auth] Registered {discovery_url} in Content Browser "
                    f"with {len(addr_list)} address(es)"
                )
        except ImportError:
            carb.log_verbose(
                "[omni.storage_api.auth] connection_manager not available — "
                "servers registered with omni.client but not shown in Content Browser"
            )
        except Exception as e:
            carb.log_warn(f"[omni.storage_api.auth] Failed to register with Content Browser: {e}")

    def _mark_placeholders_as_disconnected(self, urls):
        """Mark entries as ERROR so the user can right-click to retry discovery."""
        try:
            from omni.kit.widget.connection_manager import ConnectionStatus
            from omni.kit.widget.connection_manager import get_instance as get_cm

            mgr = get_cm()
            if not mgr:
                return

            for url in urls:
                internal = mgr.registry._get_discovery_entry_by_url(url)
                if internal:
                    internal.state.status = ConnectionStatus.ERROR
                    internal.state.error_message = "Authentication failed or timed out"
                    internal.discovery_event.set()
        except Exception:
            pass

    def on_shutdown(self):
        """Called when the extension is disabled."""
        if self._client_connected_sub:
            self._client_connected_sub.reset()
            self._client_connected_sub = None

        if self._discovery_removed_sub:
            self._discovery_removed_sub.reset()
            self._discovery_removed_sub = None

        if self._mount_task and not self._mount_task.done():
            self._mount_task.cancel()
        self._mount_task = None

        if self._progress_dialog:
            try:
                self._progress_dialog.hide()
                self._progress_dialog.destroy()
            except Exception:
                pass
            self._progress_dialog = None

        if self._timeout_dialog:
            try:
                self._timeout_dialog.hide()
                self._timeout_dialog.destroy()
            except Exception:
                pass
            self._timeout_dialog = None

        if self._error_dialog:
            try:
                self._error_dialog.hide()
                self._error_dialog.destroy()
            except Exception:
                pass
            self._error_dialog = None

        global _extension_instance
        _extension_instance = None

        if self._auth_handler:
            self._auth_handler.destroy()
            self._auth_handler = None

    def _on_auth_started(self, server_url: str):
        """Called when auth is forwarded to the portal; defers dialog to not block the callback."""
        self._current_auth_url = server_url
        asyncio.ensure_future(self._show_progress_dialog_delayed(server_url))

    async def _show_progress_dialog_delayed(self, server_url: str):
        """Show our progress dialog after a few frames (lets the UI settle)."""
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        if self._current_auth_url != server_url:
            return

        try:
            from .auth_dialog import AuthStatusDialog

            # Reuse a single AuthStatusDialog across auth sessions — creating
            # and destroying widgets per auth causes heavy widget churn that
            # triggers a Kit ``RasterImageProvider::_waitAsset`` deadlock in
            # streaming mode. Just hide/show/update-status on the same dialog.
            if self._progress_dialog is None:
                self._progress_dialog = AuthStatusDialog(
                    title="Omniverse Storage Authentication",
                    cancel_callback=self._cancel_current_auth,
                )

            self._progress_dialog.set_status(
                f"Authenticating with web portal...\n\nServer: {server_url}\n\n"
                "Please complete sign-in in your browser if prompted."
            )
            self._progress_dialog.show()
            asyncio.ensure_future(self._center_dialog_window_async(self._progress_dialog._window))
        except Exception as e:
            carb.log_warn(f"[omni.storage_api.auth] Failed to show progress dialog: {e}")

    def _on_auth_succeeded(self, server_url: str):
        """Called by the auth handler when a callback-initiated auth succeeds."""
        carb.log_info(f"[omni.storage_api.auth] Auth succeeded for {server_url!r}, closing dialog")
        self._current_auth_url = None
        self._dismiss_progress_dialog()

    def _dismiss_progress_dialog(self):
        """Hide the progress dialog (kept alive for reuse across auth sessions)."""
        if self._progress_dialog:
            try:
                self._progress_dialog.hide()
            except Exception:
                pass

    @staticmethod
    def _format_timeout_seconds(timeout: float) -> str:
        """Format timeout seconds without a trailing decimal for whole numbers."""
        return str(int(timeout)) if float(timeout).is_integer() else f"{timeout:g}"

    def _on_auth_timeout(self, server_url: str, timeout: float):
        """Called by the auth handler when a callback-initiated auth times out."""
        self._current_auth_url = None
        self._dismiss_progress_dialog()
        self._mark_placeholders_as_disconnected([server_url])
        self._show_auth_timeout_dialog(server_url, timeout)

    def _on_auth_error(self, discovery_url: str, error_code: str, error_message: str):
        """Called when the portal reports an authentication failure."""
        self._current_auth_url = None
        self._dismiss_progress_dialog()
        self._mark_placeholders_as_disconnected([discovery_url])
        self._show_auth_error_dialog(discovery_url, error_code, error_message)

    def _show_auth_error_dialog(self, discovery_url: str, error_code: str, error_message: str) -> None:
        """Show a modal error with the message reported by the portal."""
        try:
            from omni.kit.window.popup_dialog import MessageDialog

            if self._error_dialog:
                self._error_dialog.hide()
                self._error_dialog = None

            message = "\n\n".join(
                [
                    error_message,
                    f"Server: {discovery_url}",
                ]
            )

            def _on_ok(dialog):
                dialog.hide()
                if self._error_dialog is dialog:
                    self._error_dialog = None

            self._error_dialog = MessageDialog(
                title="Omniverse Storage Authentication Failed",
                message=message,
                ok_handler=_on_ok,
                ok_label="OK",
                disable_cancel_button=True,
            )
            self._error_dialog.show()
            asyncio.ensure_future(self._center_dialog_window_async(self._error_dialog))
        except ImportError:
            carb.log_warn(
                f"[omni.storage_api.auth] Auth error for {discovery_url!r}: "
                f"{error_code} - {error_message} (popup_dialog not available to show UI)"
            )
        except Exception as e:
            carb.log_warn(f"[omni.storage_api.auth] Failed to show auth error dialog: {e}")

    def _show_auth_timeout_dialog(self, server_url: str, timeout: float) -> None:
        """Show a modal error when auth times out waiting on the portal."""
        timeout_text = self._format_timeout_seconds(timeout)
        try:
            from omni.kit.window.popup_dialog import MessageDialog

            if self._timeout_dialog:
                self._timeout_dialog.hide()
                self._timeout_dialog = None

            message = "\n\n".join(
                [
                    f"Connection to web portal timed out after {timeout_text} seconds.",
                    f"Server: {server_url}",
                    "Please retry authentication and complete the web portal sign-in before the timeout expires.",
                ]
            )

            def _on_ok(dialog):
                dialog.hide()
                if self._timeout_dialog is dialog:
                    self._timeout_dialog = None

            self._timeout_dialog = MessageDialog(
                title="Omniverse Storage Authentication Timed Out",
                message=message,
                ok_handler=_on_ok,
                ok_label="OK",
                disable_cancel_button=True,
            )
            self._timeout_dialog.show()
            asyncio.ensure_future(self._center_dialog_window_async(self._timeout_dialog))
        except ImportError:
            carb.log_warn(
                f"[omni.storage_api.auth] Auth timed out for {server_url!r} after {timeout_text}s "
                f"(popup_dialog not available to show UI)"
            )
        except Exception as e:
            carb.log_warn(f"[omni.storage_api.auth] Failed to show timeout dialog: {e}")

    async def _center_dialog_window_async(self, dialog) -> None:
        """Center a popup/window after layout (accepts a dialog with ``.window`` attr or a raw ``ui.Window``)."""
        import omni.ui as ui

        for _ in range(2):
            await omni.kit.app.get_app().next_update_async()

        if not dialog:
            return

        window = getattr(dialog, "window", None)
        if window is None and hasattr(dialog, "frame"):
            window = dialog
        if not window:
            return

        dialog_width = window.frame.computed_width or window.width
        dialog_height = window.frame.computed_height or window.height
        app_width = ui.Workspace.get_main_window_width()
        app_height = ui.Workspace.get_main_window_height()

        if dialog_width < app_width:
            window.position_x = (app_width - dialog_width) / 2
        if dialog_height < app_height:
            window.position_y = (app_height - dialog_height) / 2

    def get_auth_handler(self) -> Optional[StorageAuthHandler]:
        """Return the StorageAuthHandler instance, or None if not initialized."""
        return self._auth_handler

    async def discover_and_register(self, discovery_url: str, timeout: float = 60.0) -> Tuple[str, ...]:
        """Convenience wrapper around ``StorageAuthHandler.discover_and_register``."""
        if not self._auth_handler:
            raise RuntimeError("Auth handler not initialized")
        return await self._auth_handler.discover_and_register(discovery_url, timeout)
