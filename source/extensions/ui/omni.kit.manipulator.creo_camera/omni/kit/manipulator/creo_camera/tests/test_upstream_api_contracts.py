## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
"""Upstream API contract tests.

Goal: fail loudly if any upstream API this extension relies on is renamed,
removed, or changes in a way that breaks our usage.
"""

from __future__ import annotations

import importlib
import uuid

import omni.kit.test


def _sanitize(name: str) -> str:
    return name.replace(".", "_").replace("-", "_")


def _resolve_attr(module_name: str, *attrs: str):
    mod = importlib.import_module(module_name)
    obj = mod
    for a in attrs:
        obj = getattr(obj, a)
    return obj


_UPSTREAM_ATTR_PATHS = [
    # Core Kit extension interface
    ("omni.ext", "IExt"),
    # Viewport registry + utilities
    ("omni.kit.viewport.registry", "RegisterScene"),
    ("omni.kit.viewport.utility", "get_active_viewport_window"),
    ("omni.kit.viewport.window.events", "set_ui_delegate"),
    # Camera manipulator base APIs we subclass/use
    ("omni.kit.manipulator.camera", "ViewportCameraManipulator"),
    ("omni.kit.manipulator.camera", "CameraGestureBase"),
    ("omni.kit.manipulator.camera.model", "_flatten_matrix"),
    # Viewport API used for raycasts
    ("omni.kit.widget.viewport.api", "ViewportAPI"),
    # OmniUI scene primitives we build with
    ("omni.ui.scene", "GestureManager"),
    ("omni.ui.scene", "GestureState"),
    ("omni.ui.scene", "ScrollGesture"),
    ("omni.ui.scene", "Screen"),
    ("omni.ui.scene", "Transform"),
    ("omni.ui.scene", "Manipulator"),
    ("omni.ui.scene", "AbstractManipulatorModel"),
    ("omni.ui.scene", "AbstractManipulatorItem"),
    ("omni.ui.scene", "Matrix44"),
    ("omni.ui.scene", "Line"),
    ("omni.ui.scene", "Rectangle"),
    ("omni.ui.scene", "Space"),
    # carb input flags used for gesture bindings
    ("carb.input", "KEYBOARD_MODIFIER_FLAG_SHIFT"),
    ("carb.input", "KEYBOARD_MODIFIER_FLAG_CONTROL"),
    # USD math
    ("pxr", "Gf"),
]


class TestCreoCameraUpstreamApiContracts(omni.kit.test.AsyncTestCase):
    async def test_gesture_state_expected_members_exist(self):
        gesture_state = _resolve_attr("omni.ui.scene", "GestureState")
        for name in ("CHANGED", "ENDED", "CANCELED"):
            self.assertTrue(hasattr(gesture_state, name), f"GestureState.{name} is required")

    async def test_space_expected_members_exist(self):
        space = _resolve_attr("omni.ui.scene", "Space")
        for name in ("NDC", "WORLD", "SCREEN"):
            self.assertTrue(hasattr(space, name), f"Space.{name} is required")

    async def test_transform_lookat_camera_exists(self):
        transform = _resolve_attr("omni.ui.scene", "Transform")
        self.assertTrue(hasattr(transform, "LookAt"))
        self.assertTrue(hasattr(transform.LookAt, "CAMERA"))

    async def test_viewport_api_raycast_methods_exist(self):
        viewport_api = _resolve_attr("omni.kit.widget.viewport.api", "ViewportAPI")
        for name in ("map_ndc_to_texture_pixel", "request_query"):
            self.assertTrue(hasattr(viewport_api, name), f"ViewportAPI.{name} is required")
        # We also read projection to switch gesture families in CreoGestureManager
        self.assertTrue(hasattr(viewport_api, "projection"), "ViewportAPI.projection is required")

    async def test_viewport_camera_manipulator_has_on_began_hook(self):
        vcm = _resolve_attr("omni.kit.manipulator.camera", "ViewportCameraManipulator")
        self.assertTrue(hasattr(vcm, "_on_began"), "ViewportCameraManipulator._on_began is required (used by scroll)")

    async def test_flatten_matrix_accepts_gf_matrix4d_and_returns_16_floats(self):
        flatten = _resolve_attr("omni.kit.manipulator.camera.model", "_flatten_matrix")
        gf = _resolve_attr("pxr", "Gf")
        m = gf.Matrix4d(1.0)
        out = flatten(m)
        self.assertIsInstance(out, (list, tuple))
        self.assertGreaterEqual(len(out), 16)

    async def test_register_scene_is_callable_with_factory_and_name_and_returns_destroyable_handle(self):
        register_scene = _resolve_attr("omni.kit.viewport.registry", "RegisterScene")

        def dummy_factory(_desc):
            return None

        name = f"omni.kit.manipulator.creo_camera.test.{uuid.uuid4().hex}"
        handle = register_scene(dummy_factory, name)
        self.assertIsNotNone(handle)
        self.assertTrue(hasattr(handle, "destroy"), "RegisterScene(...) must return an object with .destroy()")
        # Clean up registration (no-op if not fully created)
        handle.destroy()


def _make_attr_exists_test(module_name: str, attr_name: str):
    async def _test(self):
        obj = _resolve_attr(module_name, attr_name)
        self.assertIsNotNone(obj)

    _test.__name__ = f"test_attr_exists_{_sanitize(module_name)}__{_sanitize(attr_name)}"
    return _test


for _mod, _attr in _UPSTREAM_ATTR_PATHS:
    setattr(
        TestCreoCameraUpstreamApiContracts,
        f"test_attr_exists_{_sanitize(_mod)}__{_sanitize(_attr)}",
        _make_attr_exists_test(_mod, _attr),
    )
