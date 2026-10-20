## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
"""Lifecycle tests for CreoCameraManipulatorExtension.

These are primarily API-usage tests: they assert we call the exact upstream
functions/methods we rely on (RegisterScene, set_ui_delegate, _find_viewport_layer).
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import omni.kit.test
from omni.kit.manipulator.creo_camera.creo_camera_manipulator import CreoCameraFactory
from omni.kit.manipulator.creo_camera.extension import CreoCameraManipulatorExtension


class _DummyLayer:
    def __init__(self, visible=True):
        self.visible = visible


class _DummyViewportWindow:
    def __init__(self, layer=None):
        self._layer = layer
        self.calls = []

    def _find_viewport_layer(self, name, kind):
        self.calls.append((name, kind))
        return self._layer


class TestCreoCameraExtensionLifecycle(omni.kit.test.AsyncTestCase):
    async def test_startup_registers_scene_with_expected_name_and_factory(self):
        ext = CreoCameraManipulatorExtension()

        scene_handle = Mock()
        with patch("omni.kit.manipulator.creo_camera.extension.RegisterScene", return_value=scene_handle) as reg_scene:
            with patch("omni.kit.manipulator.creo_camera.extension.get_active_viewport_window", return_value=None):
                with patch("omni.kit.viewport.window.events.set_ui_delegate") as set_ui_delegate:
                    ext.on_startup("test_ext_id")

        reg_scene.assert_called_once()
        args, kwargs = reg_scene.call_args
        self.assertEqual(args[0], CreoCameraFactory)
        self.assertEqual(args[1], "omni.kit.manipulator.creo_camera.CreoCamera")
        self.assertEqual(kwargs, {})
        set_ui_delegate.assert_called_once_with(None)

    async def test_startup_hides_default_camera_layer_if_present(self):
        ext = CreoCameraManipulatorExtension()
        cam_layer = _DummyLayer(visible=True)
        vp = _DummyViewportWindow(layer=cam_layer)

        scene_handle = Mock()
        with patch("omni.kit.manipulator.creo_camera.extension.RegisterScene", return_value=scene_handle):
            with patch("omni.kit.manipulator.creo_camera.extension.get_active_viewport_window", return_value=vp):
                with patch("omni.kit.viewport.window.events.set_ui_delegate") as set_ui_delegate:
                    ext.on_startup("test_ext_id")

        set_ui_delegate.assert_called_once_with(None)
        self.assertEqual(vp.calls, [("Camera", "manipulator")])
        self.assertFalse(cam_layer.visible)
        self.assertIs(ext._cam_layer, cam_layer)
        self.assertEqual(ext._default_camera_visible, True)

    async def test_startup_handles_no_active_viewport_window(self):
        ext = CreoCameraManipulatorExtension()
        scene_handle = Mock()

        with patch("omni.kit.manipulator.creo_camera.extension.RegisterScene", return_value=scene_handle):
            with patch("omni.kit.manipulator.creo_camera.extension.get_active_viewport_window", return_value=None):
                with patch("omni.kit.viewport.window.events.set_ui_delegate") as set_ui_delegate:
                    ext.on_startup("test_ext_id")

        set_ui_delegate.assert_called_once_with(None)
        self.assertIsNone(ext._cam_layer)
        self.assertIsNone(ext._default_camera_visible)

    async def test_startup_handles_missing_camera_layer(self):
        ext = CreoCameraManipulatorExtension()
        vp = _DummyViewportWindow(layer=None)
        scene_handle = Mock()

        with patch("omni.kit.manipulator.creo_camera.extension.RegisterScene", return_value=scene_handle):
            with patch("omni.kit.manipulator.creo_camera.extension.get_active_viewport_window", return_value=vp):
                with patch("omni.kit.viewport.window.events.set_ui_delegate"):
                    ext.on_startup("test_ext_id")

        self.assertEqual(vp.calls, [("Camera", "manipulator")])
        self.assertIsNone(ext._cam_layer)
        self.assertIsNone(ext._default_camera_visible)

    async def test_shutdown_restores_default_camera_layer_visibility(self):
        ext = CreoCameraManipulatorExtension()
        cam_layer = _DummyLayer(visible=True)
        vp = _DummyViewportWindow(layer=cam_layer)

        scene_handle = Mock()
        with patch("omni.kit.manipulator.creo_camera.extension.RegisterScene", return_value=scene_handle):
            with patch("omni.kit.manipulator.creo_camera.extension.get_active_viewport_window", return_value=vp):
                with patch("omni.kit.viewport.window.events.set_ui_delegate"):
                    ext.on_startup("test_ext_id")

        # Visibility was forced off by startup
        self.assertFalse(cam_layer.visible)

        # On shutdown it should be restored to original (True)
        ext.on_shutdown()
        self.assertTrue(cam_layer.visible)

    async def test_shutdown_destroys_scene_registration_handle(self):
        ext = CreoCameraManipulatorExtension()
        scene_handle = Mock()

        with patch("omni.kit.manipulator.creo_camera.extension.RegisterScene", return_value=scene_handle):
            with patch("omni.kit.manipulator.creo_camera.extension.get_active_viewport_window", return_value=None):
                with patch("omni.kit.viewport.window.events.set_ui_delegate"):
                    ext.on_startup("test_ext_id")

        ext.on_shutdown()
        scene_handle.destroy.assert_called_once()
        self.assertIsNone(ext._scene_registration)

    async def test_shutdown_without_startup_is_safe(self):
        # This is intentionally strict: shutdown should be robust even if startup failed early.
        ext = CreoCameraManipulatorExtension()
        ext.on_shutdown()
