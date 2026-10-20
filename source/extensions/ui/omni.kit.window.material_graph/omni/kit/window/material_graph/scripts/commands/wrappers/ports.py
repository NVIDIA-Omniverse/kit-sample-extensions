"""Port-command wrapper utilities with post-command USD-state validation."""

from typing import List, Optional

import omni.usd
from pxr import Sdf, Tf, Usd, UsdShade

from ...config.logging import logger
from ..execution import execute_command_checked
from ..result import CommandResult

# pylint: disable=no-member


def DisconnectInputPort(usdshade_input: UsdShade.Input) -> CommandResult:
    """Disconnect an input port."""
    return DisconnectSourcePort(usdshade_input)


def DisconnectSourcePort(usdshade_port: object) -> CommandResult:
    """Disconnect a UsdShade input or output port."""
    if not usdshade_port:
        return CommandResult(False, None, message="Missing port", error_code="invalid_args")
    previous_source = None
    try:
        if usdshade_port.HasConnectedSource():
            source_prim, source_name, source_type = usdshade_port.GetConnectedSource()
            previous_source = (
                str(source_prim.GetPath()) if source_prim else None,
                str(source_name),
                int(source_type),
            )
    except (RuntimeError, ValueError, TypeError, Tf.ErrorException) as exc:
        logger.debug("GetConnectedSource failed (best-effort validation): %s", exc)
        previous_source = None
    return execute_command_checked(
        "MaterialGraph_UsdShadeDisconnectSourceCommand",
        target=usdshade_port,
        validator=lambda result: _validate_disconnected_result(result, usdshade_port, previous_source),
    )


