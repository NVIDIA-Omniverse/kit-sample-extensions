"""High-level isolation command wrappers with structured result validation."""

from typing import Iterable, Optional, Type

from pxr import UsdShade

from ...config.logging import logger
from ..execution import execute_command
from ..result import CommandResult
from .attributes import RemoveProperty

# pylint: disable=no-member


def _is_output_node(node: object, output_cls: Optional[Type[object]]) -> bool:
    """Return True when node behaves as isolation output-node type."""
    if output_cls:
        try:
            return isinstance(node, output_cls)
        except TypeError as exc:
            logger.debug("_is_output_node isinstance failed: %s", exc)
            return False
    node_fields = dir(node)
    return "remove_output" in node_fields and "remove_input" not in node_fields


def _is_empty_port(port: object, empty_cls: Optional[Type[object]]) -> bool:
    """Return True when port is an isolation empty-port sentinel."""
    if empty_cls:
        try:
            return isinstance(port, empty_cls)
        except TypeError as exc:
            logger.debug("_is_empty_port isinstance failed: %s", exc)
            return False
    return False


def DeleteInputOutputNodes(isolation_model: object, nodes: Iterable[object], graph_model: object) -> CommandResult:
    """Remove isolation nodes and return structured result."""
    try:
        from ...models.graph.isolation import MaterialGraphIsolationModel
        from ...models.graph.nodes.material import MaterialModel
    except (ImportError, AttributeError) as exc:
        logger.debug("isolation model import failed (reduced env): %s", exc)
        MaterialGraphIsolationModel = None
        MaterialModel = None
    output_cls = MaterialGraphIsolationModel.OutputNode if MaterialGraphIsolationModel else None
    empty_cls = MaterialGraphIsolationModel.EmptyPort if MaterialGraphIsolationModel else None
    removed_count = 0
    warnings: list[str] = []
    for node in nodes:
        for port in node.ports or []:
            if _is_empty_port(port, empty_cls):
                continue
            path = port.path
            if path:
                remove_result = RemoveProperty(path)
                if not remove_result.success:
                    warnings.append(f"remove_property_failed:{path}")

        if _is_output_node(node, output_cls) and MaterialModel and isinstance(graph_model, MaterialModel):
            material = UsdShade.Material(graph_model.prim)
            context_name = graph_model.context_name
            if context_name == "universal":
                context_name = UsdShade.Tokens.universalRenderContext
            output = material.GetSurfaceOutput(context_name)
            if output:
                disconnect_result = execute_command(
                    "MaterialGraph_UsdShadeDisconnectSourceCommand",
                    target=output,
                )
                if not disconnect_result.success:
                    warnings.append(f"disconnect_failed:{output.GetAttr().GetPath()}")

        remove_node_result = execute_command(
            "MaterialGraph_IsolationModelRemoveCommand",
            isolation_model=isolation_model,
            node=node,
            graph_model=graph_model,
        )
        if remove_node_result.success:
            removed_count += 1
        else:
            warnings.append("remove_isolation_node_failed")
    if warnings:
        return CommandResult(
            False,
            removed_count,
            message="Isolation cleanup had failures",
            error_code="isolation_cleanup_failed",
            validation={"removed_nodes": removed_count},
            warnings=tuple(warnings),
        )
    return CommandResult(True, removed_count, validation={"removed_nodes": removed_count})
