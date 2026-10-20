# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""MaterialX identifier upgrades for UsdShade material networks.

This package converts the active UsdShade material network into an in-memory
MaterialX document, asks the MaterialX library supplied by the running Kit to
upgrade that document, and reports identifier changes without mutating USD.

Only the result contracts and the live-prim entry point are exposed here. The
network traversal, document construction, and SDR compatibility details remain
private implementation modules.
"""

from .models import IdentifierChange, UpgradeResult
from .upgrade import upgrade_materialx_identifiers

__all__ = [
    "IdentifierChange",
    "UpgradeResult",
    "upgrade_materialx_identifiers",
]
