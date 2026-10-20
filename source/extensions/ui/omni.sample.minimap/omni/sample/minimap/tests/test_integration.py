# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Integration tests for cross-component interactions (generator <-> window <-> extension)."""

from unittest.mock import MagicMock, Mock, patch

import omni.kit.test
from omni.sample.minimap.generator import MinimapGenerator, MinimapGeneratorEventTypes
from omni.sample.minimap.settings import S_PATH
from omni.sample.minimap.window import WindowEventTypes
from pxr import Gf


class _FakeEventStream:
    """Event stream that invokes subscribers when dispatch(type) is called."""

    def __init__(self):
        self._subs = []

    def create_subscription_to_pop(self, callback, name=None):
        self._subs.append(callback)
        return len(self._subs) - 1

    def dispatch(self, event_type):
        class Evt:
            type = int(event_type)

        for cb in self._subs:
            cb(Evt())


class TestMinimapIntegration(omni.kit.test.AsyncTestCase):
    """Integration tests demonstrating how minimap components interact."""

    def _create_generator(self, settings_dict=None):
        """Create a MinimapGenerator with mocked dependencies."""
        gen = MinimapGenerator.__new__(MinimapGenerator)
        gen._app = MagicMock()
        gen._window = MagicMock()
        gen._settings = MagicMock()
        gen._usd_context = MagicMock()
        gen._stage = None
        gen._map_tile_groups = []
        gen._map_tiles_up_axis = None
        gen._event_stream = MagicMock()
        gen._task = None
        gen._stage_init_task = None
        gen._async_tasks = []
        gen._tile_counter = 0
        gen._floor = None
        gen._ceiling = None
        gen._tile_size = None
        gen._resolution = None
        gen._range = None
        gen._bounds_top = None
        gen._bounds_bottom = None
        gen._executor = MagicMock()
        gen._stage_sub = MagicMock()

        if settings_dict:
            gen._settings.get.side_effect = lambda key, *a: settings_dict.get(key)
        else:
            gen._settings.get.return_value = None

        return gen

    def _create_mock_window(self):
        """Create a MagicMock with MinimapWindow-compatible attributes.

        MinimapWindow extends omni.ui.Window (C++ type) and cannot be
        instantiated via object.__new__().  Tests use MagicMock and call
        unbound methods/descriptors from MinimapWindow when needed.
        """
        win = MagicMock()
        win._cam_zoom = 700
        win._cam_size = 0.5
        win._show_settings = None
        win._settings = MagicMock()
        win._event_stream = MagicMock()
        win._simple_model = MagicMock()
        win._actor_world_pos = Gf.Vec3d(0, 0, 0)
        win._image_layer = None
        win._provider = None
        win.arc = MagicMock()
        win.interaction_arc = MagicMock()
        win.center_dot = MagicMock()
        win.frame = MagicMock()
        win._camera_scene_view = MagicMock()
        return win

    # ------------------------------------------------------------------
    # Event flow
    # ------------------------------------------------------------------

    async def test_generator_update_event_type(self):
        """Dispatch of UPDATE on generator event stream invokes subscribers."""
        gen = self._create_generator()
        received = []

        def on_event(event):
            received.append(event.type)

        gen._event_stream = _FakeEventStream()
        gen._event_stream.create_subscription_to_pop(on_event, name="spy")
        gen._event_stream.dispatch(MinimapGeneratorEventTypes.UPDATE)

        self.assertEqual(received, [int(MinimapGeneratorEventTypes.UPDATE)])

    async def test_generator_clear_event_type(self):
        """Dispatch of CLEAR on generator event stream invokes subscribers."""
        gen = self._create_generator()
        received = []

        def on_event(event):
            received.append(event.type)

        gen._event_stream = _FakeEventStream()
        gen._event_stream.create_subscription_to_pop(on_event, name="spy")
        gen._event_stream.dispatch(MinimapGeneratorEventTypes.CLEAR)

        self.assertEqual(received, [int(MinimapGeneratorEventTypes.CLEAR)])

    # ------------------------------------------------------------------
    # Settings persistence across components
    # ------------------------------------------------------------------

    async def test_settings_persist_floor(self):
        """Setting floor on generator persists to carb settings."""
        gen = self._create_generator()
        gen.floor = 3.0

        gen._settings.set.assert_called_with(S_PATH.FLOOR, 3.0)
        self.assertEqual(gen._floor, 3.0)

    async def test_settings_persist_ceiling(self):
        """Setting ceiling on generator persists to carb settings."""
        gen = self._create_generator()
        gen.ceiling = 12.0

        gen._settings.set.assert_called_with(S_PATH.CEILING, 12.0)
        self.assertEqual(gen._ceiling, 12.0)

    # ------------------------------------------------------------------
    # Stage lifecycle
    # ------------------------------------------------------------------

    @patch("omni.sample.minimap.generator._gpu_cleanup_sync")
    async def test_stage_closed_clears_state(self, mock_gpu_sync):
        """_on_stage_closed clears all cached state."""
        gen = self._create_generator()
        gen._stage = MagicMock()
        gen._floor = 5.0
        gen._ceiling = 15.0
        gen._tile_size = 128
        gen._resolution = 1024
        gen._range = Gf.Range3d(Gf.Vec3d(0, 0, 0), Gf.Vec3d(100, 100, 100))

        gen._on_stage_closed()

        mock_gpu_sync.assert_called_once()
        self.assertIsNone(gen._stage)
        self.assertIsNone(gen._floor)
        self.assertIsNone(gen._ceiling)
        self.assertIsNone(gen._tile_size)
        self.assertIsNone(gen._resolution)
        self.assertIsNone(gen._range)

    async def test_window_show_settings_after_no_tiles(self):
        """When no tiles are loaded, show_settings should be set to True."""
        from omni.sample.minimap.window import MinimapWindow

        win = self._create_mock_window()
        win._show_settings = False

        # Simulate the logic from generator._on_stage_opened which sets
        # self._window.show_settings = not tiles_loaded
        tiles_loaded = False
        with patch("omni.sample.minimap.window.carb.settings.get_settings") as mock_gs:
            mock_gs.return_value = MagicMock()
            MinimapWindow.show_settings.fset(win, not tiles_loaded)

        self.assertTrue(win._show_settings)
        win._event_stream.dispatch.assert_called_with(WindowEventTypes.SHOW_SETTINGS)
