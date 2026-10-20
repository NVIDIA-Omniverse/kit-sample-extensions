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
import omni.usd

from ..viewusd import ViewUsd


class TestViewUsd(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self.usd_context = omni.usd.get_context()
        await omni.usd.get_context().new_stage_async()
        self._viewusd = ViewUsd()

    async def tearDown(self):
        self._viewusd = None
        if omni.usd.get_context().get_stage():
            await omni.usd.get_context().close_stage_async()

    async def test_get_prim(self):
        path = "/test/obj"

        self.assertFalse(self._viewusd.get_prim(path, create=False).IsValid())
        prim = self._viewusd.get_prim(path)
        self.assertEqual(prim.GetPath(), path)
        self.assertIsNone(self._viewusd.get_prim("", create=False))

    async def test_remove_prim(self):
        # create prim first
        path = "/test/obj"
        prim = self._viewusd.get_prim(path)
        self.assertEqual(prim.GetPath(), path)

        # remove prim
        self._viewusd.remove_prim(path)
        stage = self.usd_context.get_stage()
        self.assertFalse(prim.IsValid())

        # make sure parent prim is not removed
        self.assertTrue(stage.GetPrimAtPath("/test").IsValid())

    async def test_move_prim(self):
        orig_path = "/test/obj"
        new_path = "/new/obj"

        orig_prim = self._viewusd.get_prim(orig_path)
        self.assertTrue(orig_prim.IsValid())
        self.assertFalse(self._viewusd.get_prim(new_path, create=False).IsValid())

        self._viewusd.move_prim(orig_path, new_path)
        new_prim = self._viewusd.get_prim(new_path, create=False)
        self.assertTrue(new_prim.IsValid())

    async def test_prim_attributes(self):
        path = "/test/obj"

        prim = self._viewusd.get_prim(path)

        # get prim attributes default
        default = "Dummy"
        attr_name = "testAttr"
        attr_value = "test"

        self.assertEqual(default, self._viewusd.get_prim_attribute(prim, "nonExistentAttr", default))

        # create prim attributes
        self._viewusd.set_prim_attribute(prim, attr_name, attr_value, create=False)
        self.assertEqual(default, self._viewusd.get_prim_attribute(prim, attr_name, default))
        self._viewusd.set_prim_attribute(prim, attr_name, attr_value, create=True)
        self.assertEqual(attr_value, self._viewusd.get_prim_attribute(prim, attr_name, default))

        # set prim attributes
        new_value = "new val"
        self._viewusd.set_prim_attribute(prim, attr_name, new_value, create=False)
        self.assertEqual(new_value, self._viewusd.get_prim_attribute(prim, attr_name, default))
