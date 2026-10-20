"""Compound-file parsing helpers for extracting display metadata and UI attributes."""

from pathlib import Path
from typing import List, Optional

from pxr import Usd, UsdUI

from .....utils.context_visibility import get_context_visibility
from .source import CompoundSource


def _get_context_visibility(prim: Usd.Prim) -> Optional[List[str]]:
    """Execute get context visibility behavior for material graph workflows."""

    return get_context_visibility(prim)


def _extract_compound_data(prim: Usd.Prim, path: str) -> CompoundSource:
    """Execute extract compound data behavior for material graph workflows."""

    display_group_attr = prim.GetAttribute(UsdUI.Tokens.uiDisplayGroup)
    category = display_group_attr.Get() if display_group_attr else None
    if not category:
        category = "Material Graphs"
    description_attr = prim.GetAttribute(UsdUI.Tokens.uiDescription)
    description = description_attr.Get() if description_attr else None
    if not description:
        description = f"Compound from {Path(path).stem}"
    ui_order_attr = prim.GetAttribute("ui:order")
    ui_order = ui_order_attr.Get() if ui_order_attr else None
    display_name_attr = prim.GetAttribute(UsdUI.Tokens.uiDisplayName)
    display_name = display_name_attr.Get() if display_name_attr else prim.GetName()
    icon_attr = prim.GetAttribute(UsdUI.Tokens.uiNodegraphNodeIcon)
    icon = ""
    if icon_attr:
        asset_path = icon_attr.Get()
        if asset_path:
            resolved = asset_path.resolvedPath
            icon = resolved or asset_path.path
    context_visibility = _get_context_visibility(prim)
    if context_visibility is None:
        context_visibility = ["mdl"]
    return CompoundSource(
        source_asset=path,
        identifier=prim.GetPath().pathString,
        display_name=display_name,
        description=description,
        category=category,
        icon=icon,
        ui_order=ui_order,
        context_visibility=context_visibility,
    )
