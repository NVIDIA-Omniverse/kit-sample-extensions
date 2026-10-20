## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
"""Import/smoke tests for omni.kit.manipulator.creo_camera.

These tests are intentionally numerous: import failures are the fastest signal
that a relied-upon upstream API changed (moved/renamed/removed).
"""

from __future__ import annotations

import importlib

import omni.kit.test


def _sanitize(name: str) -> str:
    return name.replace(".", "_").replace("-", "_")


_MODULES = [
    # Package + entrypoints
    "omni.kit.manipulator.creo_camera",
    "omni.kit.manipulator.creo_camera.extension",
    # Core manipulator
    "omni.kit.manipulator.creo_camera.creo_camera_manipulator",
    "omni.kit.manipulator.creo_camera.creo_gesture_manager",
    "omni.kit.manipulator.creo_camera.creo_gesture_base",
    # Gestures (perspective)
    "omni.kit.manipulator.creo_camera.creo_pan_gesture",
    "omni.kit.manipulator.creo_camera.creo_rotate_gesture",
    "omni.kit.manipulator.creo_camera.creo_zoom_gesture",
    "omni.kit.manipulator.creo_camera.creo_scroll_zoom_gesture",
    # Gestures (orthographic)
    "omni.kit.manipulator.creo_camera.creo_ortho_pan_gesture",
    "omni.kit.manipulator.creo_camera.creo_ortho_zoom_gesture",
    "omni.kit.manipulator.creo_camera.creo_ortho_scroll_zoom_gesture",
    # Math/helpers
    "omni.kit.manipulator.creo_camera.creo_zoom_math",
    # Visualizers
    "omni.kit.manipulator.creo_camera.creo_visualizer_base",
    "omni.kit.manipulator.creo_camera.creo_pan_visualizer",
    "omni.kit.manipulator.creo_camera.creo_rotate_visualizer",
    "omni.kit.manipulator.creo_camera.creo_zoom_visualizer",
    "omni.kit.manipulator.creo_camera.creo_ortho_visualizer",
]


class TestCreoCameraImports(omni.kit.test.AsyncTestCase):
    async def test_public_package_exports_expected_entrypoints(self):
        pkg = importlib.import_module("omni.kit.manipulator.creo_camera")
        self.assertTrue(hasattr(pkg, "CreoCameraManipulatorExtension"))
        self.assertTrue(hasattr(pkg, "CreoCameraFactory"))


def _make_import_test(module_name: str):
    async def _test(self):
        mod = importlib.import_module(module_name)
        self.assertIsNotNone(mod)

    _test.__name__ = f"test_import_{_sanitize(module_name)}"
    return _test


for _m in _MODULES:
    setattr(TestCreoCameraImports, f"test_import_{_sanitize(_m)}", _make_import_test(_m))
