# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
#
"""
omni.kit.converter.gsplat — registers Gaussian splat import with the Kit Asset Importer.

Conversion APIs live in ``usd_convert_gsplat``; there is no standalone converter window.
Use **File → Import** / **Convert to USD** when ``omni.kit.tool.asset_importer`` is enabled.
"""

from __future__ import annotations

import weakref
from typing import Optional

import omni.ext

from .asset_importer_filters import GSPLAT_ASSET_IMPORTER_FILTER_DATA
from .asset_importer_hooks import register_asset_importer_delegates, unregister_asset_importer_delegates
from .gsplat_asset_importer_delegate import GaussianSplatAssetImporterDelegate

_global_instance = None


class ThreeDGSConverterExtension(omni.ext.IExt):
    """Registers ``GaussianSplatAssetImporterDelegate`` with ``omni.kit.tool.asset_importer``."""

    def on_startup(self, ext_id: str) -> None:
        global _global_instance
        _global_instance = weakref.ref(self)
        self._ext_id = ext_id
        self._asset_importer_delegates: list = []
        register_asset_importer_delegates(
            GaussianSplatAssetImporterDelegate,
            GSPLAT_ASSET_IMPORTER_FILTER_DATA,
            self._asset_importer_delegates,
        )

    def on_shutdown(self) -> None:
        global _global_instance
        _global_instance = None
        unregister_asset_importer_delegates(self._asset_importer_delegates)


def get_instance() -> Optional[ThreeDGSConverterExtension]:
    global _global_instance
    if _global_instance and _global_instance():
        return _global_instance()
    return None
