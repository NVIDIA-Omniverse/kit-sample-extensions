## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
"""Tests for CreoCameraManipulator and CreoCameraFactory.

Tests the factory function returns a manipulator instance.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import omni.kit.test
from omni.kit.manipulator.creo_camera.creo_camera_manipulator import (
    CreoCameraFactory,
    CreoCameraManipulator,
)


class TestCreoCameraFactory(omni.kit.test.AsyncTestCase):
    async def test_factory_returns_manipulator_instance(self):
        mock_manipulator = Mock(spec=CreoCameraManipulator)
        with patch(
            "omni.kit.manipulator.creo_camera.creo_camera_manipulator.CreoCameraManipulator",
            return_value=mock_manipulator,
        ):
            result = CreoCameraFactory({"viewport_api": object()})
            self.assertIs(result, mock_manipulator)

    async def test_factory_passes_viewport_api_from_desc(self):
        mock_manipulator = Mock(spec=CreoCameraManipulator)
        viewport_api = object()
        with patch(
            "omni.kit.manipulator.creo_camera.creo_camera_manipulator.CreoCameraManipulator",
            return_value=mock_manipulator,
        ) as mock_class:
            CreoCameraFactory({"viewport_api": viewport_api})
            mock_class.assert_called_once_with(viewport_api)

    async def test_factory_handles_missing_viewport_api(self):
        mock_manipulator = Mock(spec=CreoCameraManipulator)
        with patch(
            "omni.kit.manipulator.creo_camera.creo_camera_manipulator.CreoCameraManipulator",
            return_value=mock_manipulator,
        ) as mock_class:
            CreoCameraFactory({})
            mock_class.assert_called_once_with(None)

    async def test_factory_extracts_only_viewport_api_key(self):
        mock_manipulator = Mock(spec=CreoCameraManipulator)
        with patch(
            "omni.kit.manipulator.creo_camera.creo_camera_manipulator.CreoCameraManipulator",
            return_value=mock_manipulator,
        ) as mock_class:
            CreoCameraFactory({"viewport_api": "test_value", "other_key": "ignored"})
            mock_class.assert_called_once_with("test_value")
