# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
#
"""Register Asset Importer delegates — same flow as omni.kit.converter.common.cad_ext_base.ICadExtBase."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Type

import carb

if TYPE_CHECKING:
    from .asset_importer_filters import GsplatAssetImporterFilterData

try:
    import omni.kit.tool.asset_importer as ai
except ImportError:
    ai = None

__all__ = ["register_asset_importer_delegates", "unregister_asset_importer_delegates"]


def register_asset_importer_delegates(
    delegate_class: Type,
    filter_data_list: "List[GsplatAssetImporterFilterData]",
    holder: list,
) -> None:
    """Instantiate one delegate per filter row and register (matches ICadExtBase._register_importer)."""
    if ai is None:
        carb.log_warn("[3DGS] omni.kit.tool.asset_importer not importable; skipping asset importer registration.")
        return
    for fd in filter_data_list:
        delegate = delegate_class(fd.name, fd.filter_regexes, fd.filter_descriptions, fd.priority)
        ai.register_importer(delegate)
        holder.append(delegate)
        carb.log_info(f"[3DGS] Registered asset importer delegate: {fd.name}")


def unregister_asset_importer_delegates(holder: list) -> None:
    """Unregister and destroy each delegate (matches ICadExtBase._unregister_importer)."""
    if ai is None:
        holder.clear()
        return
    for delegate in holder:
        if delegate:
            delegate.destroy()
            ai.remove_importer(delegate)
    holder.clear()
