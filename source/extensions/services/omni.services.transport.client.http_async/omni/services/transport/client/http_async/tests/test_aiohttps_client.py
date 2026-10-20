# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import contextlib

import carb
import omni.kit.test
import omni.services.client as _client


class _MockCall:

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = sorted(kwargs.items())

    async def text(self):
        return (self.args, self.kwargs)


class FakeSession:

    async def __aenter__(self):
        yield self

    async def __aexit__(self):
        pass

    @contextlib.asynccontextmanager
    async def get(self, *args, **kwargs):
        yield _MockCall(*args, **kwargs)

    @contextlib.asynccontextmanager
    async def post(self, *args, **kwargs):
        yield _MockCall(*args, **kwargs)


class TesstaioHTTPS_SkipVerify_Test(omni.kit.test.AsyncTestCase):
    async def setUp(self):

        settings = carb.settings.get_settings_interface()
        settings.set("exts/omni.services.transport.client.http_async/https/ssl_skip_verify", True)

        self._client = _client.AsyncClient("https://localhost:8000", persist_connections=True)
        await self._client._transport._session.close()
        self._client._transport._session = FakeSession()

    async def test_ssl_skip_verify_get(self):
        result = (("https://localhost:8000/ping",), sorted({"headers": {}, "params": {}, "ssl_context": False}.items()))

        res = await self._client.ping.get()
        self.assertEqual(res, result)

    async def test_ssl_skip_verify_post(self):
        result = (
            ("https://localhost:8000/ping",),
            sorted({"headers": {}, "ssl_context": False, "json": {"foo": "bar"}}.items()),
        )

        res = await self._client.ping.post(foo="bar")
        self.assertEqual(res, result)
