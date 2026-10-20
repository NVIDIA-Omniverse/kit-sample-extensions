# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
#
from pathlib import Path

import omni.kit.app
import omni.kit.converter.gsplat as converter
import omni.kit.test

_EXT_MODULE = "omni.kit.converter.gsplat"


def get_test_data_dir() -> Path:
    """Return the ``data/tests`` directory shipped with this extension."""
    ext_manager = omni.kit.app.get_app().get_extension_manager()
    ext_id = ext_manager.get_enabled_extension_id(_EXT_MODULE)
    return Path(ext_manager.get_extension_path(ext_id)) / "data" / "tests"


class TestBasicImports(omni.kit.test.AsyncTestCaseFailOnLogError):
    async def setUp(self):
        pass

    async def tearDown(self):
        pass

    async def test_module_imports(self):
        """Verify all public symbols are importable."""
        self.assertIsNotNone(converter.ThreeDGSConverterExtension)
        self.assertIsNotNone(converter.GaussianSplatData)
        self.assertIsNotNone(converter.read_ply)
        self.assertIsNotNone(converter.read_ply_raw)
        self.assertIsNotNone(converter.read_spz)
        self.assertIsNotNone(converter.write_gaussian_splat_usd)
        self.assertIsNotNone(converter.write_ply)

    async def test_get_instance(self):
        """Verify the extension instance is accessible."""
        instance = converter.get_instance()
        self.assertIsNotNone(instance)
        self.assertIsInstance(instance, converter.ThreeDGSConverterExtension)
