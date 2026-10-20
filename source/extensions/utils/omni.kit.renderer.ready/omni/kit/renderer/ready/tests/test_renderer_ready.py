# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

import carb
import carb.settings
import omni.kit.test


class TestRendererReadyExtension(omni.kit.test.AsyncTestCase):
    """Tests for omni.kit.renderer.ready extension."""

    async def setUp(self):
        from omni.kit.renderer.ready.extension import RendererReadyExtension

        self._ext_class = RendererReadyExtension

    async def test_extension_loads(self):
        """Extension should be importable and class available."""
        self.assertIsNotNone(self._ext_class)

    async def test_fires_only_once(self):
        """_on_new_frame should only emit once even if called multiple times."""
        ext = self._ext_class()
        ext._fired = False
        ext._subscription = "dummy"

        emit_calls = 0

        def fake_emit():
            nonlocal emit_calls
            emit_calls += 1

        ext._emit_ready = fake_emit

        class FakeEvent:
            pass

        ext._on_new_frame(FakeEvent())
        self.assertTrue(ext._fired)
        self.assertIsNone(ext._subscription)
        self.assertEqual(emit_calls, 1)

        ext._on_new_frame(FakeEvent())
        self.assertEqual(emit_calls, 1)

    async def test_message_setting(self):
        """_emit_ready should pass the configured message through to carb.log_info."""
        settings = carb.settings.get_settings()
        original_message = settings.get("exts/omni.kit.renderer.ready/message")
        original_stdout = settings.get("exts/omni.kit.renderer.ready/stdout")
        original_log_info = carb.log_info

        captured = []

        def fake_log_info(msg):
            captured.append(msg)

        try:
            settings.set("exts/omni.kit.renderer.ready/message", "Test Ready")
            # Disable the stdout side so carb's stdout->log interceptor doesn't
            # double-count the payload through carb.log_info.
            settings.set("exts/omni.kit.renderer.ready/stdout", False)
            carb.log_info = fake_log_info

            ext = self._ext_class()
            ext._fired = False
            ext._emit_ready()

            self.assertEqual(len(captured), 1, captured)
            self.assertTrue(captured[0].endswith("Test Ready"), captured[0])
        finally:
            carb.log_info = original_log_info
            if original_message is not None:
                settings.set("exts/omni.kit.renderer.ready/message", original_message)
            else:
                settings.set("exts/omni.kit.renderer.ready/message", "RTX ready")
            settings.set("exts/omni.kit.renderer.ready/stdout", bool(original_stdout))

    async def test_autostart_disabled(self):
        """Extension should not subscribe when autostart is false."""
        settings = carb.settings.get_settings()
        original = settings.get("exts/omni.kit.renderer.ready/autostart")

        try:
            settings.set("exts/omni.kit.renderer.ready/autostart", False)

            ext = self._ext_class()
            ext.on_startup("omni.kit.renderer.ready-1.0.0")

            self.assertIsNone(ext._subscription)
            self.assertFalse(ext._fired)
        finally:
            settings.set("exts/omni.kit.renderer.ready/autostart", original if original is not None else True)
