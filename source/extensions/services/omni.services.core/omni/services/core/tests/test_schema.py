# SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from omni.services.core import main

from . import base


class SchemaTest(base.BaseServiceTest):

    async def test_controlport_status_hidden_in_schema(self):
        app = main.get_app()
        # schema = app.openapi()
        # paths = schema["paths"]

        # self.assertNotIn("/controlport/status", paths)

    async def test_status_in_schema(self):
        app = main.get_app()
        # schema = app.openapi()
        # paths = schema["paths"]

        # self.assertIn("/status", paths)
