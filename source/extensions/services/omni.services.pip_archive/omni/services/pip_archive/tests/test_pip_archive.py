# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.kit.pipapi
import omni.kit.test


class TestPipArchive(omni.kit.test.AsyncTestCase):
    async def test_pip_archive(self):
        # Take one of packages from deps/pip.toml, it should be prebundled and available without need for going into online index
        omni.kit.pipapi.install("prometheus_client", version="0.12.0", use_online_index=False)
        import prometheus_client

        self.assertIsNotNone(prometheus_client)
