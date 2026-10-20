# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.kit.test
from omni.services.transport.client.base import consumer


class _DummyTransport(consumer.BaseConsumer):

    async def __call__(self, uri, *args, __method__=None, __headers__=None, __raw__=False, **kwargs):
        return (uri, args, __method__, __headers__, __raw__, kwargs)


class TestBase(omni.kit.test.AsyncTestCase):

    def test_simple_url(self):
        standin = consumer.BaseStandin("foo", _DummyTransport("test://", None, 1.0))
        self.assertEqual(standin.bar._root_uri, "foo/bar")

    def test_url_getattr(self):
        url_parts = ["bar", "tar", "far"]
        standin = consumer.BaseStandin("foo", _DummyTransport("test://", None, 1.0))
        for url_part in url_parts:
            standin = getattr(standin, url_part)

        self.assertEqual("foo/bar/tar/far", standin._root_uri)

    async def test_call(self):
        standin = consumer.BaseStandin("foo", _DummyTransport("test://", None, 1.0))
        res = await standin.bar.car("foo", arg=1)
        self.assertEqual(res, ("foo/bar/car", ("foo",), None, None, False, {"arg": 1}))
