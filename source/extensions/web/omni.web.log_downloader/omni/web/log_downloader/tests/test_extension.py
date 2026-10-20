## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""Integration tests for LogDownloaderExtension."""

import base64
import os
import tempfile

import carb
import carb.eventdispatcher
import carb.settings
import omni.kit.app
import omni.kit.test


class TestLogDownloaderExtension(omni.kit.test.AsyncTestCase):
    """Integration tests for LogDownloaderExtension.

    These tests verify the full request→response flow:
      1. Dispatch ``request_log_download`` into carb's event system.
      2. The extension reads the file and queues a ``log_download_response``
         (or ``log_download_error``) via omni.kit.app.queue_event.
      3. omni.kit.livestream.messaging intercepts the queued event and would
         split it for the WebRTC client; our test subscriber receives the same
         event locally via carb.eventdispatcher before it leaves Kit.
    """

    async def setUp(self):
        self.received_events = {}
        self.temp_files = []
        self.subscriptions = []
        self.settings = carb.settings.get_settings()
        self.dispatcher = carb.eventdispatcher.get_eventdispatcher()
        self._subscribe_to_events()

    async def tearDown(self):
        self.subscriptions.clear()
        self.received_events.clear()
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                carb.log_warn(f"Failed to clean up temp file {temp_file}: {e}")
        self.temp_files.clear()
        await omni.kit.app.get_app().next_update_async()

    def _subscribe_to_events(self):
        """Subscribe to all outbound events — new API and deprecated v1 events."""

        def make_handler(event_name):
            def handler(event: carb.eventdispatcher.Event):
                payload = {}
                if event.payload:
                    for key in event.payload.keys():
                        payload[str(key)] = event.payload[key]
                self.received_events.setdefault(event_name, []).append(payload)

            return handler

        for event_name in [
            "log_download_response",
            "log_download_error",
            "log_download_start",
            "log_download_chunk",
            "log_download_complete",
        ]:
            sub = self.dispatcher.observe_event(
                observer_name=f"test.{event_name}",
                event_name=event_name,
                on_event=make_handler(event_name),
            )
            self.subscriptions.append(sub)

    def _create_temp_log_file(self, content: bytes) -> str:
        fd, path = tempfile.mkstemp(suffix=".log", prefix="test_kit_")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
        except Exception:
            os.close(fd)
            raise
        self.temp_files.append(path)
        return path

    async def _wait_for_event(self, event_name: str, frames: int = 4):
        """Pump the app loop until the named event arrives or we exhaust the frame budget."""
        app = omni.kit.app.get_app()
        for _ in range(frames):
            await app.next_update_async()
            if event_name in self.received_events:
                return

    async def test_response_event_fired_for_valid_file(self):
        """A valid request dispatches log_download_response, not log_download_error."""
        test_content = b"Test log content\nLine 2\n"
        log_path = self._create_temp_log_file(test_content)

        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path})
        await self._wait_for_event("log_download_response")

        self.assertIn("log_download_response", self.received_events)
        self.assertNotIn("log_download_error", self.received_events)

    async def test_response_payload_has_expected_fields(self):
        """Response payload contains filename, content, and size."""
        test_content = b"Hello log\n"
        log_path = self._create_temp_log_file(test_content)

        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path})
        await self._wait_for_event("log_download_response")

        payload = self.received_events["log_download_response"][0]
        self.assertIn("filename", payload)
        self.assertIn("content", payload)
        self.assertIn("size", payload)

    async def test_content_decodes_to_original_bytes(self):
        """Base64 content in the response decodes to the original file bytes."""
        test_content = b"Original log bytes\n" * 10
        log_path = self._create_temp_log_file(test_content)

        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path})
        await self._wait_for_event("log_download_response")

        payload = self.received_events["log_download_response"][0]
        self.assertEqual(base64.b64decode(payload["content"]), test_content)

    async def test_size_matches_file_byte_count(self):
        """size field in response equals the raw byte count of the file."""
        test_content = b"A" * 5000
        log_path = self._create_temp_log_file(test_content)

        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path})
        await self._wait_for_event("log_download_response")

        payload = self.received_events["log_download_response"][0]
        self.assertEqual(payload["size"], len(test_content))

    async def test_filename_matches_basename(self):
        """filename field in response equals the basename of the requested log path."""
        test_content = b"Test\n"
        log_path = self._create_temp_log_file(test_content)

        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path})
        await self._wait_for_event("log_download_response")

        payload = self.received_events["log_download_response"][0]
        self.assertEqual(payload["filename"], os.path.basename(log_path))

    async def test_error_event_fired_for_nonexistent_file(self):
        """A missing file path dispatches log_download_error, not log_download_response."""
        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": "/nonexistent/path/to/log.txt"})
        await self._wait_for_event("log_download_error")

        self.assertIn("log_download_error", self.received_events)
        self.assertNotIn("log_download_response", self.received_events)
        self.assertIn("error", self.received_events["log_download_error"][0])

    async def test_uses_settings_path_when_no_log_path_given(self):
        """When payload contains no log_path, the /log/file setting is used."""
        test_content = b"Log from settings\n"
        log_path = self._create_temp_log_file(test_content)
        original = self.settings.get_as_string("/log/file")
        self.settings.set_string("/log/file", log_path)
        try:
            self.dispatcher.dispatch_event("request_log_download", payload={})
            await self._wait_for_event("log_download_response")
            self.assertIn("log_download_response", self.received_events)
        finally:
            if original:
                self.settings.set_string("/log/file", original)

    async def test_large_file_fires_single_response_event(self):
        """A 200 KB file still produces exactly one log_download_response event from Kit.
        omni.kit.livestream.messaging handles splitting for the WebRTC transport layer."""
        test_content = b"X" * 200_000  # 200 KB — above the 64 KiB messaging threshold
        log_path = self._create_temp_log_file(test_content)

        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path})
        await self._wait_for_event("log_download_response")

        events = self.received_events.get("log_download_response", [])
        self.assertEqual(len(events), 1)
        payload = events[0]
        self.assertEqual(payload["size"], len(test_content))
        self.assertEqual(base64.b64decode(payload["content"]), test_content)

    async def test_error_payload_includes_transfer_id(self):
        """log_download_error payload always includes transfer_id for legacy consumer compat."""
        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": "/nonexistent/path/to/log.txt"})
        await self._wait_for_event("log_download_error")

        payload = self.received_events["log_download_error"][0]
        self.assertIn("transfer_id", payload)
        self.assertTrue(len(payload["transfer_id"]) > 0)

    async def test_file_too_large_fires_error_with_size_fields(self):
        """Files exceeding LOG_DOWNLOAD_MAX_SIZE_BYTES fire log_download_error with size and max."""
        import omni.web.log_downloader.extension as ext_module

        original_limit = ext_module.LOG_DOWNLOAD_MAX_SIZE_BYTES
        ext_module.LOG_DOWNLOAD_MAX_SIZE_BYTES = 10  # 10 bytes — any real file will exceed this
        try:
            log_path = self._create_temp_log_file(b"This content is definitely over 10 bytes")
            self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path})
            await self._wait_for_event("log_download_error")

            self.assertIn("log_download_error", self.received_events)
            self.assertNotIn("log_download_response", self.received_events)
            payload = self.received_events["log_download_error"][0]
            self.assertEqual(payload["error"], "Log file too large")
            self.assertIn("size", payload)
            self.assertIn("max", payload)
            self.assertIn("transfer_id", payload)
            self.assertEqual(payload["max"], 10)
        finally:
            ext_module.LOG_DOWNLOAD_MAX_SIZE_BYTES = original_limit

    # -------------------------------------------------------------------------
    # Deprecated v1 API tests
    # TODO: Remove this entire section when log_download_start / log_download_chunk /
    #       log_download_complete are removed in v3.0.0.
    # -------------------------------------------------------------------------

    async def _wait_for_deprecated_complete(self, frames: int = 10):
        """Wait for log_download_complete, allowing extra frames for chunk dispatch."""
        app = omni.kit.app.get_app()
        for _ in range(frames):
            await app.next_update_async()
            if "log_download_complete" in self.received_events:
                return

    async def test_deprecated_events_fired_for_valid_file(self):
        """A valid request fires all three deprecated v1 events alongside log_download_response."""
        log_path = self._create_temp_log_file(b"hello deprecated\n")
        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path})
        await self._wait_for_deprecated_complete()

        self.assertIn("log_download_start", self.received_events)
        self.assertIn("log_download_chunk", self.received_events)
        self.assertIn("log_download_complete", self.received_events)

    async def test_deprecated_start_payload_has_expected_fields(self):
        """log_download_start payload contains transfer_id, total_size, total_chunks, filename."""
        test_content = b"A" * 1000
        log_path = self._create_temp_log_file(test_content)
        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path})
        await self._wait_for_deprecated_complete()

        payload = self.received_events["log_download_start"][0]
        self.assertIn("transfer_id", payload)
        self.assertIn("total_size", payload)
        self.assertIn("total_chunks", payload)
        self.assertIn("filename", payload)
        self.assertEqual(payload["total_size"], len(test_content))
        self.assertEqual(payload["filename"], os.path.basename(log_path))

    async def test_deprecated_chunks_reassemble_to_original_content(self):
        """Reassembling all log_download_chunk data fields reproduces the original file bytes."""
        test_content = b"B" * 90_000  # 90 KB — spans three 40 KB chunks
        log_path = self._create_temp_log_file(test_content)
        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path})
        await self._wait_for_deprecated_complete()

        chunks = sorted(self.received_events["log_download_chunk"], key=lambda p: p["chunk_index"])
        reassembled = b"".join(base64.b64decode(c["data"]) for c in chunks)
        self.assertEqual(reassembled, test_content)

    async def test_deprecated_chunk_count_matches_start_total(self):
        """Number of log_download_chunk events equals total_chunks declared in log_download_start."""
        test_content = b"C" * 90_000  # 90 KB — spans three 40 KB chunks
        log_path = self._create_temp_log_file(test_content)
        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path})
        await self._wait_for_deprecated_complete()

        total_chunks = self.received_events["log_download_start"][0]["total_chunks"]
        self.assertEqual(len(self.received_events["log_download_chunk"]), total_chunks)

    async def test_deprecated_events_share_transfer_id(self):
        """log_download_start, log_download_chunk, and log_download_complete all carry the same transfer_id."""
        log_path = self._create_temp_log_file(b"transfer id test\n")
        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path})
        await self._wait_for_deprecated_complete()

        tid = self.received_events["log_download_start"][0]["transfer_id"]
        self.assertTrue(len(tid) > 0)
        for chunk in self.received_events["log_download_chunk"]:
            self.assertEqual(chunk["transfer_id"], tid)
        self.assertEqual(self.received_events["log_download_complete"][0]["transfer_id"], tid)

    async def test_deprecated_empty_file_sends_no_chunk_events(self):
        """An empty file produces log_download_start (total_chunks=0) and log_download_complete but no chunks."""
        log_path = self._create_temp_log_file(b"")
        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path})
        await self._wait_for_deprecated_complete()

        self.assertIn("log_download_start", self.received_events)
        self.assertEqual(self.received_events["log_download_start"][0]["total_chunks"], 0)
        self.assertNotIn("log_download_chunk", self.received_events)
        self.assertIn("log_download_complete", self.received_events)

    async def test_deprecated_multiple_requests_have_different_transfer_ids(self):
        """Two sequential requests produce distinct transfer_ids."""
        content1 = b"First log file\n"
        content2 = b"Second log file\n"
        log_path1 = self._create_temp_log_file(content1)
        log_path2 = self._create_temp_log_file(content2)

        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path1})
        await self._wait_for_deprecated_complete()
        transfer_id1 = self.received_events["log_download_start"][0]["transfer_id"]

        self.received_events.clear()

        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path2})
        await self._wait_for_deprecated_complete()
        transfer_id2 = self.received_events["log_download_start"][0]["transfer_id"]

        self.assertNotEqual(transfer_id1, transfer_id2)

    async def test_deprecated_chunk_indices_are_sequential(self):
        """Chunk events are dispatched in order with sequential chunk_index values [0, 1, 2, ...]."""
        test_content = b"X" * 100_000  # 100 KB — spans three 40 KB chunks
        log_path = self._create_temp_log_file(test_content)

        self.dispatcher.dispatch_event("request_log_download", payload={"log_path": log_path})
        await self._wait_for_deprecated_complete()

        chunk_indices = [c["chunk_index"] for c in self.received_events["log_download_chunk"]]
        self.assertEqual(chunk_indices, list(range(len(chunk_indices))))
