"""Shared nodegraph grouping helpers for rewiring ports during group/ungroup."""

from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

import omni.kit.undo
from pxr import Sdf, Usd, UsdShade

from ....config.logging import get_logger
from ...wrappers import (
    ConnectPortToSource,
    CreateInputPort,
    CreateOutputPort,
    DeletePrims,
    DisconnectInputPort,
    MovePrims,
)

# pylint: disable=no-member

_Port = Union[UsdShade.Input, UsdShade.Output]
_SourceInfo = UsdShade.ConnectionSourceInfo
logger = get_logger()


def _normalize_connected_sources(port: _Port) -> List[_SourceInfo]:
    """Return connected sources with tuple/list normalization."""
    sources_result = port.GetConnectedSources()
    sources = sources_result[0] if isinstance(sources_result, tuple) else sources_result
    return list(sources or [])


def _iter_connected_sources(port: _Port) -> Iterable[_SourceInfo]:
    """Iterate normalized source connections for a port."""
    for source_info in _normalize_connected_sources(port):
        yield source_info


def _resolve_source_port(stage: Usd.Stage, source_info: _SourceInfo) -> Optional[_Port]:
    """Resolve connection source metadata to a concrete input/output port."""
    prim_path = source_info.source.GetPath()
    prefix = (
        UsdShade.Tokens.inputs if source_info.sourceType == UsdShade.AttributeType.Input else UsdShade.Tokens.outputs
    )
    prop_path = prim_path.AppendProperty(f"{prefix}{source_info.sourceName}")
    attr = stage.GetAttributeAtPath(prop_path)
    if not attr:
        return None
    if source_info.sourceType == UsdShade.AttributeType.Input:
        return UsdShade.Input(attr)
    return UsdShade.Output(attr)


def _normalize_port_name(name: str) -> str:
    """Strip USD inputs/outputs prefixes from a port name."""
    return name.removeprefix(UsdShade.Tokens.inputs).removeprefix(UsdShade.Tokens.outputs)


def _unique_port_name(base: str, existing: Set[str]) -> str:
    """Generate a unique port name and reserve it in the existing set."""
    if base not in existing:
        existing.add(base)
        return base
    index = 1
    while f"{base}_{index}" in existing:
        index += 1
    name = f"{base}_{index}"
    existing.add(name)
    return name


def _resolve_input_port_attr(
    stage: Usd.Stage, nodegraph_path: Sdf.Path, port_name: str, port_type: Sdf.ValueTypeName
) -> Optional[UsdShade.Input]:
    """Create or recover a nodegraph input port attribute."""
    ng_input_result = CreateInputPort(nodegraph_path, port_name, port_type, stage=stage)
    ng_input_attr = ng_input_result.payload if ng_input_result.success else None
    if not ng_input_attr:
        attr_path = nodegraph_path.AppendProperty(f"{UsdShade.Tokens.inputs}{port_name}")
        ng_input_attr = stage.GetAttributeAtPath(attr_path)
        if not ng_input_attr:
            return None
    return ng_input_attr if isinstance(ng_input_attr, UsdShade.Input) else UsdShade.Input(ng_input_attr)


def _resolve_output_port_attr(
    stage: Usd.Stage, nodegraph_path: Sdf.Path, port_name: str, port_type: Sdf.ValueTypeName
) -> Optional[UsdShade.Output]:
    """Create or recover a nodegraph output port attribute."""
    ng_output_result = CreateOutputPort(nodegraph_path, port_name, port_type, stage=stage)
    ng_output_attr = ng_output_result.payload if ng_output_result.success else None
    if not ng_output_attr:
        attr_path = nodegraph_path.AppendProperty(f"{UsdShade.Tokens.outputs}{port_name}")
        ng_output_attr = stage.GetAttributeAtPath(attr_path)
        if not ng_output_attr:
            return None
    return ng_output_attr if isinstance(ng_output_attr, UsdShade.Output) else UsdShade.Output(ng_output_attr)


