# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os
import uuid
from contextlib import asynccontextmanager, nullcontext

import omni.client
from pxr import Sdf, Usd, UsdUtils


@asynccontextmanager
async def nucleus_test_folder(test, scope):
    """Use the existing test server and clean only this run's unique directory."""
    folder = f"omniverse://kit-test-content.ov.nvidia.com/Projects/Converters_Test_Models/{scope}/{uuid.uuid4().hex}"
    authentication = nullcontext()
    if os.environ.get("OMNI_TEST_HOST") is not None:
        authentication = omni.client.register_authentication_callback(
            lambda prefix: (os.environ.get("OMNI_TEST_USER"), os.environ.get("OMNI_TEST_PASS"))
        )
    with authentication:
        result = await omni.client.create_folder_async(folder)
        test.assertEqual(result, omni.client.Result.OK, f"Cannot create Nucleus test folder: {folder}")
        try:
            yield folder
        finally:
            result = await omni.client.delete_async(folder)
            test.assertEqual(result, omni.client.Result.OK, f"Cannot clean Nucleus test folder: {folder}")


async def assert_nucleus_output(test, url, require_textures=False):
    """Reopen the uploaded USD and read every layer and asset from Nucleus."""
    stage = Usd.Stage.Open(url)
    test.assertTrue(stage, f"Cannot open uploaded USD: {url}")
    test.assertTrue(any(stage.Traverse()), f"Uploaded USD is empty: {url}")
    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(Sdf.AssetPath(url))
    test.assertFalse(unresolved, f"Unresolved output dependencies: {unresolved}")
    if require_textures:
        test.assertTrue(assets, "Textured fixture produced no image assets")
    paths = {url} | {layer.identifier for layer in layers} | set(assets)
    folder = url.rsplit("/", 1)[0] + "/"
    for path in paths:
        test.assertTrue(path.startswith(folder), f"Output still depends on a file outside its Nucleus folder: {path}")
        result, _, content = await omni.client.read_file_async(path)
        test.assertEqual(result, omni.client.Result.OK, f"Cannot read uploaded file: {path}")
        test.assertTrue(bytes(content), f"Uploaded file is empty: {path}")
