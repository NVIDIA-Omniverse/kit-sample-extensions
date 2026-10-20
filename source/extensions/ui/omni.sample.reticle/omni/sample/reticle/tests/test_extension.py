# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from unittest.mock import Mock, patch

import omni.kit.test
from omni.sample.reticle.extension import SampleViewportReticleExtension


class TestReticleExtension(omni.kit.test.AsyncTestCase):
    """Basic tests for Reticle extension lifecycle using RegisterViewportLayer."""

    async def setUp(self):
        """Set up test fixtures before each test method."""
        self.extension = SampleViewportReticleExtension()

    async def test_extension_startup_and_shutdown_with_registry(self):
        """Test that extension can start up and shut down using RegisterViewportLayer."""
        # Mock RegisterViewportLayer
        with patch("omni.sample.reticle.extension.RegisterViewportLayer") as mock_register:
            mock_layer_instance = Mock()
            mock_register.return_value = mock_layer_instance

            # Start the extension
            self.extension.on_startup("test_ext_id")

            # Verify RegisterViewportLayer was called with ReticleScene class and ext_id
            from omni.sample.reticle.views import ReticleScene

            mock_register.assert_called_once()
            call_args = mock_register.call_args
            self.assertEqual(call_args[0][0], ReticleScene)
            self.assertEqual(call_args[0][1], "test_ext_id")

            # Verify the layer handle was stored
            self.assertEqual(self.extension._vp_layer, mock_layer_instance)

            # Shutdown the extension
            self.extension.on_shutdown()

            # Verify cleanup (layer handle set to None)
            self.assertIsNone(self.extension._vp_layer)

    async def test_extension_shutdown_without_startup(self):
        """Test shutdown when extension was never started."""
        # Should not raise error even if _vp_layer doesn't exist
        self.extension.on_shutdown()

    async def test_extension_registers_reticle_scene_class(self):
        """Test that extension registers ReticleScene class with the viewport registry."""
        with patch("omni.sample.reticle.extension.RegisterViewportLayer") as mock_register:
            self.extension.on_startup("test_ext_id")

            # Verify RegisterViewportLayer was called
            mock_register.assert_called_once()

            # Get the scene class that was registered
            from omni.sample.reticle.views import ReticleScene

            registered_class = mock_register.call_args[0][0]
            self.assertEqual(registered_class, ReticleScene)
