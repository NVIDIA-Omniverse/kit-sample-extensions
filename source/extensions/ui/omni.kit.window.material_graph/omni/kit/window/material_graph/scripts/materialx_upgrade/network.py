# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""UsdShade traversal for MaterialX upgrade checks."""

from typing import Any, Optional

from pxr import Usd, UsdShade

from .models import NetworkNode


def is_valid_prim(prim: Usd.Prim) -> bool:
    """Return whether a USD prim handle exists and is valid."""
    return bool(prim) and prim.IsValid()


def _connected_source(shade_attribute: Any) -> Optional[tuple[Usd.Prim, str]]:
    """Return the source prim and output name connected to a shade attribute."""
    try:
        connection = shade_attribute.GetConnectedSource()
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None
    if not connection:
        return None
    source, source_name, _source_type = connection
    source_prim = source.GetPrim()
    if not is_valid_prim(source_prim):
        return None
    return source_prim, str(source_name)


def _resolve_to_shader(source_prim: Usd.Prim, source_name: str) -> Optional[tuple[UsdShade.Shader, str]]:
    """Follow NodeGraph outputs until they resolve to a concrete shader."""
    current_prim = source_prim
    current_name = source_name
    visited: set[str] = set()

    while is_valid_prim(current_prim):
        if current_prim.IsA(UsdShade.Shader):
            return UsdShade.Shader(current_prim), current_name
        if not current_prim.IsA(UsdShade.NodeGraph):
            return None

        current_path = str(current_prim.GetPath())
        if current_path in visited:
            return None
        visited.add(current_path)

        output = UsdShade.NodeGraph(current_prim).GetOutput(current_name)
        if not output:
            return None
        connection = _connected_source(output)
        if not connection:
            return None
        current_prim, current_name = connection

    return None


def get_surface_shader(
    material: UsdShade.Material,
    source_type: str,
) -> Optional[tuple[UsdShade.Shader, str]]:
    """Resolve the material surface shader for the requested render context."""
    outputs = []
    if source_type:
        output = material.GetSurfaceOutput(source_type)
        if output:
            outputs.append(output)
    else:
        outputs.extend(material.GetSurfaceOutputs())

    for output in outputs:
        connection = _connected_source(output)
        if not connection:
            continue
        resolved = _resolve_to_shader(*connection)
        if resolved:
            return resolved
    return None


def collect_network(
    material: UsdShade.Material,
    surface_shader: UsdShade.Shader,
) -> dict[str, NetworkNode]:
    """Collect connected and disconnected MaterialX shaders under a material."""
    nodes: dict[str, NetworkNode] = {}

    def visit(shader: UsdShade.Shader) -> None:
        """Visit one shader and recursively collect its upstream shaders."""
        prim = shader.GetPrim()
        path = str(prim.GetPath())
        if path in nodes:
            return

        node = NetworkNode(shader=shader, identifier=str(shader.GetShaderId() or ""))
        nodes[path] = node

        for shader_input in shader.GetInputs():
            connection = _connected_source(shader_input)
            if not connection:
                continue
            resolved = _resolve_to_shader(*connection)
            if not resolved:
                continue
            upstream_shader, upstream_output = resolved
            upstream_path = str(upstream_shader.GetPrim().GetPath())
            node.connections[str(shader_input.GetBaseName())] = (upstream_path, upstream_output)
            visit(upstream_shader)

    visit(surface_shader)

    # Include temporarily disconnected nodes so opening the graph upgrades the
    # whole material rather than only its currently connected surface branch.
    for prim in Usd.PrimRange(material.GetPrim()):
        if not prim.IsA(UsdShade.Shader):
            continue
        shader = UsdShade.Shader(prim)
        identifier = str(shader.GetShaderId() or "")
        if identifier.startswith("ND_"):
            visit(shader)

    return nodes
