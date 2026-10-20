# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""MaterialX document construction from collected UsdShade shaders."""

from functools import lru_cache
from typing import Any

import MaterialX as mx
from pxr import UsdShade

from .constants import (
    FALLBACK_SOURCE_MATERIALX_VERSION,
    MATERIALX_VERSION_ATTRIBUTE,
    SWIZZLE_NODE_DEF_PATTERN,
    USD_TO_MATERIALX_TYPES,
)
from .models import MaterialXNodeSpec, NetworkNode


@lru_cache(maxsize=1)
def get_standard_libraries() -> Any:
    """Load and cache the standard libraries bundled with MaterialX."""
    libraries = mx.createDocument()
    loaded_files = mx.loadLibraries(
        mx.getDefaultDataLibraryFolders(),
        mx.getDefaultDataSearchPath(),
        libraries,
    )
    if not loaded_files:
        raise RuntimeError("MaterialX standard libraries could not be loaded")
    return libraries


def _materialx_category(node_def: Any) -> str:
    """Return the category of a MaterialX node definition with its namespace."""
    category = str(node_def.getNodeString())
    if node_def.hasNamespace():
        return f"{node_def.getNamespace()}:{category}"
    return category


def _get_node_spec(identifier: str, document: Any) -> MaterialXNodeSpec:
    """Return the MaterialX representation of one UsdShade identifier."""
    node_def = document.getNodeDef(identifier)
    if node_def:
        return MaterialXNodeSpec(
            category=_materialx_category(node_def),
            output_type=str(node_def.getType()),
            node_def_name=str(node_def.getName()),
        )

    # MaterialX 1.39 renamed this definition. Creating the node by category
    # and output type allows upgradeVersion() to apply the current definition.
    if identifier == "ND_normalmap":
        return MaterialXNodeSpec(category="normalmap", output_type="vector3")

    # MaterialX 1.39 removed swizzle definitions. Their identifiers encode the
    # input and output types needed by upgradeVersion() for structural repair.
    match = SWIZZLE_NODE_DEF_PATTERN.fullmatch(identifier)
    if match:
        return MaterialXNodeSpec(
            category="swizzle",
            output_type=match.group(2),
            swizzle_input_type=match.group(1),
        )

    # Preserve unknown nodes in the document without proposing a fabricated
    # identifier change for them.
    return MaterialXNodeSpec(category="surface", output_type="surfaceshader", convertible=False)


def _input_type(shader_input: UsdShade.Input, node_def: Any, spec: MaterialXNodeSpec) -> str:
    """Resolve a MaterialX input type from a node definition or USD type."""
    name = str(shader_input.GetBaseName())
    if node_def:
        node_def_input = node_def.getActiveInput(name)
        if node_def_input:
            return str(node_def_input.getType())
    if spec.swizzle_input_type and name == "in":
        return spec.swizzle_input_type
    if spec.swizzle_input_type and name == "channels":
        return "string"
    return USD_TO_MATERIALX_TYPES.get(str(shader_input.GetTypeName()), "string")


def _value_to_string(value: Any) -> str:
    """Serialize a common USD value using MaterialX value syntax."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    if hasattr(value, "path"):
        return str(value.path)
    if isinstance(value, (int, float)):
        return str(value)
    try:
        return ", ".join(str(component) for component in value)
    except TypeError:
        return str(value)


def build_materialx_document(
    material: UsdShade.Material,
    nodes: dict[str, NetworkNode],
    libraries: Any,
) -> tuple[Any, dict[str, Any], dict[str, MaterialXNodeSpec]]:
    """Build a MaterialX document and retain exact USD-path node mappings."""
    document = mx.createDocument()
    document.importLibrary(libraries)

    version_attribute = material.GetPrim().GetAttribute(MATERIALX_VERSION_ATTRIBUTE)
    materialx_version = version_attribute.Get() if version_attribute else None
    document.setVersionString(str(materialx_version or FALLBACK_SOURCE_MATERIALX_VERSION))

    graph_name = document.createValidChildName(f"NG_{material.GetPrim().GetName()}")
    node_graph = document.addNodeGraph(graph_name)
    materialx_nodes: dict[str, Any] = {}
    specs: dict[str, MaterialXNodeSpec] = {}

    for prim_path, network_node in nodes.items():
        spec = _get_node_spec(network_node.identifier, document)
        specs[prim_path] = spec
        node_name = node_graph.createValidChildName(network_node.shader.GetPrim().GetName())
        materialx_node = node_graph.addNode(spec.category, node_name, spec.output_type)
        if spec.node_def_name:
            materialx_node.setNodeDefString(spec.node_def_name)
        materialx_nodes[prim_path] = materialx_node

    for prim_path, network_node in nodes.items():
        materialx_node = materialx_nodes[prim_path]
        spec = specs[prim_path]
        node_def = document.getNodeDef(spec.node_def_name) if spec.node_def_name else materialx_node.getNodeDef()

        for shader_input in network_node.shader.GetInputs():
            input_name = str(shader_input.GetBaseName())
            input_type = _input_type(shader_input, node_def, spec)
            materialx_input = materialx_node.getInput(input_name)
            if not materialx_input:
                materialx_input = materialx_node.addInput(input_name, input_type)

            connection = network_node.connections.get(input_name)
            if connection:
                upstream_path, upstream_output = connection
                upstream_node = materialx_nodes.get(upstream_path)
                if upstream_node:
                    materialx_input.setConnectedNode(upstream_node)
                    if upstream_output and upstream_node.isMultiOutputType():
                        materialx_input.setOutputString(upstream_output)
                continue

            value = shader_input.Get()
            if value is not None:
                materialx_input.setValueString(_value_to_string(value))

    return document, materialx_nodes, specs


def resolved_identifier(materialx_node: Any) -> str:
    """Return the node-definition identifier represented by a MaterialX node."""
    node_def = materialx_node.getNodeDef()
    if node_def:
        return str(node_def.getName())
    category = str(materialx_node.getCategory())
    output_type = str(materialx_node.getType())
    if category and output_type:
        return f"ND_{category}_{output_type}"
    if category:
        return f"ND_{category}"
    return ""
