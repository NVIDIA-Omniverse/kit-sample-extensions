# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Orchestration for MaterialX identifier upgrade checks."""

from typing import Any

import MaterialX as mx
from pxr import Usd, UsdShade

from .document import build_materialx_document, get_standard_libraries, resolved_identifier
from .models import IdentifierChange, MaterialXNodeSpec, NetworkNode, UpgradeResult
from .network import collect_network, get_surface_shader, is_valid_prim
from .registry import find_sdr_node, get_sdr_registry


def _find_unresolved_identifier_paths(
    nodes: dict[str, NetworkNode],
    registry: Any,
    source_type: str,
) -> set[str]:
    """Return paths whose authored shader identifiers do not resolve in SDR."""
    return {
        prim_path
        for prim_path, node in nodes.items()
        if node.identifier and not find_sdr_node(registry, node.identifier, source_type)
    }


def _record_identifier_changes(
    result: UpgradeResult,
    nodes: dict[str, NetworkNode],
    materialx_nodes: dict[str, Any],
    specs: dict[str, MaterialXNodeSpec],
    unresolved_identifier_paths: set[str],
    registry: Any,
    source_type: str,
) -> None:
    """Record valid upgraded identifiers and diagnostics on an upgrade result."""
    for prim_path, network_node in nodes.items():
        old_identifier = network_node.identifier
        spec = specs[prim_path]
        if not old_identifier or not spec.convertible:
            if prim_path in unresolved_identifier_paths:
                result.unresolved_prims.append(prim_path)
                result.diagnostics.append(
                    f"Cannot construct a MaterialX node for unresolved identifier {old_identifier!r} at {prim_path}"
                )
            continue

        new_identifier = resolved_identifier(materialx_nodes[prim_path])
        if not new_identifier or new_identifier == old_identifier:
            if prim_path in unresolved_identifier_paths:
                result.unresolved_prims.append(prim_path)
                result.diagnostics.append(
                    f"MaterialX left unresolved identifier {old_identifier!r} unchanged at {prim_path}"
                )
            continue
        if not find_sdr_node(registry, new_identifier, source_type):
            result.unresolved_prims.append(prim_path)
            result.diagnostics.append(
                f"Resolved identifier {new_identifier} for {prim_path} (was {old_identifier}) not found in SDR"
            )
            continue

        result.changes.append(IdentifierChange(prim_path, old_identifier, new_identifier))
        result.diagnostics.append(f"{prim_path} was upgraded from {old_identifier} to {new_identifier}")


def upgrade_materialx_identifiers(material_prim: Usd.Prim, source_type: str = "mtlx") -> UpgradeResult:
    """Build, upgrade, and diff a UsdShade material without mutating its stage."""
    result = UpgradeResult()
    if not is_valid_prim(material_prim):
        result.diagnostics.append("Invalid material prim")
        return result

    material = UsdShade.Material(material_prim)
    if not material:
        result.diagnostics.append("Prim is not a UsdShadeMaterial")
        return result

    surface = get_surface_shader(material, source_type)
    if not surface:
        result.diagnostics.append("Empty material network or no surface terminal")
        return result

    surface_shader, _surface_output = surface
    nodes = collect_network(material, surface_shader)
    if not nodes:
        result.diagnostics.append("Empty material network or no surface terminal")
        return result

    try:
        registry = get_sdr_registry()
    except Exception as exc:
        result.diagnostics.append(f"Failed to access SDR registry: {exc}")
        return result

    # Preserve the Material Graph 2.2.0 contract: this feature repairs shader
    # identifiers only. HdMtlx handles port/type/graph migrations transiently
    # in its render document; those migrations are not authored back to USD.
    unresolved_identifier_paths = _find_unresolved_identifier_paths(nodes, registry, source_type)
    if not unresolved_identifier_paths:
        result.diagnostics.append("All node identifiers resolve in SDR; no identifier repair needed")
        return result

    try:
        libraries = get_standard_libraries()
    except Exception as exc:
        result.diagnostics.append(f"Failed to load MaterialX standard libraries: {exc}")
        return result

    try:
        document, materialx_nodes, specs = build_materialx_document(material, nodes, libraries)
    except Exception as exc:
        result.diagnostics.append(f"Failed to build MaterialX document from UsdShade network: {exc}")
        return result

    result.pre_upgrade_xml = mx.writeToXmlString(document)
    try:
        document.upgradeVersion()
        result.upgrade_attempted = True
    except Exception as exc:
        result.upgrade_attempted = True
        result.diagnostics.append(f"upgradeVersion() failed: {exc}")
        return result
    result.post_upgrade_xml = mx.writeToXmlString(document)

    _record_identifier_changes(
        result,
        nodes,
        materialx_nodes,
        specs,
        unresolved_identifier_paths,
        registry,
        source_type,
    )
    result.diagnostics.append(
        f"Upgrade complete: {len(result.changes)} changed, {len(result.unresolved_prims)} unresolved"
    )
    return result
