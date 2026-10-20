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

from ..utils import *


class TestUtils(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        pass

    async def tearDown(self):
        pass

    async def test_editor_check(self):
        checker = EditorCheck()
        self.assertIsNotNone(checker)
        self.assertFalse(checker.has_editor)

    async def test_uniform_absolute_path(self):
        # create prim first
        self.assertEqual(uniform_absolute_path("/test/obj"), "/test/obj")
        self.assertEqual(uniform_absolute_path("c:/test/obj"), "C:/test/obj")
        self.assertEqual(uniform_absolute_path("omniverse://test/obj\\"), "omniverse://test/obj/")
        self.assertEqual(uniform_absolute_path("\\test\\obj"), "/test/obj")
        self.assertEqual(uniform_absolute_path("c:\\test\\obj"), "C:/test/obj")
        self.assertEqual(uniform_absolute_path("omniverse:\\test\\obj\\"), "omniverse:/test/obj/")
        self.assertEqual(uniform_absolute_path("omniverse:\\test\\..\\obj\\"), "omniverse:/obj/")
