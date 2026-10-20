"""
USD Storage Auth Handler

Intermediate layer between the Client Library and Web Portal,
communicating authentication events via the streaming data channel.
"""

import asyncio
import threading
from typing import Any, Dict, Optional, Set, Tuple

import carb
import carb.events
import carb.settings
import omni.client
import omni.kit.app
import omni.kit.livestream.messaging as messaging
from carb.eventdispatcher import get_eventdispatcher

REFRESH_ACCESS_TOKEN_EVENT = "refreshAccessToken"
REQUEST_TOKEN_REFRESH_EVENT = "requestTokenRefresh"
ADD_NEW_STORAGE_URL_EVENT = "addNewStorageUrl"
AUTHENTICATION_ERROR_EVENT = "authenticationError"


class AuthPortalError(Exception):
    """Auth failure reported by the portal via ``authenticationError``."""

    def __init__(self, discovery_url: str, error_code: str, error_message: str):
        super().__init__(f"{error_code}: {error_message}")
        self.discovery_url = discovery_url
        self.error_code = error_code
        self.error_message = error_message


class StorageAuthHandler:
    """Broker portal-based storage auth: register a singleton auth callback,
    forward requests to the Web Portal via livestream messaging, apply received
    tokens to the Client Library."""

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Strip surrounding whitespace and trailing slashes for consistent dict keys."""
        return url.strip().rstrip("/")

    def __init__(self):
        self._lock = threading.RLock()
        self._registered_discovery_urls: Set[str] = set()
        self._auth_handle_ints: Dict[str, int] = {}
        self._handled_auth_handles: Set[int] = set()
        self._subscriptions = []
        self._pending_auth_requests: Dict[str, asyncio.Future] = {}
        self._pending_discovery_futures: Dict[str, asyncio.Future] = {}
        # Kept alive to prevent invalidating storage registrations.
        self._request_handles: Dict[str, Any] = {}
        self._callback_auth_tasks: Dict[str, asyncio.Task] = {}

        self._in_auth_callback = False

        # Kit's main event loop + thread id, captured at init time (we assume
        # the extension starts on the main thread). Needed to marshal work
        # from ``omni.client`` auth-callback worker threads (e.g. ``Dummy-1``),
        # where ``asyncio.get_event_loop()`` raises and future/task creation fails.
        try:
            self._main_loop: Optional[asyncio.AbstractEventLoop] = asyncio.get_event_loop()
        except RuntimeError:
            self._main_loop = None
        self._main_thread_id: int = threading.get_ident()

        # Normalized URLs whose last portal attempt failed (error or timeout).
        # While present, ``_single_auth_callback`` accepts (returns True, releases
        # the handle) without re-dispatching to the portal — this is what stops
        # ``omni.client``'s internal retry from re-entering us every 10s and
        # spamming ``addNewStorageUrl``. Cleared by ``discover_and_register`` /
        # ``unregister_handler`` so explicit retries start fresh.
        self._errored_servers: Set[str] = set()

        # Timeout supplied by the portal via ``refreshAccessToken.auth_timeout``.
        # Updated on each refresh; consumed by new auth flows only (not the
        # current in-flight one) so the portal can tune our timeout over time.
        self._portal_auth_timeout: Optional[float] = None

        self.on_auth_started: Optional[Any] = None
        self.on_auth_succeeded: Optional[Any] = None
        self.on_auth_timeout: Optional[Any] = None
        self.on_auth_error: Optional[Any] = None

        outgoing = (ADD_NEW_STORAGE_URL_EVENT, REQUEST_TOKEN_REFRESH_EVENT)
        for event in outgoing:
            messaging.register_event_type_to_send(event)
            omni.kit.app.register_event_alias(
                carb.events.type_from_string(event),
                event,
            )

        ed = get_eventdispatcher()

        incoming = {
            REFRESH_ACCESS_TOKEN_EVENT: self._on_token_refresh_response,
            AUTHENTICATION_ERROR_EVENT: self._on_authentication_error,
        }

        for event_type, handler in incoming.items():
            # TODO: Remove this when all clients have migrated to Events 2.0
            omni.kit.app.register_event_alias(
                carb.events.type_from_string(event_type),
                event_type,
            )

            self._subscriptions.append(
                ed.observe_event(
                    observer_name=f"USD Storage API Auth:{event_type}",
                    event_name=event_type,
                    on_event=handler,
                )
            )
        self._singleton_auth_handle = omni.client.register_storage_auth_callback(self._single_auth_callback)

    def destroy(self):
        """Clear all auth state and cancel any running timeout tasks."""
        with self._lock:
            if self._registered_discovery_urls:
                self._registered_discovery_urls.clear()

            if self._auth_handle_ints:
                self._auth_handle_ints.clear()

            if self._handled_auth_handles:
                self._handled_auth_handles.clear()

            if self._pending_auth_requests:
                self._pending_auth_requests.clear()

            if self._pending_discovery_futures:
                self._pending_discovery_futures.clear()

            if self._request_handles:
                self._request_handles.clear()

            if self._callback_auth_tasks:
                for task in self._callback_auth_tasks.values():
                    if not task.done():
                        task.cancel()
                self._callback_auth_tasks.clear()

            if self._errored_servers:
                self._errored_servers.clear()

            self.on_auth_started = None
            self.on_auth_succeeded = None
            self.on_auth_timeout = None
            self.on_auth_error = None

            self._portal_auth_timeout = None

            self._singleton_auth_handle = None

            if self._subscriptions:
                self._subscriptions.clear()

    def _resolve_url_key(self, incoming_url: str, registry: Dict[str, Any]) -> Optional[str]:
        """Find the stored key that matches ``incoming_url`` (exact, then normalized); None if no match."""
        if incoming_url in registry:
            return incoming_url

        incoming_norm = self._normalize_url(incoming_url)
        for stored_key in registry:
            if self._normalize_url(stored_key) == incoming_norm:
                carb.log_warn(
                    f"[omni.storage_api.auth] URL matched after normalization: "
                    f"incoming={incoming_url!r} stored={stored_key!r}"
                )
                return stored_key

        carb.log_warn(
            f"[omni.storage_api.auth] No matching URL found for {incoming_url!r}. "
            f"Registered keys: {list(registry.keys())}"
        )
        return None

    def _on_token_refresh_response(self, event: carb.events.IEvent):
        """Apply a token from the portal to the matching auth handle (``discovery_url="*"`` = all handles)."""
        if "access_token" not in event.payload:
            carb.log_error(f"Invalid token refresh response - missing access_token")
            return

        access_token = event.payload["access_token"]
        discovery_url = event.payload.get("discovery_url", "*")

        # Portal may include its configured timeout; apply to future flows only.
        self._maybe_update_portal_auth_timeout(event.payload.get("auth_timeout"))

        carb.log_verbose(f"Received token refresh for: {discovery_url!r}")

        if discovery_url == "*":
            for url in list(self._auth_handle_ints.keys()):
                handle = self._auth_handle_ints[url]
                try:
                    result = omni.client.set_storage_access_token(handle, access_token)
                    if result:
                        carb.log_verbose(f"Refreshed token for {url}")
                    else:
                        carb.log_error(f"Failed to refresh token for {url}")
                except Exception as e:
                    carb.log_error(f"Error refreshing token for {url}: {e}")

                pending_key = self._resolve_url_key(url, self._pending_auth_requests)
                if pending_key:
                    future = self._pending_auth_requests.pop(pending_key)
                    if not future.done():
                        future.set_result(access_token)
            return

        handle_key = self._resolve_url_key(discovery_url, self._auth_handle_ints)

        if handle_key is None:
            carb.log_warn(f"[omni.storage_api.auth] No auth handle for {discovery_url!r}, ignoring token")
            return

        handle = self._auth_handle_ints[handle_key]
        result = omni.client.set_storage_access_token(handle, access_token)

        pending_key = self._resolve_url_key(discovery_url, self._pending_auth_requests)

        if not result:
            carb.log_error(f"Failed to set token for {discovery_url}")
            if pending_key:
                future = self._pending_auth_requests.pop(pending_key)
                if not future.done():
                    future.set_exception(Exception(f"Failed to set token for {discovery_url}"))
        else:
            carb.log_verbose(f"Successfully set token for {discovery_url}")
            if pending_key:
                future = self._pending_auth_requests.pop(pending_key)
                if not future.done():
                    future.set_result(access_token)

    def _maybe_update_portal_auth_timeout(self, value: Any) -> None:
        """Store a portal-provided timeout (seconds) for use by subsequent auth flows."""
        if value is None:
            return
        try:
            seconds = float(value)
        except (TypeError, ValueError):
            carb.log_warn(f"[omni.storage_api.auth] Ignoring non-numeric auth_timeout {value!r}")
            return
        if seconds <= 0:
            carb.log_warn(f"[omni.storage_api.auth] Ignoring non-positive auth_timeout {seconds}")
            return
        if self._portal_auth_timeout != seconds:
            carb.log_info(
                f"[omni.storage_api.auth] Portal auth_timeout updated to {seconds}s " f"(applies to future auth flows)"
            )
        self._portal_auth_timeout = seconds

    def get_effective_auth_timeout(self) -> float:
        """Portal-supplied timeout if set, otherwise the ``authCallbackTimeout`` setting (default 60s)."""
        if self._portal_auth_timeout is not None:
            return self._portal_auth_timeout
        settings = carb.settings.get_settings()
        return settings.get_as_float("/exts/omni.storage_api.auth/authCallbackTimeout") or 60.0

    def _on_authentication_error(self, event: carb.events.IEvent):
        """Portal reported an auth failure; cancel the pending flow and surface the message."""
        payload = event.payload or {}
        discovery_url = payload.get("discovery_url")
        error_code = str(payload.get("error_code", "unknown"))
        error_message = str(payload.get("error_message", "Authentication failed."))

        if not discovery_url:
            carb.log_error("[omni.storage_api.auth] authenticationError missing discovery_url; ignoring")
            return

        carb.log_warn(
            f"[omni.storage_api.auth] Portal auth error for {discovery_url!r}: " f"{error_code} - {error_message}"
        )

        exc = AuthPortalError(discovery_url, error_code, error_message)

        # Fail any pending auth future so discover_and_register unblocks promptly.
        pending_key = self._resolve_url_key(discovery_url, self._pending_auth_requests)
        if pending_key:
            future = self._pending_auth_requests.pop(pending_key)
            if not future.done():
                future.set_exception(exc)

        # Fail the discovery future too so callers don't wait out the full timeout.
        disc_key = self._resolve_url_key(discovery_url, self._pending_discovery_futures)
        if disc_key:
            disc_future = self._pending_discovery_futures.pop(disc_key)
            if not disc_future.done():
                disc_future.set_exception(exc)

        # If neither future was live, the request was already cancelled/timed-out
        # locally — don't surface a late portal response as a new error dialog.
        was_live = bool(pending_key or disc_key)

        self._cleanup_callback_auth(discovery_url)

        if not was_live:
            carb.log_info(
                f"[omni.storage_api.auth] Dropping late portal error for {discovery_url!r} "
                "— request was already cancelled or cleaned up"
            )
            return

        if self.on_auth_error:
            try:
                self.on_auth_error(discovery_url, error_code, error_message)
            except Exception as e:
                carb.log_warn(f"[omni.storage_api.auth] on_auth_error callback raised: {e}")

    @staticmethod
    def _send_token_refresh_request(discovery_url: str):
        """Dispatch a ``requestTokenRefresh`` event to the Web Portal."""
        get_eventdispatcher().dispatch_event(REQUEST_TOKEN_REFRESH_EVENT, payload={"discovery_url": discovery_url})

    @staticmethod
    def _send_new_storage_url_request(discovery_url: str):
        """Dispatch an ``addNewStorageUrl`` event to the Web Portal."""
        get_eventdispatcher().dispatch_event(ADD_NEW_STORAGE_URL_EVENT, payload={"discovery_url": discovery_url})

    def _run_on_main_loop(self, fn):
        """Run ``fn()`` on the Kit main event loop.

        If we're already on the main thread, executes synchronously. Otherwise
        (e.g. ``omni.client`` invoked our auth callback on ``Dummy-1``), queues
        it via ``call_soon_threadsafe`` so asyncio future/task creation succeeds.
        """
        if threading.get_ident() == self._main_thread_id:
            fn()
            return
        if self._main_loop is not None:
            self._main_loop.call_soon_threadsafe(fn)
        else:
            carb.log_warn("[omni.storage_api.auth] No main event loop; dropping scheduled work")

    def _single_auth_callback(self, auth_handle: int, server: str) -> bool:
        """Singleton auth callback: always accepts, stores handle, forwards request to the portal.

        Always returns True so ``omni.client`` never falls through to other registered
        local auth callbacks. The portal responds via ``refreshAccessToken``; failures
        come via ``authenticationError`` and clean up URL-level state so a subsequent
        ``discover_and_register`` re-initiates the portal flow.
        """
        try:
            with self._lock:
                if self._in_auth_callback:
                    carb.log_warn(
                        "[omni.storage_api.auth] Auth callback: reentrancy, returning True without re-dispatch"
                    )
                    return True
                self._in_auth_callback = True

            if auth_handle in self._handled_auth_handles:
                carb.log_verbose("[omni.storage_api.auth] Auth callback: already handled this handle, return True")
                return True

            server_normalized = self._normalize_url(server)

            # Errored — short-circuit (see `_errored_servers` comment on __init__):
            # accept + empty-token the handle, skip portal dispatch.
            if server_normalized in self._errored_servers:
                self._handled_auth_handles.add(auth_handle)
                self._release_client_auth_handle(auth_handle)
                carb.log_verbose(
                    f"[omni.storage_api.auth] Auth callback: {server!r} is in errored state, "
                    "returning True without portal dispatch"
                )
                return True

            # If already registered, apply cached token or request refresh.
            # Do NOT return True without setting a token — the Client Library hangs.
            already_registered = any(self._normalize_url(k) == server_normalized for k in self._request_handles)
            if already_registered:
                self._handled_auth_handles.add(auth_handle)
                self._auth_handle_ints[server] = auth_handle

                def _main_reauth():
                    if server_normalized not in self._pending_auth_requests and self._main_loop is not None:
                        reauth_future = self._main_loop.create_future()
                        self._pending_auth_requests[server_normalized] = reauth_future
                        self._start_callback_auth_timeout(server, reauth_future)
                    StorageAuthHandler._send_new_storage_url_request(server)

                self._run_on_main_loop(_main_reauth)
                carb.log_info(
                    f"[omni.storage_api.auth] Auth callback: requesting token refresh for "
                    f"already-registered {server!r}"
                )
                return True

            discovery_url = None
            for url in list(self._pending_auth_requests.keys()):
                url_norm = self._normalize_url(url)
                if server_normalized == url_norm or url_norm in server_normalized:
                    discovery_url = url
                    carb.log_verbose(
                        f"[omni.storage_api.auth] Auth callback match: server {server!r} -> pending request {url!r}"
                    )
                    break

            # No pending request — Client Library triggered auth on its own;
            # forward to portal with a timeout.
            if not discovery_url:
                discovery_url = server
                carb.log_info(
                    f"[omni.storage_api.auth] Auth callback: no pending request for server={server!r}, "
                    f"forwarding to portal directly"
                )

            normalized = self._normalize_url(discovery_url)
            self._handled_auth_handles.add(auth_handle)
            self._auth_handle_ints[discovery_url] = auth_handle

            # Future/task creation + on_auth_started (UI coroutine) + portal
            # dispatch all need the main event loop. ``omni.client`` may invoke
            # us on a worker thread (``Dummy-N``); marshal the work accordingly.
            dispatch_url = discovery_url

            def _main_initial_auth():
                if normalized not in self._pending_auth_requests and self._main_loop is not None:
                    future = self._main_loop.create_future()
                    self._pending_auth_requests[normalized] = future
                    self._start_callback_auth_timeout(dispatch_url, future)
                StorageAuthHandler._send_new_storage_url_request(dispatch_url)
                if self.on_auth_started:
                    try:
                        self.on_auth_started(dispatch_url)
                    except Exception as e:
                        carb.log_warn(f"[omni.storage_api.auth] on_auth_started callback raised: {e}")

            self._run_on_main_loop(_main_initial_auth)

            return True

        except Exception as e:
            carb.log_error(f"Auth callback exception: {e}")
            return True
        finally:
            with self._lock:
                self._in_auth_callback = False

    def _start_callback_auth_timeout(self, server_url: str, future: asyncio.Future):
        """Start a task that waits for the portal response; fires ``on_auth_succeeded``/``on_auth_timeout``."""
        timeout = self.get_effective_auth_timeout()
        normalized = self._normalize_url(server_url)

        if normalized in self._callback_auth_tasks:
            existing = self._callback_auth_tasks[normalized]
            if not existing.done():
                return

        async def _wait():
            try:
                await asyncio.wait_for(asyncio.shield(future), timeout=timeout)
                carb.log_info(f"[omni.storage_api.auth] Portal responded for {server_url!r} within timeout")
                if self.on_auth_succeeded:
                    self.on_auth_succeeded(server_url)
            except asyncio.TimeoutError:
                carb.log_warn(
                    f"[omni.storage_api.auth] Portal did not respond for {server_url!r} " f"after {timeout:.0f}s"
                )
                self._cleanup_callback_auth(server_url)

                if self.on_auth_timeout:
                    self.on_auth_timeout(server_url, timeout)
            except AuthPortalError:
                # ``_on_authentication_error`` already cleaned up and notified listeners.
                pass
            except asyncio.CancelledError:
                pass
            finally:
                self._callback_auth_tasks.pop(normalized, None)

        try:
            loop = asyncio.get_event_loop()
            if loop and loop.is_running():
                self._callback_auth_tasks[normalized] = loop.create_task(_wait())
            else:
                carb.log_warn("[omni.storage_api.auth] No running event loop for auth timeout task")
        except Exception as e:
            carb.log_warn(f"[omni.storage_api.auth] Failed to start auth timeout task: {e}")

    @staticmethod
    def _release_client_auth_handle(handle: int) -> None:
        """Push an empty token so in-flight ``omni.client`` ops pinned on this handle
        resolve with auth failure and release the ``Core`` reader rwlock — without this,
        a later ``omniClientStop`` (write lock) deadlocks (cf. commit d26d1e93).
        """
        try:
            omni.client.set_storage_access_token(handle, "")
        except Exception as e:
            carb.log_warn(f"[omni.storage_api.auth] Failed to release client auth handle {handle}: {e}")

    def _cleanup_callback_auth(self, server_url: str):
        """Drop all state for a failed/timed-out/cancelled auth so the next retry starts fresh."""
        normalized = self._normalize_url(server_url)

        for key in (server_url, normalized):
            future = self._pending_auth_requests.pop(key, None)
            if future and not future.done():
                future.cancel()

        # Also cancel the pending discovery future so ``discover_and_register``
        # unblocks immediately on auth-level failures instead of waiting for
        # its outer timeout to expire.
        for key in (server_url, normalized):
            disc_future = self._pending_discovery_futures.pop(key, None)
            if disc_future and not disc_future.done():
                disc_future.cancel()

        for key in (server_url, normalized):
            handle = self._auth_handle_ints.pop(key, None)
            if handle is not None:
                self._handled_auth_handles.discard(handle)
                self._release_client_auth_handle(handle)

        for key in (server_url, normalized):
            self._request_handles.pop(key, None)

        self._registered_discovery_urls.discard(normalized)

        # Cancel the auth-timeout wait task — unless we're being called from
        # inside it (the timeout branch). Self-cancel is a no-op, but checking
        # avoids a useless CancelledError log.
        self._cancel_callback_auth_task(normalized)

        # See `_errored_servers` comment on __init__ for why we mark here.
        self._errored_servers.add(normalized)

        carb.log_info(f"[omni.storage_api.auth] Cleaned up auth state for {server_url!r}")

    def _cancel_callback_auth_task(self, normalized_url: str) -> None:
        """Cancel the ``_callback_auth_tasks`` entry for ``normalized_url`` unless that
        task is the currently-running one (avoids a pointless self-cancel)."""
        task = self._callback_auth_tasks.get(normalized_url)
        if task is None or task.done():
            return
        try:
            if asyncio.current_task() is task:
                return
        except RuntimeError:
            pass  # Called from a non-asyncio thread — cancel anyway.
        task.cancel()

    def _cleanup_failed_discovery(self, normalized_url: str, discovery_url: str):
        """Clean up all state for a failed/timed-out/canceled discovery so retries work."""
        self._pending_auth_requests.pop(normalized_url, None)
        self._pending_discovery_futures.pop(normalized_url, None)
        self._request_handles.pop(discovery_url, None)
        # Also clear auth handles that the callback may have stored before the
        # discovery itself failed — otherwise the URL appears "already registered"
        # and retries in the same session are silently skipped.
        for key in (discovery_url, normalized_url):
            handle = self._auth_handle_ints.pop(key, None)
            if handle is not None:
                self._handled_auth_handles.discard(handle)
                self._release_client_auth_handle(handle)

        self._registered_discovery_urls.discard(normalized_url)

        # Cancel any lingering auth-timeout task so it can't fire stale UI.
        self._cancel_callback_auth_task(normalized_url)

        # Same reason as `_cleanup_callback_auth`: short-circuit future retries.
        self._errored_servers.add(normalized_url)

    def register_handler(self, discovery_url: str):
        """Mark a discovery URL as handled by this auth callback (normalized form stored)."""
        normalized = self._normalize_url(discovery_url)
        with self._lock:
            self._registered_discovery_urls.add(normalized)

    def unregister_handler(self, discovery_url: str):
        """Remove all auth state for a discovery URL (call when discovery is removed or fails)."""
        normalized = self._normalize_url(discovery_url)
        with self._lock:
            self._registered_discovery_urls.discard(normalized)
            self._errored_servers.discard(normalized)

            for key in (discovery_url, normalized):
                if key in self._auth_handle_ints:
                    handle = self._auth_handle_ints.pop(key)
                    self._handled_auth_handles.discard(handle)
                    break

            for key in (discovery_url, normalized):
                if key in self._pending_auth_requests:
                    future = self._pending_auth_requests.pop(key)
                    if not future.done():
                        future.cancel()
                    break

            for key in (discovery_url, normalized):
                if key in self._pending_discovery_futures:
                    disc_future = self._pending_discovery_futures.pop(key)
                    if not disc_future.done():
                        disc_future.cancel()
                    break

            # Cancel the auth-timeout task so its timeout / error path can't
            # surface stale UI after the discovery has been removed.
            self._cancel_callback_auth_task(normalized)

    async def discover_and_register(
        self,
        discovery_url: str,
        timeout: float = 180.0,
    ) -> Tuple[str, ...]:
        """Register a discovery URL with the Client Library and wait for discovery to complete.

        ``timeout`` is an outer safety ceiling on the whole call; auth-specific
        waits are enforced separately by ``_start_callback_auth_timeout`` using
        ``get_effective_auth_timeout()``. Auth failures (portal error, auth
        timeout, user cancel) cancel the discovery future directly, so the outer
        ``wait_for`` should rarely be the one to fire.
        """
        normalized_url = self._normalize_url(discovery_url)

        # Fresh attempt: drop any prior errored mark so the callback will dispatch.
        self._errored_servers.discard(normalized_url)

        try:
            self.register_handler(discovery_url)

            auth_future: asyncio.Future = asyncio.Future()
            self._pending_auth_requests[normalized_url] = auth_future

            discovery_future: asyncio.Future = asyncio.Future()
            self._pending_discovery_futures[normalized_url] = discovery_future

            def on_registered(result: omni.client.Result, addresses):
                if result != omni.client.Result.OK:
                    carb.log_error(f"Discovery failed for {discovery_url}: {result}")
                    if not discovery_future.done():
                        discovery_future.set_exception(Exception(f"Failed to register discovery: {result}"))
                    return
                if not discovery_future.done():
                    carb.log_verbose(
                        f"Discovery completed for {discovery_url}, "
                        f"found {len(addresses) if addresses else 0} servers"
                    )
                    discovery_future.set_result(tuple(addresses) if addresses else ())

            request = omni.client.register_storage_from_discovery_with_callback(discovery_url, on_registered)
            self._request_handles[discovery_url] = request

            try:
                addresses = await asyncio.wait_for(discovery_future, timeout=timeout)
            finally:
                # Tracker is only needed while awaiting; success or failure, stop holding it.
                self._pending_discovery_futures.pop(normalized_url, None)
            carb.log_info(f"Successfully registered {discovery_url} with {len(addresses)} server(s)")
            return addresses

        except asyncio.TimeoutError:
            carb.log_error(f"Discovery timed out for {discovery_url}")
            self._cleanup_failed_discovery(normalized_url, discovery_url)
            raise
        except asyncio.CancelledError:
            carb.log_info(f"Discovery canceled for {discovery_url}")
            self._cleanup_failed_discovery(normalized_url, discovery_url)
            raise
        except Exception:
            self._cleanup_failed_discovery(normalized_url, discovery_url)
            raise

    @staticmethod
    def get_preconfigured_urls() -> Set[str]:
        """Return the set of preconfigured discovery URLs from settings."""
        settings = carb.settings.get_settings()
        urls: Set[str] = set()

        preconfigured_list = settings.get("/exts/omni.storage_api.auth/preconfiguredDiscoveryUrls") or []
        if isinstance(preconfigured_list, list):
            for url in preconfigured_list:
                if url:
                    urls.add(url)

        return urls

    async def auto_mount_preconfigured(self, timeout_per_url: float = 180.0) -> Dict[str, Tuple[str, ...]]:
        """Run ``discover_and_register`` for each preconfigured URL sequentially, skipping already-registered ones.

        Sequential execution keeps the event loop free between URLs to process portal token responses.
        """
        urls = self.get_preconfigured_urls()
        if not urls:
            return {}

        carb.log_info(f"[omni.storage_api.auth] Auto-mounting {len(urls)} preconfigured discovery URL(s)")

        results: Dict[str, Tuple[str, ...]] = {}
        for url in urls:
            already_registered = (
                url in self._request_handles or self._resolve_url_key(url, self._auth_handle_ints) is not None
            )
            if already_registered:
                carb.log_info(f"[omni.storage_api.auth] Skipping already-registered {url}")
                continue

            try:
                addresses = await self.discover_and_register(url, timeout=timeout_per_url)
                results[url] = addresses
            except Exception as e:
                carb.log_error(f"[omni.storage_api.auth] Failed to auto-mount {url}: {e}")

        if results:
            carb.log_info(f"[omni.storage_api.auth] Auto-mounted {len(results)} preconfigured discovery URL(s)")

        return results

    @staticmethod
    def manual_token_refresh(deployment_url: str):
        """Manually dispatch a token refresh request (debug helper)."""
        StorageAuthHandler._send_token_refresh_request(deployment_url)

    @staticmethod
    def manual_new_storage_url(discovery_url: str):
        """Manually dispatch a new-storage-URL request (debug helper)."""
        StorageAuthHandler._send_new_storage_url_request(discovery_url)
