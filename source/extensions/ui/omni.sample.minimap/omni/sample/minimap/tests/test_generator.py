# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Tests for minimap generator, data classes, and utility functions."""

import io
import math
from unittest.mock import MagicMock, Mock, patch

import omni.kit.test
from omni.sample.minimap.generator import (
    CaptureJobDesc,
    MapTile,
    MapTileGroup,
    MapTileSaved,
    MinimapGenerator,
    MinimapGeneratorEventTypes,
    _get_axis_indices,
)
from omni.sample.minimap.settings import S_PATH
from PIL import Image
from pxr import Gf, UsdGeom


# ===========================================================================
# Utility function tests
# ===========================================================================
class TestUtilityFunctions(omni.kit.test.AsyncTestCase):
    """Tests for module-level utility functions."""

    async def test_get_axis_indices_y_up(self):
        """Y-up axis produces (h=0, v=2, d=1, rot_axis=0, rot=-90)."""
        result = _get_axis_indices(UsdGeom.Tokens.y)
        self.assertEqual(result, (0, 2, 1, 0, -90))

    async def test_get_axis_indices_z_up(self):
        """Z-up axis produces (h=1, v=0, d=2, rot_axis=2, rot=90)."""
        result = _get_axis_indices(UsdGeom.Tokens.z)
        self.assertEqual(result, (1, 0, 2, 2, 90))

    async def test_event_types_are_distinct(self):
        """UPDATE and CLEAR have distinct integer values."""
        self.assertNotEqual(int(MinimapGeneratorEventTypes.UPDATE), int(MinimapGeneratorEventTypes.CLEAR))