def _rewire_inputs_crossing_group_boundary(
    stage: Usd.Stage,
    parent_path: Sdf.Path,
    nodegraph_path: Sdf.Path,
    selected_paths: Set[Sdf.Path],
    existing: Set[str],
) -> bool:
    """Route selected-node input dependencies through nodegraph input ports."""
    for path in selected_paths:
        prim = stage.GetPrimAtPath(path)
        if not prim:
            continue
        api = UsdShade.ConnectableAPI(prim)
        for input_port in api.GetInputs():
            for source_info in _iter_connected_sources(input_port):
                source_prim_path = source_info.source.GetPath()
                if source_prim_path in selected_paths:
                    continue
                source_port = _resolve_source_port(stage, source_info)
                if not source_port:
                    continue
                port_type = input_port.GetTypeName() or source_port.GetTypeName() or Sdf.ValueTypeNames.Token
                base_name = (
                    str(source_info.sourceName)
                    if source_prim_path == parent_path
                    else f"{prim.GetName()}_{input_port.GetBaseName()}"
                )
                port_name = _normalize_port_name(_unique_port_name(base_name, existing))
                ng_input = _resolve_input_port_attr(stage, nodegraph_path, port_name, port_type)
                if not ng_input:
                    return False
                if not ConnectPortToSource(ng_input, source_port).success:
                    return False
                if not DisconnectInputPort(input_port).success:
                    return False
                if not ConnectPortToSource(input_port, ng_input).success:
                    return False
    return True


def _ensure_group_output(
    stage: Usd.Stage,
    nodegraph_path: Sdf.Path,
    existing: Set[str],
    output_port_map: Dict[Tuple[Sdf.Path, str, int], UsdShade.Output],
    source_prim_path: Sdf.Path,
    source_info: _SourceInfo,
    source_port: _Port,
    fallback_port_type: Sdf.ValueTypeName,
    preferred_name: Optional[str] = None,
) -> Optional[UsdShade.Output]:
    """Resolve existing output mapping or create a new nodegraph output port."""
    key = (source_prim_path, source_info.sourceName, source_info.sourceType)
    ng_output = output_port_map.get(key)
    if ng_output:
        return ng_output
    base_name = preferred_name or f"{source_prim_path.name}_{source_info.sourceName}"
    port_name = _normalize_port_name(_unique_port_name(base_name, existing))
    port_type = source_port.GetTypeName() if source_port else fallback_port_type
    ng_output = _resolve_output_port_attr(stage, nodegraph_path, port_name, port_type)
    if not ng_output:
        return None
    output_port_map[key] = ng_output
    if not ConnectPortToSource(ng_output, source_port).success:
        output_port_map.pop(key, None)
        return None
    return ng_output


def _rewire_external_inputs_to_group_outputs(
    stage: Usd.Stage,
    parent_path: Sdf.Path,
    nodegraph_path: Sdf.Path,
    selected_paths: Set[Sdf.Path],
    existing: Set[str],
    output_port_map: Dict[Tuple[Sdf.Path, str, int], UsdShade.Output],
) -> bool:
    """Route external input connections from selected nodes through group outputs."""
    root_prim = stage.GetPrimAtPath(parent_path)
    if not root_prim:
        return False

    for iter_prim in Usd.PrimRange(root_prim):
        if iter_prim.GetPath().HasPrefix(nodegraph_path) or iter_prim.GetPath() in selected_paths:
            continue
        if not (iter_prim.IsA(UsdShade.Shader) or iter_prim.IsA(UsdShade.NodeGraph)):
            continue
        api = UsdShade.ConnectableAPI(iter_prim)
        for input_port in api.GetInputs():
            for source_info in _iter_connected_sources(input_port):
                source_prim_path = source_info.source.GetPath()
                if source_prim_path not in selected_paths:
                    continue
                source_port = _resolve_source_port(stage, source_info)
                if not source_port:
                    continue
                ng_output = _ensure_group_output(
                    stage,
                    nodegraph_path,
                    existing,
                    output_port_map,
                    source_prim_path,
                    source_info,
                    source_port,
                    input_port.GetTypeName(),
                )
                if not ng_output:
                    return False
                if not DisconnectInputPort(input_port).success:
                    return False
                if not ConnectPortToSource(input_port, ng_output).success:
                    return False
    return True


