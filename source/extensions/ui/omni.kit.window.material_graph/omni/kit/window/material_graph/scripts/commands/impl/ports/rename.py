"""Rename-port command implementation that preserves connections and metadata."""

from typing import List, Optional, Sequence, Union

import omni.kit.commands
from pxr import Sdf, Usd, UsdShade

from ....config.logging import logger
from ..nodegraph_api import ensure_nodegraph_node_api, prim_from_attr
from ..stage_helper import UsdStageHelper

# pylint: disable=no-member

_Port = Union[UsdShade.Input, UsdShade.Output]


def _command_renamed_property(_command: object, result: object) -> bool:
    """Return whether rename produced a valid replacement attribute."""
    return bool(result)


@ensure_nodegraph_node_api(prim_from_attr("_prim_path"), should_apply=_command_renamed_property)
class MaterialGraph_RenamePropertyCommand(omni.kit.commands.Command, UsdStageHelper):
    """Rename a USD property while preserving metadata and connections."""

    def __init__(
        self, prim_path: Sdf.Path, property_name: str, new_name: str, stage: Optional[Usd.Stage] = None
    ) -> None:
        """Store rename parameters and optional stage override for undo/redo execution."""
        UsdStageHelper.__init__(self, stage)
        self._prim_path = prim_path
        self._property_name = str(property_name) if property_name is not None else ""
        self._new_name = str(new_name) if new_name is not None else ""
        self._failed = False

    def _get_connected_ports(self, prim: Usd.Prim, target_path: Sdf.Path) -> List[_Port]:
        """Return ports connected to the target path."""

        def get_root_container(container: Usd.Prim) -> Usd.Prim:
            """Return the highest connectable prim ancestor participating in graph wiring."""
            parent = container.GetParent()
            if (not parent) or parent.IsPseudoRoot() or (not UsdShade.ConnectableAPI(parent)):
                return container
            return get_root_container(parent)

        def get_all_children(container: Usd.Prim) -> List[Usd.Prim]:
            """Collect recursive child prims so nested nodegraphs are included in rewiring."""
            children = container.GetAllChildren()
            for child in children:
                if child.IsA(UsdShade.NodeGraph):
                    children.extend(get_all_children(child))
            return children

        def is_port_connected(usdshade_port: _Port, target: Sdf.Path) -> bool:
            """Return whether a port currently sources from the specific target property path."""
            sources_result = usdshade_port.GetConnectedSources()
            sources = sources_result[0] if isinstance(sources_result, tuple) else sources_result
            for connection_source_info in sources:
                is_input = connection_source_info.sourceType == UsdShade.AttributeType.Input
                source_name_prefix = UsdShade.Tokens.inputs if is_input else UsdShade.Tokens.outputs
                prop_name = f"{source_name_prefix}{connection_source_info.sourceName}"
                source_path = connection_source_info.source.GetPrim().GetPath().AppendProperty(prop_name)
                if source_path == target:
                    return True
            return False

        root_container = get_root_container(prim)
        prims_to_check = [root_container] + get_all_children(root_container)

        connected_ports: List[_Port] = []
        for child in prims_to_check:
            api = UsdShade.ConnectableAPI(child)
            if not api:
                continue
            ports: Sequence[_Port] = api.GetOutputs() + api.GetInputs()
            connected_ports.extend([port for port in ports if is_port_connected(port, target_path)])

        return connected_ports

    @staticmethod
    def _restore_connections(snapshots: Sequence[tuple[Usd.Attribute, Sequence[Sdf.Path]]]) -> None:
        """Best-effort restore dependent connection lists after an aborted rename."""
        for dependent_attr, paths in snapshots:
            dependent_attr.SetConnections(list(paths))

    def _rename_property(self, from_name: str, to_name: str) -> Optional[Usd.Attribute]:
        """Rename a prim property while preserving authored value, metadata, and links."""
        stage = self._get_stage()
        if not stage:
            return

        prim = stage.GetPrimAtPath(self._prim_path)
        if not prim:
            return

        attr = prim.GetAttribute(from_name)
        if not attr:
            return
        if from_name == to_name:
            return attr
        existing_attr = prim.GetAttribute(to_name)
        if existing_attr:
            logger.warning("rename property skipped: %s already exists", to_name)
            return

        edit_target = stage.GetEditTarget()
        layer = edit_target.GetLayer()
        source_spec_path = edit_target.MapToSpecPath(attr.GetPath())
        source_spec = layer.GetAttributeAtPath(source_spec_path)
        if not source_spec:
            logger.warning("rename property skipped: %s is not authored in the edit target", attr.GetPath())
            return
        target_spec_path = source_spec_path.GetParentPath().AppendProperty(to_name)
        if layer.GetObjectAtPath(target_spec_path):
            logger.warning("rename property skipped: %s already exists in the edit target", target_spec_path)
            return

        ports_to_update = self._get_connected_ports(prim, attr.GetPath())
        connection_snapshots = [(port.GetAttr(), list(port.GetAttr().GetConnections())) for port in ports_to_update]
        if not Sdf.CopySpec(layer, source_spec_path, layer, target_spec_path):
            logger.warning("rename property failed: could not copy %s to %s", source_spec_path, target_spec_path)
            return

        new_attr = prim.GetAttribute(to_name)
        if not new_attr:
            prim.RemoveProperty(to_name)
            return
        for dependent_attr, original_paths in connection_snapshots:
            updated_paths = [new_attr.GetPath() if path == attr.GetPath() else path for path in original_paths]
            if not dependent_attr.SetConnections(updated_paths):
                self._restore_connections(connection_snapshots)
                prim.RemoveProperty(to_name)
                logger.warning("rename property failed: could not rewire %s", dependent_attr.GetPath())
                return

        if not prim.RemoveProperty(from_name):
            self._restore_connections(connection_snapshots)
            prim.RemoveProperty(to_name)
            logger.warning("rename property failed: could not remove %s", attr.GetPath())
            return
        return new_attr

    def do(self) -> Optional[Usd.Attribute]:
        """Apply rename from original property name to requested name."""
        if self._failed:
            return None
        renamed = self._rename_property(self._property_name, self._new_name)
        self._failed = not bool(renamed)
        return renamed

    def undo(self) -> None:
        """Reverse rename back to the original property name."""
        if not self._failed:
            self._rename_property(self._new_name, self._property_name)
