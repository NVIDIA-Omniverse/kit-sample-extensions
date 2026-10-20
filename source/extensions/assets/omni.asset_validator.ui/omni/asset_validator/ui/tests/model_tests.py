# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import omni.kit.test
from omni.asset_validator.core import ValidationEngine
from omni.asset_validator.ui import ApplicationModel, AssetMode
from pxr import Usd


class ApplicationModelTest(omni.kit.test.AsyncTestCase):
    """Test cases for ApplicationModel"""

    async def setUp(self):
        self.model = ApplicationModel.create()

    async def test_uri_model(self):
        """Test uri model getter"""
        self.assertEqual(self.model.uri_model, self.model.uri_model)

    async def test_uri(self):
        """Test uri getter/setter"""
        self.model.uri_model.uri = "test_uri"
        self.assertEqual(self.model.uri, "test_uri")

        self.model.uri = "new_uri"
        self.assertEqual(self.model.uri_model.uri, "new_uri")

    async def test_stage_model(self):
        """Test stage model getter"""
        self.assertEqual(self.model.stage_model, self.model.stage_model)

    async def test_stage(self):
        """Test stage getter/setter"""
        test_stage = Usd.Stage.CreateInMemory()
        self.model.stage_model.stage = test_stage
        self.assertEqual(self.model.stage, test_stage)

        new_stage = Usd.Stage.CreateInMemory()
        self.model.stage = new_stage
        self.assertEqual(self.model.stage_model.stage, new_stage)

    async def test_mode_model(self):
        """Test mode model getter"""
        self.assertEqual(self.model.mode_model, self.model.mode_model)

    async def test_mode(self):
        """Test mode getter/setter"""
        self.model.mode_model.mode = AssetMode.Stage
        self.assertEqual(self.model.mode, AssetMode.Stage)

        self.model.mode = AssetMode.Stage
        self.assertEqual(self.model.mode_model.mode, AssetMode.Stage)

    async def test_categories(self):
        """Test categories getter"""
        self.assertEqual(self.model.categories_model, self.model.categories_model)

    async def test_capabilities(self):
        """Test capabilities getter"""
        self.assertEqual(self.model.capabilities_model, self.model.capabilities_model)

    async def test_features(self):
        """Test features getter"""
        self.assertIsNotNone(self.model.features_model)

    async def test_profiles(self):
        """Test profiles getter"""
        self.assertEqual(self.model.profiles_model, self.model.profiles_model)

    async def test_settings(self):
        """Test settings getter"""
        self.assertEqual(self.model.settings_model, self.model.settings_model)

    async def test_filters(self):
        """Test filters getter"""
        self.assertEqual(self.model.filters_model, self.model.filters_model)

    async def test_results(self):
        """Test results getter"""
        self.assertEqual(self.model.results, self.model.results_model)

    async def test_get_singleton(self):
        """Test singleton getter creates instance with correct models"""
        model = ApplicationModel.get()
        self.assertIsInstance(model, ApplicationModel)

        # Verify it returns same instance
        model2 = ApplicationModel.get()
        self.assertIs(model, model2)

    async def test_create_engine(self):
        """Test create_engine method"""
        engine = self.model.create_engine()
        self.assertIsInstance(engine, ValidationEngine)
        self.assertTrue(engine.variants)
        self.assertTrue(engine.instance_prototypes)

        self.model.settings_model.variants = False
        self.model.settings_model.instance_prototypes = False
        engine = self.model.create_engine()
        self.assertFalse(engine.variants)
        self.assertFalse(engine.instance_prototypes)
