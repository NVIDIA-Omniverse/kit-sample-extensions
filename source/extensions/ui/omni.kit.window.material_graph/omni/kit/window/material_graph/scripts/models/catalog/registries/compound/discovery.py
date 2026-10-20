"""Compound-file discovery utilities for scanning and loading nodegraph assets."""

from pathlib import Path
from typing import Dict, Iterable, List, Optional

import omni.client
from pxr import Usd, UsdShade

from .....config.logging import logger
from ...items.compound import CompoundItem
from .parsing import _extract_compound_data
from .source import CompoundSource

_COMPOUND_EXTS = (".usd", ".usda", ".usdc")


def _iter_compound_files(path: str) -> Iterable[str]:
    """Execute iter compound files behavior for material graph workflows."""

    resolved = path
    if not resolved:
        return []
    result, entries = omni.client.list(resolved)
    if result == omni.client.Result.OK:
        for entry in entries:
            if entry.flags & int(omni.client.ItemFlags.READABLE_FILE):
                if entry.relative_path.lower().endswith(_COMPOUND_EXTS):
                    yield omni.client.combine_urls(resolved.rstrip("/") + "/", entry.relative_path)
        return []
    try:
        path_obj = Path(resolved)
        if not path_obj.exists() or not path_obj.is_dir():
            return []
        for entry in path_obj.iterdir():
            if entry.is_file() and entry.name.lower().endswith(_COMPOUND_EXTS):
                yield str(entry)
    except OSError as exc:
        logger.debug("compound file iteration failed for '%s': %s", resolved, exc)
        return []


def _open_stage(path: str) -> Optional[Usd.Stage]:
    """Execute open stage behavior for material graph workflows."""

    try:
        return Usd.Stage.Open(path)
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
        logger.warning("failed to open compound '%s': %s", path, exc)
        return None


def _compound_key(source_asset: str, identifier: str) -> str:
    """Execute compound key behavior for material graph workflows."""

    return f"{source_asset}::{identifier}"


def _load_compounds(path: str, metadata: Dict[str, Dict[str, str]]) -> List[CompoundItem]:
    """Execute load compounds behavior for material graph workflows."""

    stage = _open_stage(path)
    if not stage:
        return []
    items: List[CompoundItem] = []
    it = iter(Usd.PrimRange.Stage(stage, Usd.PrimIsLoaded & ~Usd.PrimIsAbstract))
    for prim in it:
        if prim.IsA(UsdShade.NodeGraph) or prim.IsA(UsdShade.Shader):
            data: CompoundSource = _extract_compound_data(prim, path)
            key = _compound_key(data.source_asset, data.identifier)
            overrides = metadata.get(key, {})
            display_name = overrides.get("name") or data.display_name
            group = overrides.get("group", "")
            items.append(
                CompoundItem(
                    name=display_name,
                    info=data.description,
                    icon=data.icon,
                    tooltip=data.description,
                    source_asset=data.source_asset,
                    identifier=data.identifier,
                    context_visibility=list(data.context_visibility),
                    group=group,
                )
            )
            it.PruneChildren()
    return items
