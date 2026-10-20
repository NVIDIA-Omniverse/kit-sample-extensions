# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this software, related
# documentation and any modifications thereto.  Any use, reproduction,
# disclosure or distribution of this software and related documentation
# without an express license agreement from NVIDIA CORPORATION is strictly
# prohibited.

"""
Lightweight extension that emits an "RTX ready" log message when the
first rendered frame is delivered to a viewport.

This is a headless alternative to omni.kit.viewport.ready — it provides
the log/stdout message without any viewport overlay UI, progress bar,
or omni.ui dependency.

Designed for cloud-streaming deployments (Cadence, PTC-Windchill, etc.)
where operators need to distinguish "stream broken" from "scene still loading"
by scraping logs for "RTX ready".

See: NVBUG-5556778, OMPE-66270
"""

import sys

import carb
import carb.eventdispatcher
import carb.settings
import omni.ext
import omni.kit.app
import omni.usd


class RendererReadyExtension(omni.ext.IExt):
    """Extension that logs 'RTX ready' on first rendered frame delivery."""

    def on_startup(self, ext_id: str):
        self._subscription = None
        self._fired = False

        settings = carb.settings.get_settings()
        if not settings.get("exts/omni.kit.renderer.ready/autostart"):
            return

        self._start_watching(settings)

    def on_shutdown(self):
        self._subscription = None

    def _start_watching(self, settings: carb.settings.ISettings):
        """Subscribe to the NEW_FRAME stage rendering event."""
        usd_context_name = settings.get("exts/omni.kit.renderer.ready/usd_context_name") or ""
        usd_context = omni.usd.get_context(usd_context_name)

        if usd_context is None:
            carb.log_warn(
                f"[omni.kit.renderer.ready] No UsdContext found with name "
                f"'{usd_context_name}'. Will not watch for renderer readiness."
            )
            return

        event_name = usd_context.stage_rendering_event_name(omni.usd.StageRenderingEventType.NEW_FRAME)

        self._subscription = carb.eventdispatcher.get_eventdispatcher().observe_event(
            event_name=event_name,
            on_event=self._on_new_frame,
            observer_name="omni.kit.renderer.ready.RendererReadyExtension",
        )

    def _on_new_frame(self, e: carb.eventdispatcher.Event):
        """Called when the first rendered frame is delivered."""
        # Atomically check and clear subscription to prevent potential race condition.
        self._subscription = None
        if self._fired:
            return
        self._fired = True

        self._emit_ready()

    def _emit_ready(self):
        """Log the 'RTX ready' message with elapsed time since app start."""
        settings = carb.settings.get_settings()
        message = settings.get("exts/omni.kit.renderer.ready/message") or "RTX ready"
        use_stdout = settings.get("exts/omni.kit.renderer.ready/stdout")

        try:
            seconds = omni.kit.app.get_app().get_time_since_start_s()
            full_message = f"[{seconds:.3f}s] {message}"
        except Exception:
            full_message = message

        carb.log_info(full_message)

        if use_stdout:
            sys.stdout.write(full_message + "\n")
            sys.stdout.flush()
