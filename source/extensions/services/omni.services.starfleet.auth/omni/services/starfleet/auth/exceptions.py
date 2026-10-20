# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
class BaseTokenExchangeError(Exception):
    """Base class to use for Token exchange errors"""


class StarfleetTokenExchangeError(BaseTokenExchangeError):
    """Raised when Starfleet token exchange error occurs"""

    def __init__(self, msg="Failed to exchange Starfleet session token", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)


class LauncherUnavailableError(Exception):
    """Raised when the Launcher is not running but needed for authentication"""
