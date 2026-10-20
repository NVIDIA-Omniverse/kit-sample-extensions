# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.services.usd
from omni.services.core.tests import base


class TestUsdService(base.BaseServiceTest):
    async def test_get_open_stage(self):

        result, status = await self._get_request_async("/kit/usd/stage")

        assert status == 200
        assert result == {"file_uri": ""}

    # async def test_open_stage(self):
    #    stage = "omniverse://ov-sandbox.nvidia.com/Users/"
    #    result, status = await self._post_request_async("/kit/usd/stage", stage)
    #    assert status == 200

    #    result, status = await self._get_request_async("/kit/usd/stage")

    #    assert result == {'file_uri': stage}
