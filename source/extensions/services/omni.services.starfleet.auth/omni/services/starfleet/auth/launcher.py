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
import typing

import carb
from omni.services.client import AsyncClient
from omni.services.transport.client.base import exceptions as _cli_exceptions

from .exceptions import LauncherUnavailableError, StarfleetTokenExchangeError


async def get_starfleet_tokens() -> typing.Tuple[str, str]:
    settings = carb.settings.get_settings()
    launcher_url = settings.get("exts/omni.services.starfleet_auth/launcher_url")
    client = AsyncClient(launcher_url)

    try:
        data = await asyncio.wait_for(client.auth.get(), timeout=5)
    except _cli_exceptions.BaseServiceError as exc:
        raise LauncherUnavailableError from exc
    except asyncio.TimeoutError as exc:
        raise LauncherUnavailableError("Timed out") from exc

    id_token = data.get("idToken")
    access_token = data.get("accessToken")

    if id_token is None:
        raise StarfleetTokenExchangeError("Could not find id token in response from launcher")

    if access_token is None:
        raise StarfleetTokenExchangeError("Could not find access token in response from launcher")

    return id_token, access_token
