# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
"""Top-level integration surface for the Material Graph extension.

Purpose: This package intentionally exposes only the stable integration API
from ``scripts.api`` and a small set of extension helper functions from
``scripts.extension``. Internal command wrappers and implementation packages
remain importable through their own modules but are not part of the default
public API contract.

Architectural role: This is the extension's public facade; external consumers
should import from here for versioned API access and extension lifecycle hooks.

Typical consumers: Other extensions that integrate with Material Graph (e.g.,
registering context-menu items, reading plugin settings), extension bootstrap
code, and tests that exercise the public API.
"""

from . import api
from .api import *  # noqa: F403
from .extension import (
    GraphExtension,
    add_mdl_catalog_module,
    get_extension,
    get_graph_window,
    remove_mdl_catalog_module,
)

__all__ = sorted(
    list(api.__all__)
    + [
        "GraphExtension",
        "add_mdl_catalog_module",
        "get_extension",
        "get_graph_window",
        "remove_mdl_catalog_module",
    ]
)
