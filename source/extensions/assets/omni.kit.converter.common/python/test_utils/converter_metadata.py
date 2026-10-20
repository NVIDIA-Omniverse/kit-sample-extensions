# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path
from typing import List

import omni.client
import omni.kit.test
from pxr import Usd


class ConverterMetadata(omni.kit.test.AsyncTestCase):
    def _create_delegate(self, delegate, filter_data):
        """
        Create and return a delegate that supports the filter data
        """
        filter_name = filter_data.name
        filter_regexes = filter_data.filter_regexes
        filter_descriptions = filter_data.filter_descriptions
        new_delegate = delegate(filter_name, filter_regexes, filter_descriptions)
        self.assertIsNotNone(new_delegate)
        return new_delegate

    async def _check_metadata(self, usd_path: Path, creator_components: List[str]):
        """
        Check for version data in in the custom layer data
        """
        self.assertTrue(usd_path.is_file(), f"Expected output file missing: {usd_path}.")
        stage = Usd.Stage.Open(str(usd_path))
        layer = stage.GetRootLayer()
        self.assertTrue(layer.HasCustomLayerData())
        custom_layer_data = layer.customLayerData
        self.assertTrue("creator" in custom_layer_data)
        for creator_component in creator_components:
            self.assertTrue(creator_component in custom_layer_data["creator"])

        # clean up by releasing the stage ref and deleting the usd file
        stage = None
        ret: omni.client.Result = await omni.client.delete_async(str(usd_path))
        self.assertEqual(ret, omni.client.Result.OK, f"Failed to delete {usd_path}, was handle released?")
