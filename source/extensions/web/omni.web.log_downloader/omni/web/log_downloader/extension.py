# Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Extension for downloading Kit log files via web messaging interface."""

import asyncio
import base64
import os
import uuid
import warnings

import carb
import carb.eventdispatcher
import carb.settings
import omni.ext
import omni.kit.app
import omni.kit.livestream.messaging as messaging

from .log_download import read_log_file

# Files larger than this will be rejected before any bytes are read.
# Override by changing the constant at import time or by subclassing.
LOG_DOWNLOAD_MAX_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


class LogDownloaderExtension(omni.ext.IExt):
    """Extension that provides log file download functionality via web messaging.

    Incoming ``request_log_download`` events trigger a file read.  The response
    (or error) is dispatched as a single ``log_download_response`` /
    ``log_download_error`` event via ``omni.kit.app.queue_event``.

    ``omni.kit.livestream.messaging`` intercepts those outbound events and
    automatically splits large payloads into wire-safe parts before forwarding
    them to the client, which reassembles them transparently.
    """

    def on_startup(self, ext_id: str):
        """Initialize the log downloader extension."""
        carb.log_info("[omni.web.log_downloader] Extension starting up")

        # Register outbound event names so the messaging extension routes them
        # to the client and handles splitting for large payloads automatically.
        messaging.register_event_type_to_send("log_download_response")
        messaging.register_event_type_to_send("log_download_error")

        # Deprecated v1 events — kept for backward compatibility, removed in v3.0.0.
        messaging.register_event_type_to_send("log_download_start")
        messaging.register_event_type_to_send("log_download_chunk")
        messaging.register_event_type_to_send("log_download_complete")

        self._dispatcher = carb.eventdispatcher.get_eventdispatcher()
        self._subscription = self._dispatcher.observe_event(
            observer_name="omni.web.log_downloader.LogDownloaderExtension",
            event_name="request_log_download",
            on_event=self._handle_log_download_request,
        )

        carb.log_info("[omni.web.log_downloader] Extension started - listening for log download requests")

    def _handle_log_download_request(self, event: carb.eventdispatcher.Event):
        """Handle an incoming log download request event."""
        carb.log_info("[omni.web.log_downloader] Received log download request")

        payload = {}
        if event.payload:
            for key in event.payload.keys():
                payload[str(key)] = event.payload[key]

        log_path = payload.get("log_path", None)
        asyncio.ensure_future(self._download_log(log_path))

    async def _download_log(self, log_path: str = None):
        """Read the log file and dispatch the payload via the messaging extension.

        Args:
            log_path: Path to the log file. Falls back to the ``/log/file`` carb
                setting when not provided.
        """
        # Generate transfer_id once for this request so both the new
        # log_download_error payload and the deprecated chunked events all share
        # the same ID — matching the original v1 behaviour.
        transfer_id = str(uuid.uuid4())

        try:
            # Resolve the path early so we can stat it before reading.
            resolved_path = log_path or carb.settings.get_settings().get_as_string("/log/file")
            if not resolved_path:
                omni.kit.app.queue_event(
                    "log_download_error",
                    {"transfer_id": transfer_id, "error": "No log file path specified"},
                )
                return

            # Stat the file off the event loop to avoid blocking.
            try:
                size = await asyncio.to_thread(os.path.getsize, resolved_path)
            except OSError:
                omni.kit.app.queue_event(
                    "log_download_error",
                    {"transfer_id": transfer_id, "error": f"Log file not found: {resolved_path}"},
                )
                return

            if size > LOG_DOWNLOAD_MAX_SIZE_BYTES:
                carb.log_error(
                    f"[omni.web.log_downloader] Log file too large: {size} bytes "
                    f"(max {LOG_DOWNLOAD_MAX_SIZE_BYTES})"
                )
                omni.kit.app.queue_event(
                    "log_download_error",
                    {
                        "transfer_id": transfer_id,
                        "error": "Log file too large",
                        "size": size,
                        "max": LOG_DOWNLOAD_MAX_SIZE_BYTES,
                    },
                )
                return

            # File read is performed off the event loop inside read_log_file.
            result = await read_log_file(resolved_path)

            if result:
                carb.log_info(
                    f"[omni.web.log_downloader] Dispatching log_download_response "
                    f"({result['size']} bytes, file: {result['filename']})"
                )
                # queue_event is intercepted by omni.kit.livestream.messaging which
                # splits large payloads into parts before sending them to the client.
                omni.kit.app.queue_event("log_download_response", result)
                await self._dispatch_deprecated_chunked_events(result, transfer_id)
            else:
                carb.log_error("[omni.web.log_downloader] Log download failed")
                omni.kit.app.queue_event(
                    "log_download_error",
                    {"transfer_id": transfer_id, "error": "Failed to read log file"},
                )

        except Exception as e:
            carb.log_error(f"[omni.web.log_downloader] Error during log download: {e}")
            import traceback

            carb.log_error(traceback.format_exc())
            omni.kit.app.queue_event("log_download_error", {"transfer_id": transfer_id, "error": str(e)})

    def on_shutdown(self):
        """Clean up the extension on shutdown."""
        carb.log_info("[omni.web.log_downloader] Extension shutting down")

        if hasattr(self, "_subscription") and self._subscription:
            # carb.eventdispatcher.ObserverGuard has reset(), not unsubscribe().
            self._subscription.reset()
            self._subscription = None

        messaging.unregister_event_type_to_send("log_download_response")
        messaging.unregister_event_type_to_send("log_download_error")

        # Deprecated v1 events.
        messaging.unregister_event_type_to_send("log_download_start")
        messaging.unregister_event_type_to_send("log_download_chunk")
        messaging.unregister_event_type_to_send("log_download_complete")

        carb.log_info("[omni.web.log_downloader] Extension shutdown complete")

    # -------------------------------------------------------------------------
    # Deprecated API — will be removed in v3.0.0
    # -------------------------------------------------------------------------

    _DEPRECATED_CHUNK_SIZE = 40_000  # 40 KB — matches the original v1 protocol

    async def _dispatch_deprecated_chunked_events(self, result: dict, transfer_id: str):
        """Dispatch the v1 chunked transfer events alongside the new single-payload response.

        .. deprecated::
            ``log_download_start``, ``log_download_chunk``, and
            ``log_download_complete`` are deprecated and will be removed in
            v3.0.0.  Migrate to ``log_download_response`` instead.

        These events are emitted after ``log_download_response`` so that
        existing consumers have time to migrate without breaking.  The same
        ``transfer_id`` that appears in ``log_download_error`` payloads is
        reused here, matching the original v1 behaviour.
        """
        warnings.warn(
            "log_download_start / log_download_chunk / log_download_complete are deprecated "
            "and will be removed in v3.0.0. Migrate to log_download_response.",
            DeprecationWarning,
            stacklevel=2,
        )
        carb.log_warn(
            "[omni.web.log_downloader] DEPRECATED: log_download_start / "
            "log_download_chunk / log_download_complete are deprecated and will "
            "be removed in v3.0.0. Migrate to log_download_response."
        )

        content_bytes = base64.b64decode(result["content"])
        total_size = result["size"]
        filename = result["filename"]
        chunk_size = self._DEPRECATED_CHUNK_SIZE
        # Ceiling division — matches the original exactly; gives 0 for empty
        # files, which means no chunk events are sent (also matches original).
        total_chunks = (total_size + chunk_size - 1) // chunk_size

        self._dispatcher.dispatch_event(
            "log_download_start",
            payload={
                "transfer_id": transfer_id,
                "total_size": total_size,
                "total_chunks": total_chunks,
                "filename": filename,
            },
        )

        for i in range(total_chunks):
            chunk = content_bytes[i * chunk_size : (i + 1) * chunk_size]
            self._dispatcher.dispatch_event(
                "log_download_chunk",
                payload={
                    "transfer_id": transfer_id,
                    "chunk_index": i,
                    "data": base64.b64encode(chunk).decode("utf-8"),
                },
            )
            # Yield to the event loop every 10 chunks to avoid starving other tasks.
            if i % 10 == 9:
                await omni.kit.app.get_app().next_update_async()

        self._dispatcher.dispatch_event(
            "log_download_complete",
            payload={"transfer_id": transfer_id, "success": True},
        )