def _rewire_external_outputs_to_group_outputs(
    stage: Usd.Stage,
    parent_path: Sdf.Path,
    nodegraph_path: Sdf.Path,
    selected_paths: Set[Sdf.Path],
    existing: Set[str],
    output_port_map: Dict[Tuple[Sdf.Path, str, int], UsdShade.Output],
) -> bool:
    """Route external output connections from selected nodes through group outputs."""
    root_prim = stage.GetPrimAtPath(parent_path)
    if not root_prim:
        return False

    for iter_prim in Usd.PrimRange(root_prim):
        if iter_prim.GetPath().HasPrefix(nodegraph_path) or iter_prim.GetPath() in selected_paths:
            continue
        if not (iter_prim.IsA(UsdShade.Shader) or iter_prim.IsA(UsdShade.NodeGraph)):
            continue
        api = UsdShade.ConnectableAPI(iter_prim)
        for output_port in api.GetOutputs():
            for source_info in _iter_connected_sources(output_port):
                source_prim_path = source_info.source.GetPath()
                if source_prim_path not in selected_paths:
                    continue
                source_port = _resolve_source_port(stage, source_info)
                if not source_port:
                    continue
                ng_output = _ensure_group_output(
                    stage,
                    nodegraph_path,
                    existing,
                    output_port_map,
                    source_prim_path,
                    source_info,
                    source_port,
                    output_port.GetTypeName(),
                    output_port.GetBaseName() if iter_prim.GetPath() == parent_path else None,
                )
                if not ng_output:
                    return False
                if not ConnectPortToSource(output_port, ng_output).success:
                    return False
    return True


def _rewire_group_inputs_back_to_children(
    stage: Usd.Stage, nodegraph: UsdShade.NodeGraph, nodegraph_path: Sdf.Path, children: Sequence[Usd.Prim]
) -> bool:
    """Reconnect child input ports to original sources through nodegraph inputs."""
    for ng_input in nodegraph.GetInputs():
        for source_info in _iter_connected_sources(ng_input):
            source_port = _resolve_source_port(stage, source_info)
            if not source_port:
                continue
            for child in children:
                api = UsdShade.ConnectableAPI(child)
                for child_input in api.GetInputs():
                    for child_info in _iter_connected_sources(child_input):
                        if (
                            child_info.source.GetPath() == nodegraph_path
                            and child_info.sourceName == ng_input.GetBaseName()
                        ):
                            if not DisconnectInputPort(child_input).success:
                                return False
                            if not ConnectPortToSource(child_input, source_port).success:
                                return False
    return True


def _find_internal_source_for_output(stage: Usd.Stage, ng_output: UsdShade.Output) -> Optional[_Port]:
    """Return the first internal source connected to a nodegraph output."""
    for source_info in _iter_connected_sources(ng_output):
        internal_source = _resolve_source_port(stage, source_info)
        if internal_source:
            return internal_source
    for raw_path in ng_output.GetRawConnectedSourcePaths() or []:
        attr = stage.GetAttributeAtPath(raw_path)
        if not attr:
            continue
        if raw_path.name.startswith(UsdShade.Tokens.inputs):
            return UsdShade.Input(attr)
        if raw_path.name.startswith(UsdShade.Tokens.outputs):
            return UsdShade.Output(attr)
    return None


def _rewire_external_references_to_internal_sources(
    stage: Usd.Stage,
    parent_path: Sdf.Path,
    nodegraph_path: Sdf.Path,
    nodegraph: UsdShade.NodeGraph,
) -> bool:
    """Reconnect parent-scope consumers/producers away from nodegraph ports."""
    root_prim = stage.GetPrimAtPath(parent_path)
    if not root_prim:
        return False
    for ng_output in nodegraph.GetOutputs():
        internal_source = _find_internal_source_for_output(stage, ng_output)
        if not internal_source:
            continue
        for iter_prim in Usd.PrimRange(root_prim):
            if iter_prim.GetPath().HasPrefix(nodegraph_path):
                continue
            api = UsdShade.ConnectableAPI(iter_prim)
            for input_port in api.GetInputs():
                for source_info in _iter_connected_sources(input_port):
                    if (
                        source_info.source.GetPath() == nodegraph_path
                        and source_info.sourceName == ng_output.GetBaseName()
                    ):
                        if not DisconnectInputPort(input_port).success:
                            return False
                        if not ConnectPortToSource(input_port, internal_source).success:
                            return False
            for output_port in api.GetOutputs():
                for source_info in _iter_connected_sources(output_port):
                    if (
                        source_info.source.GetPath() == nodegraph_path
                        and source_info.sourceName == ng_output.GetBaseName()
                    ):
                        # ClearConnections drops existing output connections before reconnecting.
                        output_port.GetAttr().ClearConnections()
                        if not ConnectPortToSource(output_port, internal_source).success:
                            return False
    return True


