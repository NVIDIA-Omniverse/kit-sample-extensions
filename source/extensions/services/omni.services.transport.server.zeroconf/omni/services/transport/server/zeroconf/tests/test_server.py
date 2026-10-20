# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import platform
from unittest import skipUnless

import omni.kit.test
from omni.services.transport.server.zeroconf import ZeroConf


class TestZeroConfServer(omni.kit.test.AsyncTestCase):
    testServiceName = "test._udp.local."

    async def setUp(self) -> None:
        self._server_extension = ZeroConf()
        self._server_extension.on_startup()

    async def tearDown(self) -> None:
        self._server_extension.on_shutdown()
        self._server_extension = None

    @skipUnless(platform.system().lower() == "windows", "Issues with zeroconf so files changing")
    async def test_server_creation(self):
        loop = asyncio.get_running_loop()

        def addTestServer():
            self._server_extension.add(TestZeroConfServer.testServiceName, 123)

        result = await loop.run_in_executor(None, addTestServer)
        print("test_server_creation", result)

    @skipUnless(platform.system().lower() == "windows", "Issues with zeroconf so files changing")
    async def test_server_destruction(self):
        loop = asyncio.get_running_loop()

        def removeTestServer():
            self._server_extension.remove(TestZeroConfServer.testServiceName, 123)

        result = await loop.run_in_executor(None, removeTestServer)
        print("test_server_destruction", result)

    async def test_ip_fetch(self):
        loop = asyncio.get_running_loop()
        for ip in ZeroConf.ipAddresses():
            print("test_ip_fetch: ", '"%s"' % ip)
            self.assertFalse(ip == "")
