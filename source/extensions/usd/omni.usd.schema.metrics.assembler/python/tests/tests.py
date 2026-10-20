# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import os

import omni.kit.test
from pxr import Plug, Sdf, Tf, Usd


class MetricsAssemblerSchemaTests(omni.kit.test.AsyncTestCaseFailOnLogError):
    async def setUp(self):
        pass

    async def tearDown(self):
        pass

    async def test_plugin_load(self):
        asset_resolver_plugin = Plug.Registry().GetPluginWithName("MetricsAssembler")
        self.assertTrue(asset_resolver_plugin != None)

    async def test_metrics_assembler_file_format(self):
        all_formats = Sdf.FileFormat.FindAllFileFormatExtensions()

        # https://github.com/PixarAnimationStudios/OpenUSD/commit/124967b943157a93c9062aa8a1d6888820ff3eba
        # change to keep registered extensions as lower case
        # Id remains the same, but any query by extension needs lower case
        self.assertTrue("metricsassembler" in all_formats)
        file_format = Sdf.FileFormat.FindById("metricsAssembler")
        self.assertTrue(file_format)
        file_format = Sdf.FileFormat.FindByExtension("metricsassembler")
        self.assertTrue(file_format)

    async def test_load_metrics_assembler_layer(self):
        data_folder = os.path.abspath(os.path.normpath(os.path.join(__file__, "../../../../../data/tests/")))
        data_folder = data_folder.replace("\\", "/") + "/"

        stage = Usd.Stage.Open(data_folder + "test.usda")

        # check we have all layers
        layers = stage.GetLayerStack()

        self.assertTrue(len(layers) == 3)

        metrics_layer = layers[2]
        print(metrics_layer.identifier)
        self.assertTrue("metrics:" in metrics_layer.identifier)