def _validate_attribute_result(
    result: CommandResult,
    prim_path: Sdf.Path,
    attr_name: str,
    as_output: bool,
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Ensure a requested input/output attribute exists after command execution.

    We do this extra verification because underlying command execution may report
    success even when authored USD state is not what callers expect.
    """
    if not result.success:
        return result
    stage = stage or omni.usd.get_context().get_stage()
    if not stage:
        return CommandResult(
            False,
            result.payload,
            message="No USD stage for validation",
            error_code="validation_stage_missing",
            command_name=result.command_name,
            validation={"prim_path": str(prim_path), "attribute": attr_name},
        )
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return CommandResult(
            False,
            result.payload,
            message="Prim missing after command",
            error_code="validation_prim_missing",
            command_name=result.command_name,
            validation={"prim_path": str(prim_path), "attribute": attr_name},
        )
    attr = prim.GetAttribute(attr_name)
    if not attr:
        return CommandResult(
            False,
            result.payload,
            message="Attribute missing after command",
            error_code="validation_attribute_missing",
            command_name=result.command_name,
            validation={"prim_path": str(prim_path), "attribute": attr_name},
        )
    payload = UsdShade.Output(attr) if as_output else UsdShade.Input(attr)
    return CommandResult(
        True,
        payload,
        message=result.message,
        error_code=result.error_code,
        command_name=result.command_name,
        validation={"exists": True, "attribute": attr_name},
    )


def _validate_connected_result(
    result: CommandResult, target_port: UsdShade.ConnectableAPI, source_port: UsdShade.ConnectableAPI
) -> CommandResult:
    """Validate a source connection is authored after command execution.

    Some underlying commands only return bool-style success and do not guarantee
    final authored connection state, so we verify post-state directly.
    """
    if not result.success:
        return result
    if not target_port or not source_port:
        return CommandResult(
            False,
            None,
            message="Invalid ports for validation",
            error_code="validation_invalid_ports",
            command_name=result.command_name,
        )
    try:
        has_source = target_port.HasConnectedSource()
    except (RuntimeError, ValueError, TypeError, Tf.ErrorException) as exc:
        logger.debug("_validate_connected_result HasConnectedSource failed: %s", exc)
        return CommandResult(
            False,
            None,
            message=str(exc),
            error_code="validation_exception",
            command_name=result.command_name,
        )
    if not has_source:
        return CommandResult(
            False,
            None,
            message="Connection missing after command",
            error_code="validation_connection_missing",
            command_name=result.command_name,
        )
    return CommandResult(True, True, command_name=result.command_name, validation={"connected": True})


def _validate_disconnected_result(
    result: CommandResult,
    target_port: UsdShade.ConnectableAPI,
    previous_source: object,
) -> CommandResult:
    """Validate a source disconnection is authored after command execution.

    This protects against false-positive command success where the source
    relationship still exists after execution.
    """
    if not result.success:
        return result
    if not target_port:
        return CommandResult(
            False,
            None,
            message="Invalid target for disconnect validation",
            error_code="validation_invalid_target",
            command_name=result.command_name,
        )
    try:
        has_source = target_port.HasConnectedSource()
    except (RuntimeError, ValueError, TypeError, Tf.ErrorException) as exc:
        logger.debug("_validate_disconnected_result HasConnectedSource failed: %s", exc)
        return CommandResult(
            False,
            None,
            message=str(exc),
            error_code="validation_exception",
            command_name=result.command_name,
        )
    if has_source:
        return CommandResult(
            False,
            None,
            message="Connection still present after disconnect",
            error_code="validation_disconnect_failed",
            command_name=result.command_name,
            validation={"previous_source": previous_source},
        )
    return CommandResult(
        True,
        None,
        command_name=result.command_name,
        validation={"disconnected": True, "previous_source": previous_source},
    )


def _validate_removed_connections_result(
    result: CommandResult,
    dest_attr_path: Sdf.Path,
    disconnected_values: List[Sdf.Path],
) -> CommandResult:
    """Validate expected source paths are no longer connected to destination.

    The command can succeed operationally while only partially applying intent;
    we compare requested removals with actual connected sources.
    """
    if not result.success:
        return result
    stage = omni.usd.get_context().get_stage()
    if not stage:
        return CommandResult(
            False,
            None,
            message="No USD stage for validation",
            error_code="validation_stage_missing",
            command_name=result.command_name,
        )
    dest_attr = stage.GetAttributeAtPath(dest_attr_path)
    if not dest_attr:
        return CommandResult(
            False,
            None,
            message="Destination attribute missing after command",
            error_code="validation_destination_missing",
            command_name=result.command_name,
            validation={"dest_attr_path": str(dest_attr_path)},
        )
    port = UsdShade.Input(dest_attr) if UsdShade.Input.IsInput(dest_attr) else UsdShade.Output(dest_attr)
    try:
        source_infos = port.GetConnectedSources()
    except (RuntimeError, ValueError, TypeError, Tf.ErrorException) as exc:
        logger.debug("_validate_removed_connections_result GetConnectedSources failed: %s", exc)
        return CommandResult(
            False,
            None,
            message=str(exc),
            error_code="validation_exception",
            command_name=result.command_name,
        )
    source_infos = source_infos[0] if isinstance(source_infos, tuple) else source_infos
    connected_paths = set()
    for source_info in source_infos or []:
        if not source_info:
            continue
        prefix = (
            UsdShade.Tokens.inputs
            if source_info.sourceType == UsdShade.AttributeType.Input
            else UsdShade.Tokens.outputs
        )
        connected_paths.add(str(source_info.source.GetPath().AppendProperty(f"{prefix}{source_info.sourceName}")))
    requested = {str(path) for path in disconnected_values}
    still_connected = sorted(requested.intersection(connected_paths))
    if still_connected:
        return CommandResult(
            False,
            None,
            message="Some requested connections still present",
            error_code="validation_remove_connections_failed",
            command_name=result.command_name,
            validation={"still_connected": tuple(still_connected)},
        )
    return CommandResult(
        True,
        None,
        command_name=result.command_name,
        validation={"removed_connections": tuple(sorted(requested))},
    )


def CreateInputPort(
    prim_path: Sdf.Path,
    port_name: str,
    port_type: Sdf.ValueTypeName,
    variability: Sdf.Variability = Sdf.VariabilityVarying,
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Create an input port and return a structured command result."""
    if not prim_path or not isinstance(port_name, str):
        return CommandResult(False, None, message="Invalid arguments", error_code="invalid_args")
    if not isinstance(port_type, Sdf.ValueTypeName) or not port_type:
        return CommandResult(False, None, message="Invalid USD value type", error_code="invalid_port_type")
    if variability is None:
        variability = Sdf.VariabilityVarying
    full_name = port_name if port_name.startswith(UsdShade.Tokens.inputs) else f"{UsdShade.Tokens.inputs}{port_name}"
    return execute_command_checked(
        "MaterialGraph_CreateInputPortCommand",
        prim_path=prim_path,
        port_name=port_name,
        port_type=port_type,
        variability=variability,
        stage=stage,
        error_message="create input port failed",
        validator=lambda result: _validate_attribute_result(
            result,
            prim_path,
            full_name,
            as_output=False,
            stage=stage,
        ),
    )


def CreateOutputPort(
    prim_path: Sdf.Path,
    port_name: str,
    port_type: Sdf.ValueTypeName,
    variability: Sdf.Variability = Sdf.VariabilityVarying,
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Create an output port and return a structured command result."""
    if not prim_path or not isinstance(port_name, str):
        return CommandResult(False, None, message="Invalid arguments", error_code="invalid_args")
    if not isinstance(port_type, Sdf.ValueTypeName) or not port_type:
        return CommandResult(False, None, message="Invalid USD value type", error_code="invalid_port_type")
    if variability is None:
        variability = Sdf.VariabilityVarying
    full_name = port_name if port_name.startswith(UsdShade.Tokens.outputs) else f"{UsdShade.Tokens.outputs}{port_name}"
    return execute_command_checked(
        "MaterialGraph_CreateOutputPortCommand",
        prim_path=prim_path,
        port_name=port_name,
        port_type=port_type,
        variability=variability,
        stage=stage,
        error_message="create output port failed",
        validator=lambda result: _validate_attribute_result(
            result,
            prim_path,
            full_name,
            as_output=True,
            stage=stage,
        ),
    )


def ConnectInputToSource(usdshade_input: UsdShade.Input, source_input: UsdShade.Output) -> CommandResult:
    """Connect an input to a source and return a structured result."""
    if not usdshade_input or not source_input:
        return CommandResult(False, False, message="Invalid input/source", error_code="invalid_args")
    return execute_command_checked(
        "MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand",
        target=usdshade_input,
        source=source_input,
        error_message="connect input failed",
        validator=lambda result: _validate_connected_result(result, usdshade_input, source_input),
    )


def ConnectPortToSource(target_port: UsdShade.ConnectableAPI, source_port: UsdShade.ConnectableAPI) -> CommandResult:
    """Connect a generic port to source and return a structured result."""
    if not target_port or not source_port:
        return CommandResult(False, False, message="Invalid target/source", error_code="invalid_args")
    return execute_command_checked(
        "MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand",
        target=target_port,
        source=source_port,
        error_message="connect port failed",
        validator=lambda result: _validate_connected_result(result, target_port, source_port),
    )


def RemoveConnections(dest_attr_path: Sdf.Path, disconnected_values: List[Sdf.Path]) -> CommandResult:
    """Remove connections from a destination attribute."""
    if not dest_attr_path or not disconnected_values:
        return CommandResult(False, None, message="Invalid arguments", error_code="invalid_args")
    return execute_command_checked(
        "MaterialGraph_RemoveConnectionsCommand",
        dest_attr_path=dest_attr_path,
        disconnected_values=disconnected_values,
        validator=lambda result: _validate_removed_connections_result(result, dest_attr_path, disconnected_values),
    )
