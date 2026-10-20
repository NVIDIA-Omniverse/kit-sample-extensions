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
from omni.ui import color as cl


class TestReticleScene(omni.kit.test.AsyncTestCase):
    """Unit tests for ReticleScene class.

    ReticleScene is the main class used by RegisterViewportLayer to create
    per-viewport reticle overlays. When initialized, a ui.Frame is already
    in scope from the registry.
    """

    def _create_mock_viewport_api(self, width=1920, height=1080):
        """Create a mock viewport API for testing."""
        mock_vp_api = Mock()
        mock_vp_api.resolution = (width, height)
        mock_vp_api.subscribe_to_render_settings_change = Mock(return_value=Mock())
        return mock_vp_api

    @patch("omni.sample.reticle.views.ReticleMenu")
    @patch("omni.sample.reticle.views.scene")
    @patch("omni.sample.reticle.views.ui")
    def test_scene_initialization(self, mock_ui, mock_scene, mock_menu_class):
        """Test ReticleScene initialization."""
        mock_vp_api = self._create_mock_viewport_api()
        vp_args = {"viewport_api": mock_vp_api}

        # Mock UI components
        mock_ui.ZStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.ZStack.return_value.__exit__ = Mock(return_value=None)
        mock_ui.VStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.VStack.return_value.__exit__ = Mock(return_value=None)
        mock_ui.HStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.HStack.return_value.__exit__ = Mock(return_value=None)

        # Mock scene view
        mock_scene_view = Mock()
        mock_scene_view.scene = Mock()
        mock_scene_view.scene.__enter__ = Mock(return_value=mock_scene_view.scene)
        mock_scene_view.scene.__exit__ = Mock(return_value=None)
        mock_scene.SceneView.return_value = mock_scene_view

        # Create scene
        scene = ReticleScene(vp_args)

        # Verify initialization
        self.assertEqual(scene._vp_api, mock_vp_api)
        self.assertIsNotNone(scene._model)
        self.assertIsNotNone(scene._root)
        mock_vp_api.subscribe_to_render_settings_change.assert_called_once()

    @patch("omni.sample.reticle.views.ReticleMenu")
    @patch("omni.sample.reticle.views.scene")
    @patch("omni.sample.reticle.views.ui")
    def test_aspect_ratio_calculation(self, mock_ui, mock_scene, mock_menu_class):
        """Test aspect ratio calculation from viewport resolution."""
        mock_vp_api = self._create_mock_viewport_api(1920, 1080)
        vp_args = {"viewport_api": mock_vp_api}

        # Mock UI components
        mock_ui.ZStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.ZStack.return_value.__exit__ = Mock(return_value=None)
        mock_ui.VStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.VStack.return_value.__exit__ = Mock(return_value=None)
        mock_ui.HStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.HStack.return_value.__exit__ = Mock(return_value=None)

        mock_scene_view = Mock()
        mock_scene_view.scene = Mock()
        mock_scene_view.scene.__enter__ = Mock(return_value=mock_scene_view.scene)
        mock_scene_view.scene.__exit__ = Mock(return_value=None)
        mock_scene.SceneView.return_value = mock_scene_view

        scene = ReticleScene(vp_args)

        # Check aspect ratio (1920/1080 = 16:9)
        expected_ratio = 1920 / 1080
        self.assertAlmostEqual(scene._aspect_ratio, expected_ratio, places=2)
        self.assertAlmostEqual(scene._get_aspect_ratio(), expected_ratio, places=2)

    def test_aspect_ratio_flip_threshold(self):
        """Test aspect ratio threshold calculation."""
        scene = ReticleScene.__new__(ReticleScene)
        scene._aspect_ratio = 1.5

        threshold = scene._get_aspect_ratio_flip_threshold()
        expected = 1.5 - (1.5 * 0.05)  # 5% buffer
        self.assertAlmostEqual(threshold, expected, places=3)

    @patch("omni.sample.reticle.views.ReticleMenu")
    @patch("omni.sample.reticle.views.scene")
    @patch("omni.sample.reticle.views.ui")
    def test_different_resolutions(self, mock_ui, mock_scene, mock_menu_class):
        """Test scene with different viewport resolutions."""
        resolutions = [(1280, 720), (1920, 1080), (2560, 1440), (1024, 768)]

        # Mock UI components
        mock_ui.ZStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.ZStack.return_value.__exit__ = Mock(return_value=None)
        mock_ui.VStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.VStack.return_value.__exit__ = Mock(return_value=None)
        mock_ui.HStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.HStack.return_value.__exit__ = Mock(return_value=None)

        mock_scene_view = Mock()
        mock_scene_view.scene = Mock()
        mock_scene_view.scene.__enter__ = Mock(return_value=mock_scene_view.scene)
        mock_scene_view.scene.__exit__ = Mock(return_value=None)
        mock_scene.SceneView.return_value = mock_scene_view

        for width, height in resolutions:
            mock_vp_api = self._create_mock_viewport_api(width, height)
            vp_args = {"viewport_api": mock_vp_api}

            scene = ReticleScene(vp_args)

            expected_ratio = width / height
            self.assertAlmostEqual(scene._aspect_ratio, expected_ratio, places=2)

    @patch("omni.sample.reticle.views.ReticleMenu")
    @patch("omni.sample.reticle.views.scene")
    @patch("omni.sample.reticle.views.ui")
    def test_scene_destroy(self, mock_ui, mock_scene, mock_menu_class):
        """Test scene destruction and cleanup."""
        mock_vp_api = self._create_mock_viewport_api()
        vp_args = {"viewport_api": mock_vp_api}

        # Mock UI components
        mock_ui.ZStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.ZStack.return_value.__exit__ = Mock(return_value=None)
        mock_ui.ZStack.return_value.clear = Mock()
        mock_ui.VStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.VStack.return_value.__exit__ = Mock(return_value=None)
        mock_ui.HStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.HStack.return_value.__exit__ = Mock(return_value=None)

        mock_scene_view = Mock()
        mock_scene_view.scene = Mock()
        mock_scene_view.scene.clear = Mock()
        mock_scene_view.scene.__enter__ = Mock(return_value=mock_scene_view.scene)
        mock_scene_view.scene.__exit__ = Mock(return_value=None)
        mock_scene.SceneView.return_value = mock_scene_view

        mock_menu_instance = Mock()
        mock_menu_instance.destroy = Mock()
        mock_menu_class.return_value = mock_menu_instance

        scene = ReticleScene(vp_args)
        scene.scene_view = mock_scene_view
        scene.reticle_menu = mock_menu_instance

        # Destroy
        scene.destroy()

        # Verify cleanup
        mock_scene_view.scene.clear.assert_called_once()
        mock_menu_instance.destroy.assert_called_once()
        self.assertIsNone(scene.scene_view)
        self.assertIsNone(scene.reticle_menu)
        self.assertIsNone(scene._vp_api)

    @patch("omni.sample.reticle.views.ReticleMenu")
    @patch("omni.sample.reticle.views.scene")
    @patch("omni.sample.reticle.views.ui")
    def test_visible_property(self, mock_ui, mock_scene, mock_menu_class):
        """Test visible property getter and setter."""
        mock_vp_api = self._create_mock_viewport_api()
        vp_args = {"viewport_api": mock_vp_api}

        # Mock UI components
        mock_root = Mock()
        mock_root.visible = True
        mock_ui.ZStack.return_value = mock_root
        mock_root.__enter__ = Mock(return_value=mock_root)
        mock_root.__exit__ = Mock(return_value=None)
        mock_ui.VStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.VStack.return_value.__exit__ = Mock(return_value=None)
        mock_ui.HStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.HStack.return_value.__exit__ = Mock(return_value=None)

        mock_scene_view = Mock()
        mock_scene_view.scene = Mock()
        mock_scene_view.scene.__enter__ = Mock(return_value=mock_scene_view.scene)
        mock_scene_view.scene.__exit__ = Mock(return_value=None)
        mock_scene.SceneView.return_value = mock_scene_view

        scene = ReticleScene(vp_args)

        # Test getter
        self.assertTrue(scene.visible)

        # Test setter
        scene.visible = False
        self.assertFalse(mock_root.visible)

    @patch("omni.sample.reticle.views.scene")
    def test_build_thirds(self, mock_scene):
        """Test _build_thirds creates correct lines."""
        scene = ReticleScene.__new__(ReticleScene)
        scene._aspect_ratio = 1.777
        scene.scene_view = Mock()
        scene.scene_view.aspect_ratio_policy = mock_scene.AspectRatioPolicy.PRESERVE_ASPECT_VERTICAL

        scene._build_thirds()

        # Verify 4 lines were created
        self.assertEqual(mock_scene.Line.call_count, 4)

    @patch("omni.sample.reticle.views.scene")
    def test_build_quad(self, mock_scene):
        """Test _build_quad creates correct lines."""
        scene = ReticleScene.__new__(ReticleScene)
        scene._aspect_ratio = 1.777
        scene.scene_view = Mock()
        scene.scene_view.aspect_ratio_policy = mock_scene.AspectRatioPolicy.PRESERVE_ASPECT_VERTICAL

        scene._build_quad()

        # Verify 2 lines were created
        self.assertEqual(mock_scene.Line.call_count, 2)

    @patch("omni.sample.reticle.views.scene")
    def test_build_crosshair(self, mock_scene):
        """Test _build_crosshair creates correct lines and center point."""
        scene = ReticleScene.__new__(ReticleScene)
        scene._aspect_ratio = 1.777
        scene.scene_view = Mock()
        scene.scene_view.aspect_ratio_policy = mock_scene.AspectRatioPolicy.PRESERVE_ASPECT_VERTICAL

        scene._build_crosshair()

        # Verify 4 lines and 1 point
        self.assertEqual(mock_scene.Line.call_count, 4)
        mock_scene.Points.assert_called_once()

    @patch("omni.sample.reticle.views.scene")
    def test_build_safe_rect(self, mock_scene):
        """Test _build_safe_rect creates rectangle."""
        scene = ReticleScene.__new__(ReticleScene)
        scene._aspect_ratio = 1.777
        scene.scene_view = Mock()
        scene.scene_view.aspect_ratio_policy = mock_scene.AspectRatioPolicy.PRESERVE_ASPECT_VERTICAL

        test_color = cl(1.0, 0.0, 0.0)
        scene._build_safe_rect(0.9, color=test_color)

        # Verify rectangle was created
        mock_scene.Rectangle.assert_called_once()
        call_kwargs = mock_scene.Rectangle.call_args[1]
        self.assertTrue(call_kwargs["wireframe"])

    @patch("omni.sample.reticle.views.scene")
    def test_build_letterbox(self, mock_scene):
        """Test _build_letterbox creates letterbox bars."""
        scene = ReticleScene.__new__(ReticleScene)
        scene._aspect_ratio = 1.777
        scene._model = ReticleModel()
        scene._model.letterbox_ratio.set_value(2.35)
        scene.scene_view = Mock()
        scene.scene_view.aspect_ratio_policy = mock_scene.AspectRatioPolicy.PRESERVE_ASPECT_VERTICAL

        # Mock Transform context
        mock_scene.Transform.return_value.__enter__ = Mock(return_value=Mock())
        mock_scene.Transform.return_value.__exit__ = Mock(return_value=None)

        scene._build_letterbox()

        # Verify rectangles were created (2 bars)
        self.assertGreaterEqual(mock_scene.Rectangle.call_count, 2)


