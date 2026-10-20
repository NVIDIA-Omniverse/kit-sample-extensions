# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
import asyncio
import threading
from typing import Callable, Dict
from unittest.mock import patch

import omni.kit.test
from idl.connection.transport.ws import WebSocketClient
from omni.services.transport.client.base.exceptions import BaseServiceError
from omni.services.transport.client.http_async.consumer import HttpAsyncConsumer
from omniverse_auth import client as auth_client
from omniverse_auth import data as auth_data

from ..exceptions import LauncherUnavailableError, StarfleetTokenExchangeError
from ..extension import ServiceStarfleetAuthExtension


class MockAuth:
    def __init__(self, status: auth_data.AuthStatus = auth_data.AuthStatus.OK, access_token: str = None):
        self.status = status
        self.access_token = access_token


class ClientThread(threading.Thread):
    def __init__(self, auth_fn: Callable):
        super().__init__()
        self._auth_fn = auth_fn
        self.return_value = None

    def run(self):
        self.return_value = self._auth_fn()


class TestServicesStarfleetAuth(omni.kit.test.AsyncTestCase):
    """Testing omni.services.starfleet.auth extension."""

    async def setUp(self):
        self._test_url = "omniverse://7e592-2e=ef20=448c=aa94=615986b372aa.stg.cne.ngc.nvidia.com"
        self._auth_token = {
            "email": "user@nvidia.com",
            "username": "Joe User",
            "accessToken": "MOCK_ACCESS_TOKEN",
            "idToken": "MOCK_ID_TOKEN",
            "expires": "2027-03-22T22:33:55.160Z",
        }

    async def tearDown(self):
        pass

    async def _mock_http_consumer_call_impl(
        self, uri, *args, __method__=None, __headers__=None, __raw__=False, **kwargs
    ):
        """Mocks the core http call"""
        if __method__ == "get":
            if uri == "auth":
                # Get auth token
                return self._auth_token
        return {}

    async def _mock_http_consumer_call_returns_nothing(
        self, uri, *args, __method__=None, __headers__=None, __raw__=False, **kwargs
    ):
        return {}

    async def _mock_ws_client_prepare_impl(self):
        pass

    async def _mock_sso_client_auth_impl(self, type: str, params: Dict) -> MockAuth:
        resp = None
        if type == "Starfleet" and params.get("id_token") == self._auth_token["idToken"]:
            resp = MockAuth(access_token=self._auth_token["accessToken"])
        return resp

    async def test_authentication_async_succeeds(self):
        """Testing authentication succeeds"""
        under_test = ServiceStarfleetAuthExtension()
        with (
            patch.object(HttpAsyncConsumer, "__call__", side_effect=self._mock_http_consumer_call_impl),
            patch.object(WebSocketClient, "prepare", side_effect=self._mock_ws_client_prepare_impl),
            patch.object(auth_client.SSO, "auth", side_effect=self._mock_sso_client_auth_impl),
        ):
            result = await under_test.authenticate_async(self._test_url)
            self.assertEqual(result, self._auth_token["accessToken"])

    async def test_launcher_auth_fails(self):
        """Testing launcher error and raises a 'launcher unvaliable' error"""
        under_test = ServiceStarfleetAuthExtension()
        for exc in [BaseServiceError, asyncio.TimeoutError]:
            with patch.object(HttpAsyncConsumer, "__call__", side_effect=exc):
                try:
                    result = await under_test.authenticate_async(self._test_url)
                except Exception as e:
                    self.assertEqual(type(e), LauncherUnavailableError)
                else:
                    self.assertEqual(result, None)

    async def test_starfleet_token_exchange_error(self):
        """Testing starfleet token exchange error"""
        under_test = ServiceStarfleetAuthExtension()
        with patch.object(HttpAsyncConsumer, "__call__", side_effect=self._mock_http_consumer_call_returns_nothing):
            try:
                result = await under_test.authenticate_async(self._test_url)
            except Exception as e:
                self.assertEqual(type(e), StarfleetTokenExchangeError)
            else:
                self.assertEqual(result, None)

    async def test_authentication_from_separate_thread_succeeds(self):
        """Testing authentication called from a separate thread, which is typically what happens in practice"""
        under_test = ServiceStarfleetAuthExtension()
        with (
            patch.object(HttpAsyncConsumer, "__call__", side_effect=self._mock_http_consumer_call_impl),
            patch.object(WebSocketClient, "prepare", side_effect=self._mock_ws_client_prepare_impl),
            patch.object(auth_client.SSO, "auth", side_effect=self._mock_sso_client_auth_impl),
        ):
            client_thread = ClientThread(lambda: under_test.authenticate(self._test_url))
            client_thread.start()
            client_thread.join()
            result = client_thread.return_value
            self.assertEqual(result, self._auth_token["accessToken"])

    async def test_authentication_from_separate_thread_fails(self):
        """Testing authentication called from a separate thread, fails"""
        under_test = ServiceStarfleetAuthExtension()
        for exc in [BaseServiceError, asyncio.TimeoutError]:
            client_thread = ClientThread(lambda: under_test.authenticate(self._test_url))
            with patch.object(HttpAsyncConsumer, "__call__", side_effect=exc):
                client_thread.start()
                client_thread.join()
                result = client_thread.return_value
                self.assertEqual(result, None)
