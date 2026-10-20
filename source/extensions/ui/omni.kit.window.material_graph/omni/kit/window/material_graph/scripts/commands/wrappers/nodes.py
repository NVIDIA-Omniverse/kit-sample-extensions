"""Node-creation wrapper helpers that normalize command results and payloads."""

from typing import Dict, Optional, Tuple

from pxr import Sdf, Usd, UsdShade

from ...config.logging import logger
from ...utils.sdr_wrappers import SdrShaderNodeWrapper, resolve_output_value_type
from ..execution import execute_command_checked
from ..result import CommandResult

# pylint: disable=no-member

Position = Tuple[float, float]


def CreateShader(
    parent_path: Sdf.Path,
    sdr_node: SdrShaderNodeWrapper,
    position: Optional[Position],
    stage: Optional[Usd.Stage] = None,
    **kwargs: object,
) -> CommandResult:
    """Create a shader prim from an SDR node and return structured result."""
    if not parent_path or not sdr_node:
        return CommandResult(False, None, message="Invalid arguments", error_code="invalid_args")

    identifier = sdr_node.GetIdentifier().split(">")[0].split("<")[-1]
    prim_name = identifier.split("(")[0]

    source_asset_path = kwargs.get("source_asset_path", None)
    context = None
    subidentifier = None
    if source_asset_path:
        context = kwargs.get("context", None)
        subidentifier = kwargs.get("subidentifier", None)
        polymorphic_subidentifiers = kwargs.get("polymorphic_subidentifiers", None)
        if kwargs.get("is_polymorphic", False) and isinstance(polymorphic_subidentifiers, list):
            # Deterministic fallback for unconstrained polymorphic nodes.
            first_candidate = next((str(item) for item in polymorphic_subidentifiers if item), None)
            if first_candidate:
                subidentifier = first_candidate
        if not (context and subidentifier):
            return CommandResult(
                False,
                None,
                message="source_asset_path requires context + subidentifier",
                error_code="invalid_args",
            )
    output_types = {}
    for name in sdr_node.GetShaderOutputNames():
        sdr_shader_property = sdr_node.GetShaderOutput(name)
        if not sdr_shader_property:
            continue
        output_types[name] = resolve_output_value_type(sdr_shader_property)

    return execute_command_checked(
        "MaterialGraph_CreatePrimCommand",
        parent_path=parent_path,
        prim_type=UsdShade.Tokens.Shader,
        prim_name=prim_name,
        shader_identifier=None if source_asset_path else identifier,
        source_asset_path=str(source_asset_path) if source_asset_path else None,
        source_asset_context=str(context) if context else None,
        source_asset_subidentifier=str(subidentifier) if subidentifier else None,
        output_types=output_types,
        input_values=kwargs.get("input_values"),
        position=position,
        stage=stage,
        error_message="create shader failed",
    )


def CreateNode(
    parent_path: Sdf.Path,
    prim_type: str,
    sub_identifier: str,
    source_asset: object,
    position: Optional[Position] = None,
    attributes_to_set: Optional[Dict[Sdf.Path, object]] = None,
    prim_name: Optional[str] = None,
    context_name: Optional[str] = None,
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Create a node prim and return structured result."""
    if not parent_path or not prim_type:
        return CommandResult(False, None, message="Invalid arguments", error_code="invalid_args")
    if prim_type == "Backdrop":
        return execute_command_checked(
            "MaterialGraph_CreateUsdUIBackdropCommand",
            parent_path=parent_path,
            identifier=prim_type,
            position=position,
            stage=stage,
        )

    if prim_type == "NodeGraph":
        return execute_command_checked(
            "MaterialGraph_NewUsdShadeNodeGraphCommand",
            parent_path=parent_path,
            identifier=prim_type,
            position=position,
            context_visibility=context_name,
            stage=stage,
        )

    if prim_type == "ImportNodeGraph":
        return execute_command_checked(
            "MaterialGraph_ImportNodeGraphCommand",
            parent_path=parent_path,
            source_asset=source_asset,
            identifier=sub_identifier,
            position=position,
            attributes_to_set=attributes_to_set,
            prim_name=prim_name,
            context_name=context_name,
            stage=stage,
        )

    logger.warning("unsupported node type for CreateNode: %s", prim_type)
    return CommandResult(
        False,
        None,
        message="Unsupported node type",
        error_code="unsupported_node_type",
        warnings=(f"unsupported:{prim_type}",),
    )
