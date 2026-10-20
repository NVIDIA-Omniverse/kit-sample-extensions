# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.kit.test
from omni.sample.reticle import constants
from omni.sample.reticle.models import ReticleModel


class TestReticleModel(omni.kit.test.AsyncTestCase):
    """Unit tests for ReticleModel class."""

    async def setUp(self):
        """Set up test fixtures before each test method."""
        self.model = ReticleModel()

    async def tearDown(self):
        """Clean up after each test method."""
        # Clear any registered callbacks
        self.model._callbacks.clear()

    def test_model_initialization(self):
        """Test that ReticleModel initializes with correct default values."""
        model = ReticleModel()

        # Test composition mode
        self.assertEqual(model.composition_mode.as_int, constants.DEFAULT_COMPOSITION_MODE)

        # Test safe area defaults
        self.assertFalse(model.action_safe_enabled.as_bool)
        self.assertEqual(model.action_safe_percentage.as_float, constants.DEFAULT_ACTION_SAFE_PERCENTAGE)
        self.assertFalse(model.title_safe_enabled.as_bool)
        self.assertEqual(model.title_safe_percentage.as_float, constants.DEFAULT_TITLE_SAFE_PERCENTAGE)

        # Test letterbox defaults
        self.assertFalse(model.letterbox_enabled.as_bool)
        self.assertEqual(model.letterbox_ratio.as_float, constants.DEFAULT_LETTERBOX_RATIO)

    def test_composition_mode_changes(self):
        """Test composition mode value changes."""
        # Test setting different composition modes
        self.model.composition_mode.set_value(constants.CompositionGuidelines.THIRDS)
        self.assertEqual(self.model.composition_mode.as_int, constants.CompositionGuidelines.THIRDS)

        self.model.composition_mode.set_value(constants.CompositionGuidelines.CROSSHAIR)
        self.assertEqual(self.model.composition_mode.as_int, constants.CompositionGuidelines.CROSSHAIR)

    def test_safe_area_functionality(self):
        """Test safe area enable/disable and percentage changes."""
        # Test action safe area
        self.model.action_safe_enabled.set_value(True)
        self.assertTrue(self.model.action_safe_enabled.as_bool)

        self.model.action_safe_percentage.set_value(95.0)
        self.assertEqual(self.model.action_safe_percentage.as_float, 95.0)

        # Test title safe area
        self.model.title_safe_enabled.set_value(True)
        self.assertTrue(self.model.title_safe_enabled.as_bool)

        self.model.title_safe_percentage.set_value(88.0)
        self.assertEqual(self.model.title_safe_percentage.as_float, 88.0)

    def test_letterbox_functionality(self):
        """Test letterbox enable/disable and ratio changes."""
        self.model.letterbox_enabled.set_value(True)
        self.assertTrue(self.model.letterbox_enabled.as_bool)

        self.model.letterbox_ratio.set_value(2.4)
        self.assertEqual(self.model.letterbox_ratio.as_float, 2.4)

    def test_callback_registration(self):
        """Test callback registration and triggering."""
        callback_count = 0

        def test_callback():
            nonlocal callback_count
            callback_count += 1

        # Register callback
        self.model.add_reticle_changed_fn(test_callback)

        # Trigger changes
        self.model.composition_mode.set_value(constants.CompositionGuidelines.THIRDS)
        self.assertEqual(callback_count, 1)

        self.model.action_safe_enabled.set_value(True)
        self.assertEqual(callback_count, 2)

    def test_multiple_callbacks(self):
        """Test multiple callback registration."""
        callback1_count = 0
        callback2_count = 0

        def callback1():
            nonlocal callback1_count
            callback1_count += 1

        def callback2():
            nonlocal callback2_count
            callback2_count += 1

        # Register multiple callbacks
        self.model.add_reticle_changed_fn(callback1)
        self.model.add_reticle_changed_fn(callback2)

        # Trigger change
        self.model.letterbox_enabled.set_value(True)

        # Both callbacks should be called
        self.assertEqual(callback1_count, 1)
        self.assertEqual(callback2_count, 1)

    def test_custom_safe_area(self):
        """Test custom safe area enable/disable and percentage changes."""
        # Test custom safe area
        self.model.custom_safe_enabled.set_value(True)
        self.assertTrue(self.model.custom_safe_enabled.as_bool)

        self.model.custom_safe_percentage.set_value(85.0)
        self.assertEqual(self.model.custom_safe_percentage.as_float, 85.0)

    def test_letterbox_ratio_boundaries(self):
        """Test letterbox ratio with boundary values."""
        # Test minimum value
        self.model.letterbox_ratio.set_value(0.001)
        self.assertEqual(self.model.letterbox_ratio.as_float, 0.001)

        # Test larger values
        self.model.letterbox_ratio.set_value(3.5)
        self.assertEqual(self.model.letterbox_ratio.as_float, 3.5)

    def test_safe_area_percentage_boundaries(self):
        """Test safe area percentages at boundaries."""
        # Test minimum
        self.model.action_safe_percentage.set_value(0.0)
        self.assertEqual(self.model.action_safe_percentage.as_float, 0.0)

        # Test maximum
        self.model.action_safe_percentage.set_value(100.0)
        self.assertEqual(self.model.action_safe_percentage.as_float, 100.0)

    def test_all_composition_modes(self):
        """Test setting all composition mode values."""
        modes = [
            constants.CompositionGuidelines.OFF,
            constants.CompositionGuidelines.THIRDS,
            constants.CompositionGuidelines.QUAD,
            constants.CompositionGuidelines.CROSSHAIR,
        ]

        for mode in modes:
            self.model.composition_mode.set_value(mode)
            self.assertEqual(self.model.composition_mode.as_int, mode)

    def test_multiple_model_changes(self):
        """Test multiple rapid model changes."""
        callback_count = 0

        def test_callback():
            nonlocal callback_count
            callback_count += 1

        self.model.add_reticle_changed_fn(test_callback)

        # Make multiple changes
        self.model.composition_mode.set_value(constants.CompositionGuidelines.THIRDS)
        self.model.action_safe_enabled.set_value(True)
        self.model.title_safe_enabled.set_value(True)
        self.model.letterbox_enabled.set_value(True)

        # Should have been called 4 times
        self.assertEqual(callback_count, 4)
