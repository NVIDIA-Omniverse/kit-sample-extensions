# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Kit USD micro service."""

import omni.ext
import omni.services.core.main as main

from .services import usd as _usd


class UsdService(omni.ext.IExt):
    """
    Kit USD micro service.

    Simple USD micro service.
    Exposes simple USD commands that can be execute from internal and external processes.
    """

    def on_startup(self) -> None:
        main.register_router(_usd.router, prefix="/kit/usd", tags=["usd"])

    def on_shutdown(self) -> None:
        main.deregister_router(_usd.router, prefix="/kit/usd")
