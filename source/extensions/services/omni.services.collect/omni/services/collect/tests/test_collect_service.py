# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from unittest.mock import patch

import omni.kit.test
import omni.services.collect
from omni.services.client import AsyncClient
from omni.services.core import main


class Test_Base(omni.kit.test.AsyncTestCase):

    async def test_simple_collect(self):
        """Test that a call to the collect service returns finished when successful."""
        client = AsyncClient("local://", app=main.get_app())

        async def mock_collect_call(*args, **kwargs):
            pass

        with patch("omni.kit.usd.collect.collector.Collector.collect", wraps=mock_collect_call) as mock_generate:
            res = await client.collect.process(
                usd_path="/foo",
                collect_dir="/bar",
            )
            mock_generate.assert_called_once()
            self.assertEqual({"status": "finished"}, res)
