# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import re

import omni.client
import omni.ext
from carb import log_info, log_warn
from idl.connection.transport.ws import WebSocketClient
from omniverse_auth import client as auth_client
from omniverse_auth import data as auth_data

from .exceptions import LauncherUnavailableError, StarfleetTokenExchangeError
from .launcher import get_starfleet_tokens


class ServiceStarfleetAuthExtension(omni.ext.IExt):
    NUCLEUS_CLOUD_RE = re.compile(r"^.*\.cne\.ngc\.nvidia\.com$")

    def __init__(self):
        super().__init__()
        self._sub_auto_auth = None

    def on_startup(self):
        self._sub_auto_auth = omni.client.register_authorize_callback(self.authenticate)

    def on_shutdown(self):
        self._sub_auto_auth = None

    def authenticate(self, omniverse_uri: str) -> str:
        url_parts = omni.client.break_url(omniverse_uri)
        if url_parts.scheme != "omniverse":
            return None

        if self.NUCLEUS_CLOUD_RE.match(url_parts.host) is None:
            return None

        log_info(f"Attempting to auto-login to nucleus cloud {url_parts.host} with Starfleet")
        loop = asyncio.new_event_loop()
        try:
            auth_coroutine = self.authenticate_async(url_parts.host)
            access_token = loop.run_until_complete(auth_coroutine)
            log_info(f"Successfully logged into nucleus cloud {url_parts.host} with Starfleet")
            return access_token
        except Exception as exc:
            log_warn(f"Unable to auto authenticate to Nucleus Cloud Instance {url_parts.host} : {exc}")
            return None
        finally:
            loop.close()

    async def authenticate_async(self, nucleus_cloud_host: str) -> str:
        try:
            starfleet_id_token, starfleet_access_token = await get_starfleet_tokens()
        except Exception as e:
            raise e

        ws = WebSocketClient(f"wss://{nucleus_cloud_host}/omni/auth")
        await ws.prepare()
        try:
            ssoClient = auth_client.SSO(ws)
            result = await ssoClient.auth(type="Starfleet", params={"id_token": starfleet_id_token})
            assert result.status == auth_data.AuthStatus.OK
            return result.access_token
        except Exception as e:
            raise StarfleetTokenExchangeError from e
        finally:
            await ws.close()

        return None