# ===========================================================================
# MapTile tests
# ===========================================================================
class TestMapTile(omni.kit.test.AsyncTestCase):
    """Tests for the MapTile class."""

    async def test_map_tile_init(self):
        """Fresh MapTile has _cleaned=False, _system_data=None."""
        tile = MapTile()
        self.assertFalse(tile._cleaned)
        self.assertIsNone(tile._system_data)

    async def test_map_tile_cleanup_sets_flag(self):
        """cleanup() sets _cleaned flag; second call is a no-op."""
        tile = MapTile()
        tile.image_provider = Mock()
        tile.image_data = None

        tile.cleanup()
        self.assertTrue(tile._cleaned)

        # Should not raise on second call
        tile.cleanup()
        self.assertTrue(tile._cleaned)

    async def test_map_tile_cleanup_nullifies_resources(self):
        """cleanup() sets image_provider and _system_data to None."""
        tile = MapTile()
        tile.image_provider = Mock()
        tile.image_data = None
        tile._system_data = bytearray(b"fake")

        tile.cleanup()

        self.assertIsNone(tile.image_provider)
        self.assertIsNone(tile._system_data)

    @patch("omni.sample.minimap.generator.ui.ByteImageProvider")
    async def test_map_tile_from_saved_roundtrip(self, mock_bip_cls):
        """MapTile.from_saved restores tile geometry and image data from MapTileSaved."""
        mock_provider = MagicMock()
        mock_bip_cls.return_value = mock_provider

        # Create a small 2x2 RGBA PNG
        img = Image.new("RGBA", (2, 2), (255, 0, 0, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        saved = MapTileSaved(
            tile_width=100,
            tile_height=100,
            tile_center=(50.0, 50.0),
            image_data=png_bytes,
        )

        tile = MapTile.from_saved(saved)

        self.assertEqual(tile.tile_width, 100)
        self.assertEqual(tile.tile_height, 100)
        self.assertEqual(tile.tile_center, (50.0, 50.0))
        self.assertEqual(tile.image_width, 2)
        self.assertEqual(tile.image_height, 2)
        self.assertIsNotNone(tile._system_data)
        mock_provider.set_bytes_data.assert_called_once()


# ===========================================================================
# MapTileSaved tests
# ===========================================================================
class TestMapTileSaved(omni.kit.test.AsyncTestCase):
    """Tests for the MapTileSaved dataclass."""

    async def test_from_tile_with_system_data(self):
        """from_tile encodes system-memory tile data as PNG."""
        tile = MapTile()
        tile.tile_width = 64
        tile.tile_height = 64
        tile.tile_center = (0.0, 0.0)
        tile.image_width = 2
        tile.image_height = 2
        # 2x2 RGBA = 16 bytes
        tile._system_data = bytearray(b"\xff\x00\x00\xff" * 4)

        saved = MapTileSaved.from_tile(tile)

        self.assertEqual(saved.tile_width, 64)
        self.assertEqual(saved.tile_height, 64)
        self.assertEqual(saved.tile_center, (0.0, 0.0))
        # Verify PNG header bytes
        self.assertTrue(saved.image_data[:4] == b"\x89PNG")

    async def test_from_tile_raises_without_data(self):
        """from_tile raises ValueError when no image data is available."""
        tile = MapTile()
        tile.tile_width = 64
        tile.tile_height = 64
        tile.tile_center = (0.0, 0.0)
        tile.image_width = 2
        tile.image_height = 2
        # No _system_data and no image_data set

        with self.assertRaises(ValueError):
            MapTileSaved.from_tile(tile)


# ===========================================================================
# MapTileGroup tests
# ===========================================================================
class TestMapTileGroup(omni.kit.test.AsyncTestCase):
    """Tests for the MapTileGroup class."""

    async def test_tile_group_empty_bbox_intersects_all(self):
        """Group with empty Range3d always returns True for intersects()."""
        empty_bbox = Gf.BBox3d(Gf.Range3d())
        group = MapTileGroup(empty_bbox)
        self.assertTrue(group.intersects(Gf.Vec3d(999, 999, 999)))

    @patch("omni.sample.minimap.generator.omni.usd.get_context")
    async def test_tile_group_intersects_inside(self, mock_get_context):
        """Position inside bbox returns True."""
        mock_stage = MagicMock()
        mock_get_context.return_value.get_stage.return_value = mock_stage

        # Patch UsdGeom.GetStageUpAxis at the call site
        with patch("omni.sample.minimap.generator.UsdGeom.GetStageUpAxis", return_value=UsdGeom.Tokens.y):
            bbox = Gf.BBox3d(Gf.Range3d(Gf.Vec3d(0, 0, 0), Gf.Vec3d(100, 100, 100)))
            group = MapTileGroup(bbox)
            self.assertTrue(group.intersects(Gf.Vec3d(50, 50, 50)))

    @patch("omni.sample.minimap.generator.omni.usd.get_context")
    async def test_tile_group_intersects_outside(self, mock_get_context):
        """Position outside bbox (horizontal) returns False."""
        mock_stage = MagicMock()
        mock_get_context.return_value.get_stage.return_value = mock_stage

        with patch("omni.sample.minimap.generator.UsdGeom.GetStageUpAxis", return_value=UsdGeom.Tokens.y):
            bbox = Gf.BBox3d(Gf.Range3d(Gf.Vec3d(0, 0, 0), Gf.Vec3d(100, 100, 100)))
            group = MapTileGroup(bbox)
            # X = 200 is outside [0,100]
            self.assertFalse(group.intersects(Gf.Vec3d(200, 50, 50)))

    async def test_tile_group_stores_tiles(self):
        """Group stores and exposes tiles."""
        tile_a, tile_b = MapTile(), MapTile()
        bbox = Gf.BBox3d(Gf.Range3d())
        group = MapTileGroup(bbox, [tile_a, tile_b])
        self.assertEqual(len(group.tiles), 2)


# ===========================================================================
# CaptureJobDesc tests
# ===========================================================================
class TestCaptureJobDesc(omni.kit.test.AsyncTestCase):
    """Tests for the CaptureJobDesc dataclass."""

    async def test_capture_job_desc_fields(self):
        """CaptureJobDesc stores all provided field values."""
        desc = CaptureJobDesc(
            h_min=0.0,
            h_max=128.0,
            v_min=0.0,
            v_max=128.0,
            h_axis_idx=0,
            v_axis_idx=2,
            d_axis_idx=1,
            cam_rot_axis=0,
            cam_rot=-90.0,
            job_limit=3,
            capture_height_min_meters=0.0,
            capture_height_max_meters=10.0,
            mpu=0.01,
            tile_size=128.0,
            index=1,
        )
        self.assertEqual(desc.h_min, 0.0)
        self.assertEqual(desc.h_max, 128.0)
        self.assertEqual(desc.index, 1)
        self.assertEqual(desc.mpu, 0.01)
        self.assertEqual(desc.job_limit, 3)


# ===========================================================================
# MinimapGenerator tests
# ===========================================================================
class TestMinimapGenerator(omni.kit.test.AsyncTestCase):
    """Tests for MinimapGenerator properties, calculations, and cleanup."""

    def _create_generator(self, stage=None, settings_dict=None):
        """Create a MinimapGenerator with mocked dependencies."""
        gen = MinimapGenerator.__new__(MinimapGenerator)

        # Minimal internal state so property access does not crash
        gen._app = MagicMock()
        gen._window = MagicMock()
        gen._settings = MagicMock()
        gen._usd_context = MagicMock()
        gen._stage = stage
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

        # Wire settings.get to return from dict if provided
        if settings_dict:
            gen._settings.get.side_effect = lambda key, *a: settings_dict.get(key)
        else:
            gen._settings.get.return_value = None

        return gen

    # ------------------------------------------------------------------
    # Property caching
    # ------------------------------------------------------------------

    async def test_floor_property_set_and_get(self):
        """Setting floor caches the value and persists to settings."""
        gen = self._create_generator()
        gen.floor = 2.5
        self.assertEqual(gen._floor, 2.5)
        gen._settings.set.assert_called_with(S_PATH.FLOOR, 2.5)
        # Reading back should return cached value
        self.assertEqual(gen.floor, 2.5)

    async def test_ceiling_property_set_and_get(self):
        """Setting ceiling caches the value and persists to settings."""
        gen = self._create_generator()
        gen.ceiling = 10.0
        self.assertEqual(gen._ceiling, 10.0)
        gen._settings.set.assert_called_with(S_PATH.CEILING, 10.0)
        self.assertEqual(gen.ceiling, 10.0)

    async def test_tile_size_defaults_to_256(self):
        """When no metadata or cache exists, tile_size falls back to 256."""
        gen = self._create_generator(settings_dict={S_PATH.DEFAULT_TILE_SIZE: 256})
        # No stage, no cache
        self.assertEqual(gen.tile_size, 256)

    async def test_resolution_property(self):
        """Setting resolution caches and persists."""
        gen = self._create_generator()
        gen.resolution = 2048
        self.assertEqual(gen.resolution, 2048)
        gen._settings.set.assert_called_with(S_PATH.RESOLUTION, 2048)

    # ------------------------------------------------------------------
    # Tile calculations
    # ------------------------------------------------------------------

    def _mock_stage(self, up_axis=UsdGeom.Tokens.y, mpu=0.01):
        """Create a mock stage with configurable up axis and meters per unit."""
        mock_stage = MagicMock()
        mock_stage.GetPseudoRoot.return_value = MagicMock()
        mock_stage.GetRootLayer.return_value.customLayerData = {}
        return mock_stage

    async def test_calculate_tile_count_no_stage(self):
        """Returns 1 when no stage is available."""
        gen = self._create_generator()
        self.assertEqual(gen.calculate_tile_count(), 1)

    @patch("omni.sample.minimap.generator.UsdGeom.GetStageMetersPerUnit", return_value=0.01)
    @patch("omni.sample.minimap.generator.UsdGeom.GetStageUpAxis", return_value=UsdGeom.Tokens.y)
    async def test_calculate_tile_count_single_tile(self, mock_up, mock_mpu):
        """Small scene with large tile_size returns 1."""
        stage = self._mock_stage()
        gen = self._create_generator(stage=stage, settings_dict={S_PATH.DEFAULT_TILE_SIZE: 256})
        # Set a small range and large tile size
        gen._range = Gf.Range3d(Gf.Vec3d(0, 0, 0), Gf.Vec3d(100, 100, 100))
        gen._tile_size = 10000  # Very large tile

        count = gen.calculate_tile_count()
        self.assertEqual(count, 1)

    @patch("omni.sample.minimap.generator.UsdGeom.GetStageMetersPerUnit", return_value=1.0)
    @patch("omni.sample.minimap.generator.UsdGeom.GetStageUpAxis", return_value=UsdGeom.Tokens.y)
    async def test_calculate_tile_count_multiple(self, mock_up, mock_mpu):
        """512x512 scene with 128m tiles returns expected count > 1."""
        stage = self._mock_stage()
        gen = self._create_generator(stage=stage)
        gen._range = Gf.Range3d(Gf.Vec3d(0, 0, 0), Gf.Vec3d(512, 100, 512))
        gen._tile_size = 128  # 128m tiles

        count = gen.calculate_tile_count()
        # 512*512 / 128^2 * 2 = 32, so expect around 32
        self.assertGreater(count, 1)

    async def test_calculate_tile_size_no_stage(self):
        """Returns default tile size when no stage."""
        gen = self._create_generator(settings_dict={S_PATH.DEFAULT_TILE_SIZE: 256})
        self.assertEqual(gen.calculate_tile_size(4), 256)

    @patch("omni.sample.minimap.generator.UsdGeom.GetStageMetersPerUnit", return_value=1.0)
    @patch("omni.sample.minimap.generator.UsdGeom.GetStageUpAxis", return_value=UsdGeom.Tokens.y)
    async def test_calculate_tile_size_single_tile(self, mock_up, mock_mpu):
        """calculate_tile_size(1) returns size >= max horizontal dimension."""
        stage = self._mock_stage()
        gen = self._create_generator(stage=stage)
        gen._range = Gf.Range3d(Gf.Vec3d(0, 0, 0), Gf.Vec3d(200, 50, 300))

        size = gen.calculate_tile_size(1)
        # Should cover the larger horizontal dimension (300 for Y-up, axes 0 and 2)
        self.assertGreaterEqual(size, 300)

    @patch("omni.sample.minimap.generator.UsdGeom.GetStageMetersPerUnit", return_value=1.0)
    @patch("omni.sample.minimap.generator.UsdGeom.GetStageUpAxis", return_value=UsdGeom.Tokens.y)
    async def test_calculate_tile_size_multiple(self, mock_up, mock_mpu):
        """calculate_tile_size(4) returns smaller size than single tile."""
        stage = self._mock_stage()
        gen = self._create_generator(stage=stage)
        gen._range = Gf.Range3d(Gf.Vec3d(0, 0, 0), Gf.Vec3d(500, 50, 500))

        size_1 = gen.calculate_tile_size(1)
        size_4 = gen.calculate_tile_size(4)
        self.assertLess(size_4, size_1)

    # ------------------------------------------------------------------
    # get_tiles
    # ------------------------------------------------------------------

    async def test_get_tiles_empty_groups(self):
        """Returns None when no tile groups exist."""
        gen = self._create_generator()
        self.assertIsNone(gen.get_tiles(Gf.Vec3d(0, 0, 0)))

    @patch("omni.sample.minimap.generator.omni.usd.get_context")
    async def test_get_tiles_matching_group(self, mock_get_context):
        """Returns tiles from the group that intersects the position."""
        mock_stage = MagicMock()
        mock_get_context.return_value.get_stage.return_value = mock_stage

        gen = self._create_generator()
        tile = MapTile()
        # Use empty bbox so it always intersects
        group = MapTileGroup(Gf.BBox3d(Gf.Range3d()), [tile])
        gen._map_tile_groups = [group]

        result = gen.get_tiles(Gf.Vec3d(50, 50, 50))
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)

    # ------------------------------------------------------------------
    # Toggle features
    # ------------------------------------------------------------------

    async def test_toggle_features_disable_and_restore(self):
        """Disabling features returns original values; restoring writes them back."""
        gen = self._create_generator()
        original_values = {"/rtx/shadows/enabled": True, "/app/viewport/grid/enabled": True}
        gen._settings.get.side_effect = lambda key, *a: original_values.get(key)

        # Disable
        restore_dict = gen._toggle_features()
        self.assertIsInstance(restore_dict, dict)

        # Restore
        gen._toggle_features(restore_dict)
        # Settings should have been restored (set called with original values)
        for path, value in restore_dict.items():
            if value is not None:
                gen._settings.set.assert_any_call(path, value)

    # ------------------------------------------------------------------
    # Destroy
    # ------------------------------------------------------------------

    @patch("omni.sample.minimap.generator._gpu_cleanup_sync")
    async def test_destroy_cancels_tasks(self, mock_gpu_sync):
        """destroy() cancels async tasks and shuts down executor."""
        gen = self._create_generator()
        mock_task = MagicMock()
        mock_task.done.return_value = False
        gen._task = mock_task
        gen._async_tasks = [mock_task]

        # Save a reference before destroy sets _executor to None
        mock_executor = gen._executor

        gen.destroy()

        mock_task.cancel.assert_called()
        mock_executor.shutdown.assert_called_once_with(wait=False)
        self.assertIsNone(gen._window)
        self.assertIsNone(gen._stage)

    @patch("omni.sample.minimap.generator._gpu_cleanup_sync")
    async def test_destroy_is_idempotent(self, mock_gpu_sync):
        """Calling destroy() twice does not raise."""
        gen = self._create_generator()
        gen._task = None

        gen.destroy()
        gen.destroy()  # Should not raise
