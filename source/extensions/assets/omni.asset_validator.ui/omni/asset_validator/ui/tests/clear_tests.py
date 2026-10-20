# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import omni.kit.test
from omni.asset_validator.ui import ApplicationModel, AssetResultsModel, ClearFn
from pxr import Usd


class ClearFnTest(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self.model = ApplicationModel.create()

    async def test_clear_fn_clears_results(self):
        test_asset = Usd.Stage.CreateInMemory()
        asset_results = AssetResultsModel(test_asset)
        self.model.results.add_asset(asset_results)

        self.assertEqual(len(self.model.results.assets), 1)

        clear_fn = ClearFn(model=self.model)
        await clear_fn.apply_async()

        self.assertIsNotNone(self.model.results)
        self.assertEqual(len(self.model.results.assets), 0)
