"""
Tests for the USD Storage API Authentication Handler
"""

import asyncio
from unittest.mock import MagicMock, patch

import carb
import carb.settings
import omni.client
import omni.kit.app
import omni.kit.test


class TestStorageAuthHandler(omni.kit.test.AsyncTestCase):
    """Tests for StorageAuthHandler and StorageAuthExtension."""

    async def test_extension_loads(self):
        """Extension enables successfully."""
        ext_manager = omni.kit.app.get_app().get_extension_manager()
        ext_manager.set_extension_enabled_immediate("omni.storage_api.auth", True)
        self.assertTrue(ext_manager.is_extension_enabled("omni.storage_api.auth"))

    async def test_handler_init_and_empty_state(self):
        """Handler constructs with empty state; destroy clears it."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        self.assertEqual(len(handler._registered_discovery_urls), 0)
        self.assertEqual(len(handler._auth_handle_ints), 0)
        self.assertEqual(len(handler._pending_auth_requests), 0)
        self.assertEqual(len(handler._handled_auth_handles), 0)

        handler.register_handler("https://a.example.com")
        handler.register_handler("https://b.example.com")
        self.assertEqual(len(handler._registered_discovery_urls), 2)

        handler.destroy()
        self.assertEqual(len(handler._registered_discovery_urls), 0)
        self.assertEqual(len(handler._auth_handle_ints), 0)

    async def test_register_handler_normalizes(self):
        """register_handler stores the normalized form (no trailing slash)."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        handler.register_handler("https://x.example.com/")
        self.assertIn("https://x.example.com", handler._registered_discovery_urls)
        self.assertNotIn("https://x.example.com/", handler._registered_discovery_urls)
        handler.destroy()

    async def test_unregister_handler_cross_slash(self):
        """unregister handles trailing-slash mismatch and also clears auth handles/futures."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        handler.register_handler("https://x.example.com/")
        handler._auth_handle_ints["https://x.example.com"] = 99
        handler._handled_auth_handles.add(99)
        future = asyncio.Future()
        handler._pending_auth_requests["https://x.example.com"] = future

        handler.unregister_handler("https://x.example.com")

        self.assertEqual(len(handler._registered_discovery_urls), 0)
        self.assertEqual(len(handler._auth_handle_ints), 0)
        self.assertEqual(len(handler._pending_auth_requests), 0)
        self.assertNotIn(99, handler._handled_auth_handles)
        handler.destroy()

    async def test_unregister_nonexistent_handler_does_not_crash(self):
        """unregister tolerates unknown URLs."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        handler.unregister_handler("https://nonexistent.example.com")
        handler.destroy()

    async def test_single_auth_callback_no_pending_request(self):
        """Auth callback always accepts and stores the handle even without a pending request."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        result = handler._single_auth_callback(42, "https://unknown.example.com")
        self.assertTrue(result)
        self.assertIn(42, handler._handled_auth_handles)
        self.assertIn("https://unknown.example.com", handler._auth_handle_ints)
        handler.destroy()

    async def test_auth_callback_reentrancy_guard(self):
        """Auth callback returns True when re-entered (never False, to avoid triggering other local callbacks)."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        handler._in_auth_callback = True
        self.assertTrue(handler._single_auth_callback(42, "https://example.com"))
        handler._in_auth_callback = False
        handler.destroy()

    async def test_on_token_refresh_missing_access_token(self):
        """Token refresh without access_token is logged and ignored."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()

        class MockEvent:
            payload = {"discovery_url": "https://example.com"}

        handler._on_token_refresh_response(MockEvent())
        handler.destroy()

    async def test_get_instance_and_handler(self):
        """get_instance returns the extension; the extension exposes the auth handler."""
        from omni.storage_api.auth import get_instance

        instance = get_instance()
        self.assertIsNotNone(instance)
        self.assertIsNotNone(instance.get_auth_handler())

    # --- URL Normalization ---

    async def test_normalize_url(self):
        """_normalize_url strips whitespace and trailing slashes."""
        from omni.storage_api.auth import StorageAuthHandler

        n = StorageAuthHandler._normalize_url
        self.assertEqual(n("https://example.com/"), "https://example.com")
        self.assertEqual(n("https://example.com///"), "https://example.com")
        self.assertEqual(n("  https://example.com  "), "https://example.com")
        self.assertEqual(n("https://example.com"), "https://example.com")
        self.assertEqual(n(""), "")

    async def test_resolve_url_key(self):
        """_resolve_url_key: exact match, normalized fallback, or None."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        registry = {"https://example.com": "val"}
        self.assertEqual(handler._resolve_url_key("https://example.com", registry), "https://example.com")
        self.assertEqual(handler._resolve_url_key("https://example.com/", registry), "https://example.com")
        self.assertIsNone(handler._resolve_url_key("https://other.com", registry))
        handler.destroy()

    # --- Token Refresh ---

    async def test_on_token_refresh_normalized_url_matches_stored(self):
        """Portal response with trailing slash still matches the stored key."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        handler._auth_handle_ints["https://example.com"] = 42
        future = asyncio.Future()
        handler._pending_auth_requests["https://example.com"] = future

        class MockEvent:
            payload = {"access_token": "tok", "discovery_url": "https://example.com/"}

        handler._on_token_refresh_response(MockEvent())
        self.assertTrue(future.done())
        self.assertNotIn("https://example.com", handler._pending_auth_requests)
        handler.destroy()

    async def test_on_token_refresh_wildcard(self):
        """Wildcard refresh pops every pending request."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        handler._auth_handle_ints["https://a.com"] = 1
        handler._auth_handle_ints["https://b.com"] = 2
        handler._pending_auth_requests["https://a.com"] = asyncio.Future()
        handler._pending_auth_requests["https://b.com"] = asyncio.Future()

        class MockEvent:
            payload = {"access_token": "tok", "discovery_url": "*"}

        handler._on_token_refresh_response(MockEvent())
        self.assertEqual(len(handler._pending_auth_requests), 0)
        handler.destroy()

    # --- Extension state ---

    async def test_init_attrs_on_startup(self):
        """on_startup sets all expected attributes."""
        from omni.storage_api.auth import get_instance

        instance = get_instance()
        for attr in (
            "_auth_handler",
            "_client_connected_sub",
            "_discovery_removed_sub",
            "_mount_task",
            "_skip_current_url",
            "_current_auth_url",
        ):
            self.assertTrue(hasattr(instance, attr), f"missing attr: {attr}")

    # --- discover_and_register ---

    async def test_discover_and_register_timeout(self):
        """discover_and_register raises TimeoutError when the callback is never invoked."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        with patch("omni.client.register_storage_from_discovery_with_callback", return_value=MagicMock()):
            with self.assertRaises(asyncio.TimeoutError):
                await handler.discover_and_register("https://disc.example.com", timeout=1.0)
        handler.destroy()

    async def test_discover_and_register_success(self):
        """discover_and_register returns the address tuple when the callback reports OK."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        expected = ("https://server1.example.com", "https://server2.example.com")

        def mock_register(url, callback):
            callback(omni.client.Result.OK, expected)
            return MagicMock()

        with patch("omni.client.register_storage_from_discovery_with_callback", side_effect=mock_register):
            addresses = await handler.discover_and_register("https://disc.example.com", timeout=5.0)

        self.assertEqual(addresses, expected)
        handler.destroy()

    async def test_discover_and_register_timeout_cleans_up(self):
        """On timeout, all per-URL state is removed so a retry starts fresh."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        url = "https://cleanup.example.com"
        normalized = handler._normalize_url(url)
        with patch("omni.client.register_storage_from_discovery_with_callback", return_value=MagicMock()):
            with self.assertRaises(asyncio.TimeoutError):
                await handler.discover_and_register(url, timeout=1.0)

        self.assertNotIn(normalized, handler._pending_auth_requests)
        self.assertNotIn(normalized, handler._pending_discovery_futures)
        self.assertNotIn(url, handler._request_handles)
        self.assertNotIn(normalized, handler._registered_discovery_urls)
        handler.destroy()

    # --- Preconfigured URLs ---

    async def test_get_preconfigured_urls(self):
        """get_preconfigured_urls reads the list from settings."""
        from omni.storage_api.auth import StorageAuthHandler

        settings = carb.settings.get_settings()
        settings.set(
            "/exts/omni.storage_api.auth/preconfiguredDiscoveryUrls",
            ["https://pre1.example.com", "https://pre2.example.com"],
        )

        urls = StorageAuthHandler.get_preconfigured_urls()
        self.assertIn("https://pre1.example.com", urls)
        self.assertIn("https://pre2.example.com", urls)

        settings.set("/exts/omni.storage_api.auth/preconfiguredDiscoveryUrls", [])
        self.assertEqual(len(StorageAuthHandler.get_preconfigured_urls()), 0)

    async def test_auto_mount_preconfigured_calls_discover(self):
        """auto_mount_preconfigured calls discover_and_register for each URL."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        settings = carb.settings.get_settings()
        settings.set(
            "/exts/omni.storage_api.auth/preconfiguredDiscoveryUrls",
            ["https://pre1.example.com", "https://pre2.example.com"],
        )

        calls = []

        async def mock_discover(url, timeout=60.0):
            calls.append(url)
            return ("https://server.example.com",)

        with patch.object(handler, "discover_and_register", side_effect=mock_discover):
            results = await handler.auto_mount_preconfigured(timeout_per_url=5.0)

        self.assertEqual(sorted(calls), ["https://pre1.example.com", "https://pre2.example.com"])
        self.assertEqual(len(results), 2)

        settings.set("/exts/omni.storage_api.auth/preconfiguredDiscoveryUrls", [])
        handler.destroy()

    async def test_auto_mount_preconfigured_skips_already_registered(self):
        """URLs already in _request_handles are skipped by auto_mount_preconfigured."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        settings = carb.settings.get_settings()
        settings.set(
            "/exts/omni.storage_api.auth/preconfiguredDiscoveryUrls",
            ["https://already.example.com"],
        )
        handler._request_handles["https://already.example.com"] = MagicMock()

        calls = []

        async def mock_discover(url, timeout=60.0):
            calls.append(url)
            return ()

        with patch.object(handler, "discover_and_register", side_effect=mock_discover):
            results = await handler.auto_mount_preconfigured()

        self.assertEqual(calls, [])
        self.assertEqual(results, {})

        settings.set("/exts/omni.storage_api.auth/preconfiguredDiscoveryUrls", [])
        handler.destroy()

    # --- Re-auth ---

    async def test_reauth_already_registered_creates_timeout(self):
        """Auth callback for an already-registered URL creates a reauth future + timeout task."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        server = "https://registered.example.com"
        normalized = handler._normalize_url(server)
        handler._request_handles[server] = MagicMock()

        result = handler._single_auth_callback(99, server)
        self.assertTrue(result)
        self.assertIn(normalized, handler._pending_auth_requests)
        self.assertIn(normalized, handler._callback_auth_tasks)
        handler.destroy()

    # --- Cancel ---

    async def test_cancel_preconfigured_sets_skip_event(self):
        """_cancel_current_auth sets the skip event for the preconfigured mount loop."""
        from omni.storage_api.auth import get_instance

        instance = get_instance()
        instance._skip_current_url = asyncio.Event()
        instance._cancel_current_auth()
        self.assertTrue(instance._skip_current_url.is_set())
        instance._skip_current_url = None

    async def test_cancel_interactive_cleans_up(self):
        """_cancel_current_auth for interactive flow cleans up auth state and marks entry disconnected."""
        from omni.storage_api.auth import get_instance

        instance = get_instance()
        url = "https://interactive.example.com"
        instance._skip_current_url = None
        instance._current_auth_url = url

        with (
            patch.object(instance._auth_handler, "_cleanup_callback_auth") as mock_cleanup,
            patch.object(instance, "_mark_placeholders_as_disconnected") as mock_mark,
        ):
            instance._cancel_current_auth()

        mock_cleanup.assert_called_once_with(url)
        mock_mark.assert_called_once_with([url])
        self.assertIsNone(instance._current_auth_url)

    # --- Portal-supplied auth timeout ---

    async def test_on_token_refresh_updates_portal_auth_timeout(self):
        """refreshAccessToken.auth_timeout is stored for use by future auth flows."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        self.assertIsNone(handler._portal_auth_timeout)

        class MockEvent:
            payload = {"access_token": "tok", "discovery_url": "*", "auth_timeout": 45}

        handler._on_token_refresh_response(MockEvent())
        self.assertEqual(handler._portal_auth_timeout, 45.0)
        handler.destroy()

    async def test_on_token_refresh_ignores_invalid_auth_timeout(self):
        """Non-numeric or non-positive auth_timeout values are ignored; existing value is preserved."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        handler._portal_auth_timeout = 30.0

        class BadEvent:
            payload = {"access_token": "tok", "discovery_url": "*", "auth_timeout": "nope"}

        class NonPositiveEvent:
            payload = {"access_token": "tok", "discovery_url": "*", "auth_timeout": 0}

        handler._on_token_refresh_response(BadEvent())
        self.assertEqual(handler._portal_auth_timeout, 30.0)

        handler._on_token_refresh_response(NonPositiveEvent())
        self.assertEqual(handler._portal_auth_timeout, 30.0)
        handler.destroy()

    async def test_get_effective_auth_timeout_prefers_portal(self):
        """get_effective_auth_timeout returns portal value if set, else the setting."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        settings = carb.settings.get_settings()
        settings.set("/exts/omni.storage_api.auth/authCallbackTimeout", 60.0)

        self.assertEqual(handler.get_effective_auth_timeout(), 60.0)

        handler._portal_auth_timeout = 50.0
        self.assertEqual(handler.get_effective_auth_timeout(), 50.0)

        handler._portal_auth_timeout = None
        self.assertEqual(handler.get_effective_auth_timeout(), 60.0)
        handler.destroy()

    # --- authenticationError ---

    async def test_on_authentication_error_fails_pending_auth_future(self):
        """authenticationError sets AuthPortalError on the pending auth future and cleans up all state."""
        from omni.storage_api.auth import AuthPortalError, StorageAuthHandler

        handler = StorageAuthHandler()
        url = "https://err.example.com"
        normalized = handler._normalize_url(url)

        handler._auth_handle_ints[url] = 77
        handler._handled_auth_handles.add(77)
        handler._request_handles[url] = MagicMock()
        handler._registered_discovery_urls.add(normalized)
        auth_future: asyncio.Future = asyncio.Future()
        handler._pending_auth_requests[normalized] = auth_future

        class MockEvent:
            payload = {
                "discovery_url": url,
                "error_code": "idp_denied",
                "error_message": "Identity provider rejected the request.",
            }

        with patch("omni.client.set_storage_access_token") as mock_release:
            handler._on_authentication_error(MockEvent())

        self.assertTrue(auth_future.done())
        with self.assertRaises(AuthPortalError) as ctx:
            auth_future.result()
        self.assertEqual(ctx.exception.error_code, "idp_denied")
        self.assertEqual(ctx.exception.error_message, "Identity provider rejected the request.")
        self.assertEqual(ctx.exception.discovery_url, url)
        self.assertNotIn(normalized, handler._pending_auth_requests)
        self.assertNotIn(77, handler._handled_auth_handles)
        self.assertNotIn(url, handler._request_handles)
        self.assertNotIn(normalized, handler._registered_discovery_urls)
        # Empty token is pushed so stuck omni.client readers fail fast and release the rwlock.
        mock_release.assert_called_once_with(77, "")
        handler.destroy()

    async def test_on_authentication_error_fires_on_auth_error_callback(self):
        """on_auth_error callback receives the portal's error details when a request was live."""
        import asyncio

        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        received = []

        handler.on_auth_error = lambda url, code, msg: received.append((url, code, msg))

        # Simulate a live auth attempt by populating the pending request.
        handler._pending_auth_requests["https://err.example.com"] = asyncio.Future()

        class MockEvent:
            payload = {
                "discovery_url": "https://err.example.com",
                "error_code": "user_cancelled",
                "error_message": "User cancelled sign-in.",
            }

        handler._on_authentication_error(MockEvent())
        self.assertEqual(
            received,
            [("https://err.example.com", "user_cancelled", "User cancelled sign-in.")],
        )
        handler.destroy()

    async def test_on_authentication_error_drops_late_response_after_cancel(self):
        """A portal error arriving after local cancel/cleanup does NOT fire on_auth_error."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        received = []
        handler.on_auth_error = lambda url, code, msg: received.append((url, code, msg))

        # No pending/discovery request: simulates the "already cleaned up" state
        # that exists after a user-cancel or timeout-cleanup.
        class MockEvent:
            payload = {
                "discovery_url": "https://err.example.com",
                "error_code": "some_error",
                "error_message": "too late",
            }

        handler._on_authentication_error(MockEvent())
        self.assertEqual(received, [])  # callback must NOT fire
        handler.destroy()

    async def test_on_authentication_error_missing_discovery_url_is_ignored(self):
        """authenticationError without discovery_url does not raise or invoke the callback."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        received = []
        handler.on_auth_error = lambda url, code, msg: received.append((url, code, msg))

        class MockEvent:
            payload = {"error_code": "oops", "error_message": "no url"}

        handler._on_authentication_error(MockEvent())
        self.assertEqual(received, [])
        handler.destroy()

    # --- Errored-servers short-circuit (prevents omni.client 10s auto-retry spam) ---

    async def test_cleanup_callback_auth_marks_url_errored(self):
        """_cleanup_callback_auth adds the URL to _errored_servers so retries short-circuit."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        url = "https://err.example.com"
        normalized = handler._normalize_url(url)

        self.assertNotIn(normalized, handler._errored_servers)
        handler._cleanup_callback_auth(url)
        self.assertIn(normalized, handler._errored_servers)
        handler.destroy()

    async def test_cleanup_failed_discovery_marks_url_errored(self):
        """_cleanup_failed_discovery also populates _errored_servers (covers cancel path)."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        url = "https://cancel.example.com"
        normalized = handler._normalize_url(url)

        handler._cleanup_failed_discovery(normalized, url)
        self.assertIn(normalized, handler._errored_servers)
        handler.destroy()

    async def test_auth_callback_short_circuits_for_errored_url(self):
        """Callback returns True without dispatching to portal when URL is errored."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        server = "https://err.example.com"
        handler._errored_servers.add(handler._normalize_url(server))

        with (
            patch.object(StorageAuthHandler, "_send_new_storage_url_request") as mock_send,
            patch("omni.client.set_storage_access_token") as mock_release,
        ):
            result = handler._single_auth_callback(123, server)

        self.assertTrue(result)
        mock_send.assert_not_called()  # NO portal dispatch
        mock_release.assert_called_once_with(123, "")  # empty-token release to unblock
        self.assertIn(123, handler._handled_auth_handles)
        handler.destroy()

    async def test_discover_and_register_clears_errored_state(self):
        """A fresh discover_and_register drops any prior errored mark so the portal flow can retry."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        url = "https://retry.example.com"
        normalized = handler._normalize_url(url)
        handler._errored_servers.add(normalized)

        with patch("omni.client.register_storage_from_discovery_with_callback", return_value=MagicMock()):
            with self.assertRaises(asyncio.TimeoutError):
                await handler.discover_and_register(url, timeout=1.0)

        # discover_and_register clears the errored mark up front, then the timeout
        # cleanup re-adds it — net effect: mark is present after timeout.
        self.assertIn(normalized, handler._errored_servers)
        handler.destroy()

    async def test_unregister_handler_clears_errored_state(self):
        """unregister_handler clears the errored mark for the URL."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        url = "https://forget.example.com"
        normalized = handler._normalize_url(url)
        handler._errored_servers.add(normalized)

        handler.unregister_handler(url)
        self.assertNotIn(normalized, handler._errored_servers)
        handler.destroy()

    # --- Task cancellation on removal / cleanup ---

    async def test_unregister_handler_cancels_auth_timeout_task(self):
        """Removing a discovery cancels its in-flight auth timeout task so no stale UI fires."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        url = "https://in-flight.example.com"
        normalized = handler._normalize_url(url)

        async def _never():
            await asyncio.sleep(60)

        task = asyncio.ensure_future(_never())
        handler._callback_auth_tasks[normalized] = task
        handler._pending_discovery_futures[normalized] = asyncio.Future()

        handler.unregister_handler(url)

        # Give the event loop a tick to process the cancellation.
        await omni.kit.app.get_app().next_update_async()
        self.assertTrue(task.cancelled() or task.done())
        self.assertNotIn(normalized, handler._pending_discovery_futures)
        handler.destroy()

    async def test_cleanup_callback_auth_cancels_discovery_future(self):
        """_cleanup_callback_auth cancels a pending discovery future so discover_and_register unblocks."""
        from omni.storage_api.auth import StorageAuthHandler

        handler = StorageAuthHandler()
        url = "https://unblock.example.com"
        normalized = handler._normalize_url(url)
        disc_future = asyncio.Future()
        handler._pending_discovery_futures[normalized] = disc_future

        handler._cleanup_callback_auth(url)

        self.assertTrue(disc_future.cancelled())
        self.assertNotIn(normalized, handler._pending_discovery_futures)
        handler.destroy()

    # --- authenticationError (continued) ---

    async def test_on_authentication_error_cancels_pending_discovery(self):
        """authenticationError fails the in-flight discovery future so discover_and_register unblocks."""
        from omni.storage_api.auth import AuthPortalError, StorageAuthHandler

        handler = StorageAuthHandler()
        url = "https://err-disc.example.com"

        with patch("omni.client.register_storage_from_discovery_with_callback", return_value=MagicMock()):
            task = asyncio.ensure_future(handler.discover_and_register(url, timeout=30.0))
            # Let discover_and_register register its futures before we fire the error.
            for _ in range(3):
                await omni.kit.app.get_app().next_update_async()

            class MockEvent:
                payload = {
                    "discovery_url": url,
                    "error_code": "server_error",
                    "error_message": "Portal upstream error.",
                }

            handler._on_authentication_error(MockEvent())

            with self.assertRaises(AuthPortalError):
                await task

        self.assertNotIn(handler._normalize_url(url), handler._pending_auth_requests)
        self.assertNotIn(handler._normalize_url(url), handler._pending_discovery_futures)
        self.assertNotIn(url, handler._request_handles)
        handler.destroy()

    # --- Discovery removed ---

    async def test_on_discovery_removed_releases_auth_state(self):
        """DISCOVERY_SERVER_REMOVED handler clears request handle and auth state for the URL."""
        from omni.storage_api.auth import get_instance

        instance = get_instance()
        url = "https://removed.example.com"
        instance._auth_handler.register_handler(url)
        instance._auth_handler._request_handles[url] = MagicMock()

        class MockEvent:
            payload = {"url": url, "name": "removed"}

        instance._on_discovery_removed(MockEvent())
        self.assertNotIn(url, instance._auth_handler._request_handles)
        self.assertNotIn(instance._auth_handler._normalize_url(url), instance._auth_handler._registered_discovery_urls)
