# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from unittest.mock import MagicMock, Mock, patch

import omni.kit.test
from omni.sample.reticle import constants
from omni.sample.reticle.models import ReticleModel
from omni.sample.reticle.views import ReticleMenu, ReticleScene


class TestReticleIntegration(omni.kit.test.AsyncTestCase):
    """Integration tests demonstrating how Reticle components work together.

    These tests focus on component interactions rather than individual component behavior,
    which is covered in unit tests.
    """

    async def setUp(self):
        """Set up test environment before each test."""
        self.model = ReticleModel()

    def _create_mock_viewport_api(self, width=1920, height=1080):
        """Create a mock viewport API for testing."""
        mock_vp_api = Mock()
        mock_vp_api.resolution = (width, height)
        mock_vp_api.subscribe_to_render_settings_change = Mock(return_value=Mock())
        return mock_vp_api

    def _create_mock_ui_components(self, mock_ui, mock_scene):
        """Set up common UI mocks for ReticleScene tests."""
        mock_ui.ZStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.ZStack.return_value.__exit__ = Mock(return_value=None)
        mock_ui.ZStack.return_value.clear = Mock()
        mock_ui.VStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.VStack.return_value.__exit__ = Mock(return_value=None)
        mock_ui.HStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.HStack.return_value.__exit__ = Mock(return_value=None)
        mock_ui.Spacer = Mock()

        mock_scene_view = Mock()
        mock_scene_view.scene = Mock()
        mock_scene_view.scene.__enter__ = Mock(return_value=mock_scene_view.scene)
        mock_scene_view.scene.__exit__ = Mock(return_value=None)
        mock_scene_view.scene.clear = Mock()
        mock_scene.SceneView.return_value = mock_scene_view
        return mock_scene_view

    @patch("omni.sample.reticle.views.ReticleMenu")
    @patch("omni.sample.reticle.views.scene")
    @patch("omni.sample.reticle.views.ui")
    async def test_scene_responds_to_model_changes(self, mock_ui, mock_scene, mock_menu_class):
        """Test the observer pattern: scene rebuilds when model changes.

        This demonstrates how the view automatically updates when the model state changes,
        a key pattern in Model-View architectures.
        """
        mock_scene_view = self._create_mock_ui_components(mock_ui, mock_scene)
        mock_vp_api = self._create_mock_viewport_api()
        vp_args = {"viewport_api": mock_vp_api}

        # Create scene with custom model
        with patch.object(ReticleScene, "_model", self.model, create=True):
            scene = ReticleScene(vp_args)
            scene._model = self.model
            scene._model.add_reticle_changed_fn(scene._rebuild)

        # Clear any calls from initialization
        mock_scene_view.scene.clear.reset_mock()

        # Change model and verify scene rebuilds
        self.model.composition_mode.set_value(constants.CompositionGuidelines.THIRDS)
        mock_scene_view.scene.clear.assert_called()

    @patch("omni.sample.reticle.views.ui.Button")
    async def test_menu_and_model_stay_synchronized(self, mock_button):
        """Test shared state pattern: menu and model stay synchronized.

        This demonstrates how UI components can share state through a common model,
        ensuring consistency across the application.
        """
        menu = ReticleMenu(self.model)

        # Create mock buttons for composition mode changes
        menu.comp_off_button = Mock()
        menu.comp_thirds_button = Mock()
        menu.comp_quad_button = Mock()
        menu.comp_crosshair_button = Mock()

        # Simulate menu changing composition mode
        menu.on_composition_mode_changed(constants.CompositionGuidelines.QUAD)

        # Menu and model should have the same value
        self.assertEqual(menu.model.composition_mode.as_int, constants.CompositionGuidelines.QUAD)
        self.assertEqual(self.model.composition_mode.as_int, constants.CompositionGuidelines.QUAD)

    @patch("omni.sample.reticle.views.ReticleMenu")
    @patch("omni.sample.reticle.views.scene")
    @patch("omni.sample.reticle.views.ui")
    async def test_viewport_resolution_change_triggers_subscription(self, mock_ui, mock_scene, mock_menu_class):
        """Test viewport event integration: scene registers for viewport changes.

        This demonstrates how extensions integrate with viewport events to handle
        dynamic viewport changes like resizing.
        """
        self._create_mock_ui_components(mock_ui, mock_scene)
        mock_vp_api = self._create_mock_viewport_api()
        vp_args = {"viewport_api": mock_vp_api}

        scene = ReticleScene(vp_args)

        # Verify viewport change subscription was registered
        mock_vp_api.subscribe_to_render_settings_change.assert_called_once()

    @patch("omni.sample.reticle.views.ReticleMenu")
    @patch("omni.sample.reticle.views.scene")
    @patch("omni.sample.reticle.views.ui")
    async def test_multiple_viewports_have_independent_aspect_ratios(self, mock_ui, mock_scene, mock_menu_class):
        """Test that each viewport maintains its own independent aspect ratio.

        When multiple viewports exist with different resolutions, each ReticleScene
        should calculate and maintain its own aspect ratio independently.
        """
        self._create_mock_ui_components(mock_ui, mock_scene)

        # Create two scenes with different viewport APIs
        mock_vp_api1 = self._create_mock_viewport_api(1920, 1080)
        mock_vp_api2 = self._create_mock_viewport_api(1280, 720)

        scene1 = ReticleScene({"viewport_api": mock_vp_api1})
        scene2 = ReticleScene({"viewport_api": mock_vp_api2})

        # Verify aspect ratios are independent
        self.assertAlmostEqual(scene1._aspect_ratio, 1920 / 1080, places=2)
        self.assertAlmostEqual(scene2._aspect_ratio, 1280 / 720, places=2)

    @patch("omni.sample.reticle.views.ReticleMenu")
    @patch("omni.sample.reticle.views.scene")
    @patch("omni.sample.reticle.views.ui")
    async def test_scene_cleanup(self, mock_ui, mock_scene, mock_menu_class):
        """Test resource management: proper cleanup when scene is destroyed.

        This demonstrates the importance of proper resource cleanup in extensions,
        preventing memory leaks and ensuring clean shutdown.
        """
        mock_scene_view = self._create_mock_ui_components(mock_ui, mock_scene)

        mock_menu_instance = Mock()
        mock_menu_instance.destroy = Mock()
        mock_menu_class.return_value = mock_menu_instance

        mock_vp_api = self._create_mock_viewport_api()
        scene = ReticleScene({"viewport_api": mock_vp_api})

        # Destroy scene
        scene.destroy()

        # Verify cleanup
        mock_menu_instance.destroy.assert_called_once()
        mock_scene_view.scene.clear.assert_called()
        self.assertIsNone(scene.scene_view)
        self.assertIsNone(scene._vp_api)

    @patch("omni.sample.reticle.views.ReticleMenu")
    @patch("omni.sample.reticle.views.scene")
    @patch("omni.sample.reticle.views.ui")
    async def test_all_composition_modes_can_be_set(self, mock_ui, mock_scene, mock_menu_class):
        """Test that all composition modes can be rendered without error.

        This demonstrates comprehensive support for all composition guidelines.
        """
        mock_scene_view = self._create_mock_ui_components(mock_ui, mock_scene)
        mock_vp_api = self._create_mock_viewport_api()

        scene = ReticleScene({"viewport_api": mock_vp_api})

        # Test each composition mode
        modes = [
            constants.CompositionGuidelines.OFF,
            constants.CompositionGuidelines.THIRDS,
            constants.CompositionGuidelines.QUAD,
            constants.CompositionGuidelines.CROSSHAIR,
        ]

        for mode in modes:
            mock_scene_view.scene.clear.reset_mock()
            scene._model.composition_mode.set_value(mode)
            # Verify the model was updated
            self.assertEqual(scene._model.composition_mode.as_int, mode)

    @patch("omni.sample.reticle.views.ReticleMenu")
    @patch("omni.sample.reticle.views.scene")
    @patch("omni.sample.reticle.views.ui")
    async def test_safe_areas_can_be_enabled_together(self, mock_ui, mock_scene, mock_menu_class):
        """Test enabling multiple safe areas simultaneously.

        This demonstrates that different safe area overlays can coexist.
        """
        self._create_mock_ui_components(mock_ui, mock_scene)
        mock_vp_api = self._create_mock_viewport_api()

        scene = ReticleScene({"viewport_api": mock_vp_api})

        # Enable all safe areas
        scene._model.action_safe_enabled.set_value(True)
        scene._model.title_safe_enabled.set_value(True)
        scene._model.custom_safe_enabled.set_value(True)

        # Verify all are enabled
        self.assertTrue(scene._model.action_safe_enabled.as_bool)
        self.assertTrue(scene._model.title_safe_enabled.as_bool)
        self.assertTrue(scene._model.custom_safe_enabled.as_bool)

    @patch("omni.sample.reticle.views.ReticleMenu")
    @patch("omni.sample.reticle.views.scene")
    @patch("omni.sample.reticle.views.ui")
    async def test_letterbox_with_composition_guides(self, mock_ui, mock_scene, mock_menu_class):
        """Test letterbox combined with composition guidelines.

        This demonstrates that letterbox and composition guides can be active together.
        """
        self._create_mock_ui_components(mock_ui, mock_scene)
        mock_vp_api = self._create_mock_viewport_api()

        scene = ReticleScene({"viewport_api": mock_vp_api})

        # Enable letterbox and composition mode
        scene._model.letterbox_enabled.set_value(True)
        scene._model.composition_mode.set_value(constants.CompositionGuidelines.THIRDS)

        # Verify both settings are active
        self.assertTrue(scene._model.letterbox_enabled.as_bool)
        self.assertEqual(scene._model.composition_mode.as_int, constants.CompositionGuidelines.THIRDS)

    async def test_model_persistence_across_changes(self):
        """Test that model maintains state across multiple changes.

        This demonstrates state persistence in the model.
        """
        # Set initial values
        self.model.composition_mode.set_value(constants.CompositionGuidelines.CROSSHAIR)
        self.model.action_safe_percentage.set_value(92.5)
        self.model.letterbox_ratio.set_value(2.35)

        # Make other changes
        self.model.title_safe_enabled.set_value(True)
        self.model.title_safe_percentage.set_value(87.0)

        # Verify initial values are still maintained
        self.assertEqual(self.model.composition_mode.as_int, constants.CompositionGuidelines.CROSSHAIR)
        self.assertAlmostEqual(self.model.action_safe_percentage.as_float, 92.5, places=1)
        self.assertAlmostEqual(self.model.letterbox_ratio.as_float, 2.35, places=2)