class TestReticleMenu(omni.kit.test.AsyncTestCase):
    """Unit tests for ReticleMenu class."""

    async def setUp(self):
        """Set up test fixtures before each test method."""
        self.model = ReticleModel()

    async def tearDown(self):
        """Clean up after each test method."""
        self.model._callbacks.clear()

    @patch("omni.sample.reticle.views.ui.Button")
    def test_menu_initialization(self, mock_button):
        """Test ReticleMenu initializes correctly."""
        menu = ReticleMenu(self.model)

        # Verify model is stored
        self.assertEqual(menu.model, self.model)

        # Verify button was created
        mock_button.assert_called_once()
        call_kwargs = mock_button.call_args[1]
        self.assertEqual(call_kwargs["width"], 120)

    @patch("omni.sample.reticle.views.ui.Button")
    def test_menu_destroy(self, mock_button):
        """Test ReticleMenu cleanup on destroy."""
        mock_button_instance = Mock()
        mock_button_instance.destroy = Mock()
        mock_button.return_value = mock_button_instance

        menu = ReticleMenu(self.model)
        menu.destroy()

        # Verify button was destroyed
        mock_button_instance.destroy.assert_called_once()
        self.assertIsNone(menu.button)

    @patch("omni.sample.reticle.views.ui.Button")
    def test_on_group_check_changed(self, mock_button):
        """Test on_group_check_changed enables/disables groups correctly."""
        menu = ReticleMenu(self.model)

        mock_group = Mock()

        # Test enabling
        self.model.action_safe_enabled.set_value(True)
        menu.on_group_check_changed(mock_group, self.model.action_safe_enabled)
        self.assertTrue(mock_group.enabled)

        # Test disabling
        self.model.action_safe_enabled.set_value(False)
        menu.on_group_check_changed(mock_group, self.model.action_safe_enabled)
        self.assertFalse(mock_group.enabled)

    @patch("omni.sample.reticle.views.ui.Button")
    def test_on_composition_mode_changed(self, mock_button):
        """Test on_composition_mode_changed updates button states correctly."""
        menu = ReticleMenu(self.model)

        # Create mock buttons
        menu.comp_off_button = Mock()
        menu.comp_thirds_button = Mock()
        menu.comp_quad_button = Mock()
        menu.comp_crosshair_button = Mock()

        # Test setting to THIRDS
        menu.on_composition_mode_changed(constants.CompositionGuidelines.THIRDS)

        # Verify model was updated
        self.assertEqual(self.model.composition_mode.as_int, constants.CompositionGuidelines.THIRDS)

        # Verify only THIRDS button is checked
        self.assertFalse(menu.comp_off_button.checked)
        self.assertTrue(menu.comp_thirds_button.checked)
        self.assertFalse(menu.comp_quad_button.checked)
        self.assertFalse(menu.comp_crosshair_button.checked)

    @patch("omni.sample.reticle.views.ui")
    def test_show_reticle_menu_creates_menu(self, mock_ui):
        """Test show_reticle_menu creates and displays menu."""
        mock_menu_instance = MagicMock()
        mock_menu_instance.clear = Mock()
        mock_menu_instance.show_at = Mock()
        mock_menu_instance.width = 400
        mock_menu_instance.height = 200
        mock_menu_instance.__enter__ = Mock(return_value=mock_menu_instance)
        mock_menu_instance.__exit__ = Mock(return_value=None)
        mock_ui.Menu.return_value = mock_menu_instance

        # Mock all UI components
        mock_ui.Frame.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.Frame.return_value.__exit__ = Mock(return_value=None)
        mock_ui.HStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.HStack.return_value.__exit__ = Mock(return_value=None)
        mock_ui.VStack.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.VStack.return_value.__exit__ = Mock(return_value=None)
        mock_ui.VGrid.return_value.__enter__ = Mock(return_value=Mock())
        mock_ui.VGrid.return_value.__exit__ = Mock(return_value=None)

        menu = ReticleMenu(self.model)
        menu.show_reticle_menu(100, 100, 0, 0)

        # Verify menu was created and shown
        mock_ui.Menu.assert_called_once()
        mock_menu_instance.clear.assert_called_once()
        mock_menu_instance.show_at.assert_called_once()

    @patch("omni.sample.reticle.views.ui.Button")
    def test_composition_modes_all_settable(self, mock_button):
        """Test all composition modes can be set via on_composition_mode_changed."""
        menu = ReticleMenu(self.model)

        menu.comp_off_button = Mock()
        menu.comp_thirds_button = Mock()
        menu.comp_quad_button = Mock()
        menu.comp_crosshair_button = Mock()

        modes = [
            constants.CompositionGuidelines.OFF,
            constants.CompositionGuidelines.THIRDS,
            constants.CompositionGuidelines.QUAD,
            constants.CompositionGuidelines.CROSSHAIR,
        ]

        for mode in modes:
            menu.on_composition_mode_changed(mode)
            self.assertEqual(self.model.composition_mode.as_int, mode)