def _group_nodes_into_nodegraph(
    stage: Usd.Stage,
    parent_path: Sdf.Path,
    nodegraph_prim: Usd.Prim,
    selected_paths: Set[Sdf.Path],
) -> bool:
    """Create nodegraph I/O ports and rewire connections."""
    if not stage or not nodegraph_prim or not parent_path or not selected_paths:
        return False

    nodegraph_path = nodegraph_prim.GetPath()
    nodegraph = UsdShade.NodeGraph(nodegraph_prim)
    existing = {port.GetBaseName() for port in (nodegraph.GetInputs() + nodegraph.GetOutputs())}
    output_port_map: Dict[Tuple[Sdf.Path, str, int], UsdShade.Output] = {}
    if not _rewire_inputs_crossing_group_boundary(stage, parent_path, nodegraph_path, selected_paths, existing):
        return False
    if not _rewire_external_inputs_to_group_outputs(
        stage, parent_path, nodegraph_path, selected_paths, existing, output_port_map
    ):
        return False
    if not _rewire_external_outputs_to_group_outputs(
        stage, parent_path, nodegraph_path, selected_paths, existing, output_port_map
    ):
        return False
    return True


def _ungroup_nodegraph(stage: Usd.Stage, nodegraph_prim: Usd.Prim) -> bool:
    """Ungroup a nodegraph by moving children and reconnecting ports."""
    if not stage or not nodegraph_prim:
        return False

    edit_layer = stage.GetEditTarget().GetLayer()
    snapshot = Sdf.Layer.CreateAnonymous("material_graph_ungroup_transaction.usda")
    snapshot.TransferContent(edit_layer)

    def _rollback() -> bool:
        edit_layer.TransferContent(snapshot)
        return False

    nodegraph_path = nodegraph_prim.GetPath()
    parent_path = nodegraph_path.GetParentPath()
    nodegraph = UsdShade.NodeGraph(nodegraph_prim)
    children = [child for child in nodegraph_prim.GetChildren()]
    # The registered group/ungroup command owns the outer undo item. Prevent
    # successful inner rewires/moves from surviving a later rollback as ghost
    # commands that could mutate the graph on a subsequent redo.
    with omni.kit.undo.disabled():
        if not _rewire_group_inputs_back_to_children(stage, nodegraph, nodegraph_path, children):
            return _rollback()
        if not _rewire_external_references_to_internal_sources(stage, parent_path, nodegraph_path, nodegraph):
            return _rollback()

        paths_to_move: Dict[str, str] = {}
        for child in children:
            old_path = child.GetPath().pathString
            new_path = parent_path.AppendChild(child.GetName()).pathString
            paths_to_move[old_path] = new_path

        if paths_to_move:
            move_result = MovePrims(paths_to_move=paths_to_move, destructive=False, stage_or_context=stage)
            if not move_result.success:
                logger.warning(
                    "ungroup move failed for nodegraph %s while moving %s child prim(s) to %s: %s",
                    nodegraph_path,
                    len(paths_to_move),
                    parent_path,
                    move_result.error_code or move_result.message,
                )
                return _rollback()

        delete_result = DeletePrims(paths=[nodegraph_path], stage=stage)
        if not delete_result.success:
            logger.warning(
                "ungroup failed to delete emptied nodegraph %s: %s",
                nodegraph_path,
                delete_result.error_code or delete_result.message,
            )
            return _rollback()
    return True
