"""Polymorphic connection command helpers for MDL shader retargeting."""

from collections import deque
from typing import Dict, List, Optional, Union

import omni.kit.commands
import omni.UsdMdl
from pxr import Sdf, Tf, UsdShade

from ....config.logging import logger
from ....utils.sdr_wrappers import (
    SdrShaderNodeWrapper,
    compute_polymorphic_constraint_score,
    mdl_polymorphic_family_key,
    mdl_property_matches_polymorphic_constraint,
    resolve_output_value_type,
    resolve_property_type_name,
    wrap_shader_node,
    wrap_shader_nodes,
)
from ....utils.usd_names import strip_usd_namespace
from ..stage_helper import UsdStageHelper

# pylint: disable=no-member


class MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand(omni.kit.commands.Command, UsdStageHelper):
    """Connect ports with polymorphic MDL retargeting before final connection.

    Retargeting is applied to the source prim (when the source has an overload
    that matches the target port type) **and** to the target prim (when the
    target has an overload that matches the effective source port type).

    After the immediate connection, a cascade walk propagates the resolved
    type both upstream and downstream through connected polymorphic nodes so
    that a single concrete connection can resolve an entire chain.
    """

    MDL = "mdl"

    def __init__(
        self, target: Union[UsdShade.Input, UsdShade.Output], source: Union[UsdShade.Input, UsdShade.Output]
    ) -> None:
        """Initialize connect command state for polymorphic MDL retargeting."""
        target_prim = target.GetPrim() if target and callable(getattr(target, "GetPrim", None)) else None
        get_stage = getattr(target_prim, "GetStage", None)
        stage = get_stage() if callable(get_stage) else None
        UsdStageHelper.__init__(self, stage)
        self._target = target
        self._source = source
        self._subidentifier = ""
        self._new_subidentifier = ""
        self._target_subidentifier = ""
        self._target_new_subidentifier = ""
        self._cascade_log: List[tuple] = []
        self._source_interface_count = 0
        self._target_interface_start = 0
        self._target_interface_end = 0
        self._target_raw_source_paths: List[Sdf.Path] = []
        self._failed = False

    def _snapshot_target_connections(self) -> None:
        """Capture exact authored sources so failed edits and undo can restore them."""
        attr = self._target.GetAttr() if self._target else None
        self._target_raw_source_paths = list(attr.GetConnections()) if attr else []

    def _restore_target_connections(self, stage=None) -> None:
        """Restore the target's exact pre-command source paths."""
        stage = stage or self._get_stage()
        target = self._refresh_port_handle(self._target, stage) if stage else self._target
        attr = target.GetAttr() if target else None
        if not attr:
            return
        if self._target_raw_source_paths:
            attr.SetConnections(self._target_raw_source_paths)
        else:
            attr.ClearConnections()

    # -- overload discovery via asset registry ---------------------------------

    @classmethod
    def _get_overloads_for_prim(cls, prim) -> List[SdrShaderNodeWrapper]:
        """Return all overload SDR nodes for a polymorphic prim via asset registry.

        This mirrors the approach used by ``MdlPolymorphicResolver._get_cached_overloads``
        and avoids ``GetOverloads(prim, False)`` which only reliably returns
        overloads for the *source* prim in the original connect path.
        """
        shader = UsdShade.Shader(prim)
        if not shader:
            return []
        api = UsdShade.NodeDefAPI(prim)
        if not api:
            return []
        source_asset = api.GetSourceAsset("mdl")
        sub = api.GetSourceAssetSubIdentifier("mdl")
        if not source_asset or not sub:
            return []
        try:
            current_node = wrap_shader_node(omni.UsdMdl.RegistryUtils.GetShaderNode(source_asset, sub))
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.debug("Cannot resolve current SDR node for %s subidentifier '%s': %s", source_asset.path, sub, exc)
            return []
        family_key = mdl_polymorphic_family_key(current_node, str(sub))
        if not family_key:
            return []
        try:
            all_subs = omni.UsdMdl.RegistryUtils.GetSubIdentifiersForAsset(source_asset)
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.debug("Cannot list subidentifiers for MDL asset %s: %s", source_asset.path, exc)
            return []
        results: List[SdrShaderNodeWrapper] = []
        for s in all_subs or []:
            try:
                node = wrap_shader_node(omni.UsdMdl.RegistryUtils.GetShaderNode(source_asset, s))
            except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
                logger.debug("Cannot resolve SDR node for %s subidentifier '%s': %s", source_asset.path, s, exc)
                continue
            if node and mdl_polymorphic_family_key(node, str(s)) == family_key:
                results.append(node)
        return sorted(results, key=cls._overload_sort_key)

    # -- polymorphic state queries ---------------------------------------------

    @classmethod
    def _is_prim_polymorphic(cls, prim) -> bool:
        """Return True if *prim* has multiple overloads in the MDL registry."""
        return len(cls._get_overloads_for_prim(prim)) > 1

    @staticmethod
    def _is_prim_unresolved_polymorphic(prim) -> bool:
        """Return True if *prim* has multiple overloads that don't resolve to one."""
        try:
            all_overloads = omni.UsdMdl.RegistryUtils.GetOverloads(prim, False)
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.debug("GetOverloads(prim, False) failed for %s: %s", prim.GetPath(), exc)
            return False
        if not all_overloads or len(all_overloads) <= 1:
            return False
        try:
            resolved = omni.UsdMdl.RegistryUtils.GetOverloads(prim)
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.debug("GetOverloads(prim) failed for %s, treating as unresolved: %s", prim.GetPath(), exc)
            return True
        resolved_subs = set()
        for r in resolved or []:
            sub = r.GetSubIdentifier()
            if sub:
                resolved_subs.add(sub)
        return len(resolved_subs) != 1

    # -- overload resolution ---------------------------------------------------

    @staticmethod
    def _overload_sort_key(overload: SdrShaderNodeWrapper) -> str:
        """Return a stable key for deterministic overload selection."""
        for accessor in ("GetSubIdentifier", "GetIdentifier", "GetName"):
            try:
                value = getattr(overload, accessor)()
            except (RuntimeError, ValueError, TypeError, AttributeError):
                continue
            if value:
                return str(value)
        return ""

    def _get_overload(self) -> Optional[SdrShaderNodeWrapper]:
        """Choose an overload whose source port type matches the target port type."""
        overloads = wrap_shader_nodes(omni.UsdMdl.RegistryUtils.GetOverloads(self._source.GetPrim(), False))
        if not overloads:
            return
        overloads = sorted(overloads, key=self._overload_sort_key)

        source_attr_name = self._port_base_name(self._source)
        is_input = isinstance(self._source, UsdShade.Input)

        for oload in overloads:
            sdr_shader_property = (
                oload.GetShaderInput(source_attr_name) if is_input else oload.GetShaderOutput(source_attr_name)
            )
            if not sdr_shader_property:
                continue

            if mdl_property_matches_polymorphic_constraint(
                sdr_shader_property,
                str(self._target.GetAttr().GetTypeName()),
                is_input,
            ):
                return oload

    @classmethod
    def _find_overload_for_port(
        cls, prim, port_name: str, expected_type: str, is_input: bool
    ) -> Optional[SdrShaderNodeWrapper]:
        """Find an overload of *prim* where *port_name* has *expected_type*."""
        compatible = []
        for oload in cls._get_overloads_for_prim(prim):
            score = compute_polymorphic_constraint_score(oload, [(port_name, expected_type, is_input)])
            if score is not None:
                compatible.append((score, cls._overload_sort_key(oload), oload))
        if not compatible:
            return None
        compatible.sort(key=lambda item: (item[0], item[1]))
        return compatible[0][2]

    @classmethod
    def _port_base_name(cls, port: Union[UsdShade.Input, UsdShade.Output]) -> str:
        """Return a port's base attribute name without inputs/outputs prefix."""
        return strip_usd_namespace(port.GetAttr().GetName())

    @staticmethod
    def _is_nodegraph_interface_port(port: Union[UsdShade.Input, UsdShade.Output]) -> bool:
        """Return True when *port* belongs to a nodegraph interface."""
        prim = port.GetPrim() if port else None
        return bool(prim and prim.IsA(UsdShade.NodeGraph))

    @classmethod
    def _is_shader_port(cls, port: Union[UsdShade.Input, UsdShade.Output]) -> bool:
        """Return True when *port* belongs to a shader prim."""
        prim = port.GetPrim() if port else None
        return bool(prim and prim.IsA(UsdShade.Shader))

    @classmethod
    def _port_subidentifier(cls, port: Union[UsdShade.Input, UsdShade.Output], source_type: str) -> str:
        """Return the MDL source-asset subidentifier for shader ports."""
        if not cls._is_shader_port(port):
            return ""
        shader = UsdShade.Shader(port.GetPrim())
        return shader.GetSourceAssetSubIdentifier(source_type) if shader else ""

    @classmethod
    def _is_internal_nodegraph_interface_connection(
        cls,
        source: Union[UsdShade.Input, UsdShade.Output],
        target: Union[UsdShade.Input, UsdShade.Output],
    ) -> bool:
        """Return True for child shader <-> containing nodegraph interface wiring."""
        source_prim = source.GetPrim() if source else None
        target_prim = target.GetPrim() if target else None
        if not source_prim or not target_prim:
            return False
        return (
            cls._is_nodegraph_interface_port(target) and source_prim.GetParent().GetPath() == target_prim.GetPath()
        ) or (cls._is_nodegraph_interface_port(source) and target_prim.GetParent().GetPath() == source_prim.GetPath())

    @staticmethod
    def _connect_internal_nodegraph_interface(
        source: Union[UsdShade.Input, UsdShade.Output],
        target: Union[UsdShade.Input, UsdShade.Output],
    ) -> bool:
        """Connect direct child <-> nodegraph interface wiring without retargeting."""
        with Sdf.ChangeBlock():
            connected = bool(target.ConnectToSource(source))
        return connected and bool(target.HasConnectedSource())

    @staticmethod
    def _source_info_to_port(stage, source_info):
        """Resolve UsdShade source info to an input/output port object."""
        prefix = (
            UsdShade.Tokens.inputs
            if source_info.sourceType == UsdShade.AttributeType.Input
            else UsdShade.Tokens.outputs
        )
        attr = stage.GetAttributeAtPath(
            source_info.source.GetPath().AppendProperty(f"{prefix}{source_info.sourceName}")
        )
        if not attr:
            return None
        if source_info.sourceType == UsdShade.AttributeType.Input:
            return UsdShade.Input(attr)
        return UsdShade.Output(attr)

    @classmethod
    def _iter_nodegraph_forwarded_ports(
        cls,
        stage,
        interface_port: Union[UsdShade.Input, UsdShade.Output],
        visited: Optional[set] = None,
    ) -> List[Union[UsdShade.Input, UsdShade.Output]]:
        """Return internal ports represented by a nodegraph interface port."""
        if visited is None:
            visited = set()
        attr = interface_port.GetAttr() if interface_port else None
        if not attr:
            return []
        attr_path = attr.GetPath()
        if attr_path in visited:
            return []
        visited.add(attr_path)

        prim = interface_port.GetPrim()
        if not (prim and prim.IsA(UsdShade.NodeGraph)):
            return [interface_port]

        forwarded: List[Union[UsdShade.Input, UsdShade.Output]] = []
        interface_name = cls._port_base_name(interface_port)
        if isinstance(interface_port, UsdShade.Input):
            interface_attr_name = f"{UsdShade.Tokens.inputs}{interface_name}"
            for child in prim.GetChildren():
                api = UsdShade.ConnectableAPI(child)
                if not api:
                    continue
                for child_input in api.GetInputs():
                    try:
                        raw_paths = child_input.GetRawConnectedSourcePaths()
                    except (RuntimeError, ValueError, TypeError, AttributeError):
                        continue
                    if not any(
                        raw_path.GetPrimPath() == prim.GetPath() and str(raw_path.name) == interface_attr_name
                        for raw_path in raw_paths
                    ):
                        continue
                    if child_input.GetPrim().IsA(UsdShade.NodeGraph):
                        forwarded.extend(cls._iter_nodegraph_forwarded_ports(stage, child_input, visited))
                    else:
                        forwarded.append(child_input)
            return forwarded

        sources_result = interface_port.GetConnectedSources()
        sources = sources_result[0] if isinstance(sources_result, tuple) else sources_result
        for source_info in sources or []:
            source_port = cls._source_info_to_port(stage, source_info)
            if not source_port:
                continue
            if source_port.GetPrim().IsA(UsdShade.NodeGraph):
                forwarded.extend(cls._iter_nodegraph_forwarded_ports(stage, source_port, visited))
            else:
                forwarded.append(source_port)
        return forwarded

    def _retarget_nodegraph_interface(
        self,
        interface_port: Union[UsdShade.Input, UsdShade.Output],
        expected_type: str,
        start_prims: List[object],
    ) -> None:
        """Retarget polymorphic internal ports represented by a nodegraph interface."""
        if not self._is_nodegraph_interface_port(interface_port):
            return
        stage = self._get_stage()
        for forwarded_port in self._iter_nodegraph_forwarded_ports(stage, interface_port):
            prim = forwarded_port.GetPrim()
            if not (prim and prim.IsValid() and self._is_prim_polymorphic(prim)):
                continue
            port_name = self._port_base_name(forwarded_port)
            is_input = isinstance(forwarded_port, UsdShade.Input)
            compatible = self._narrow_overloads(prim, [(port_name, expected_type, is_input)])
            if not compatible:
                continue
            old_sub = UsdShade.Shader(prim).GetSourceAssetSubIdentifier(self.MDL)
            new_sub = compatible[0].GetSubIdentifier()
            if not new_sub or new_sub == old_sub:
                continue
            self._cascade_log.append((str(prim.GetPath()), old_sub))
            self._retarget_prim(prim, new_sub, compatible[0], stage)
            start_prims.append(prim)

    def _effective_interface_type(self, port: Union[UsdShade.Input, UsdShade.Output], fallback_type: str) -> str:
        """Return the concrete internal type for a nodegraph interface when unambiguous."""
        if not self._is_nodegraph_interface_port(port):
            return fallback_type
        stage = self._get_stage()
        forwarded_types = {
            str(forwarded.GetAttr().GetTypeName())
            for forwarded in self._iter_nodegraph_forwarded_ports(stage, port)
            if forwarded and forwarded.GetAttr()
        }
        return next(iter(forwarded_types)) if len(forwarded_types) == 1 else fallback_type

    def _restore_logged_retargets(self, stage, entries: List[tuple]) -> None:
        """Restore logged prim retargets in reverse order."""
        for prim_path, old_sub in reversed(entries):
            prim = stage.GetPrimAtPath(Sdf.Path(prim_path))
            if prim and prim.IsValid():
                if not self._retarget_prim(prim, old_sub, None, stage):
                    logger.warning(
                        "failed to restore polymorphic prim '%s' to subidentifier='%s'; graph may require reload",
                        prim_path,
                        old_sub,
                    )

    def _rollback_retargets(self, stage, source_interface_count: int, target_interface_start: int) -> None:
        """Best-effort restore of retargets made before a failed connection."""
        if self._target_subidentifier != self._target_new_subidentifier:
            if not self._update_target_prim(self._target_subidentifier):
                logger.warning(
                    "failed to restore target polymorphic prim '%s' to subidentifier='%s'; graph may require reload",
                    self._prim_path_for_log(self._target),
                    self._target_subidentifier,
                )
        self._restore_logged_retargets(stage, self._cascade_log[target_interface_start:])
        if self._subidentifier != self._new_subidentifier:
            if not self._update_shader_prim(self._subidentifier):
                logger.warning(
                    "failed to restore source polymorphic prim '%s' to subidentifier='%s'; graph may require reload",
                    self._prim_path_for_log(self._source),
                    self._subidentifier,
                )
        self._restore_logged_retargets(stage, self._cascade_log[:source_interface_count])
        self._cascade_log = []
        self._new_subidentifier = self._subidentifier
        self._target_new_subidentifier = self._target_subidentifier
        self._source_interface_count = 0
        self._target_interface_start = 0
        self._target_interface_end = 0

    @staticmethod
    def _refresh_port_handle(port: Union[UsdShade.Input, UsdShade.Output], stage):
        """Return a fresh port wrapper for the same attribute path when available."""
        try:
            attr = stage.GetAttributeAtPath(port.GetAttr().GetPath())
        except (RuntimeError, ValueError, TypeError, AttributeError):
            attr = None
        if not attr:
            return port
        return UsdShade.Input(attr) if isinstance(port, UsdShade.Input) else UsdShade.Output(attr)

    @staticmethod
    def _port_path_for_log(port: object) -> str:
        """Return a port path without allowing diagnostics to mask the original failure."""
        try:
            attribute = port.GetAttr()
            path = attribute.GetPath()
            return str(path)
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return str(getattr(port, "path", "<unknown>"))

    @staticmethod
    def _prim_path_for_log(port: object) -> str:
        """Return an owning prim path without risking a secondary logging failure."""
        try:
            prim = port.GetPrim()
            return str(prim.GetPath())
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return "<unknown>"

    # -- prim mutation ---------------------------------------------------------

    def _update_shader_prim(
        self, subidentifier: str, sdr_node: Optional[SdrShaderNodeWrapper] = None
    ) -> Optional[Union[UsdShade.Input, UsdShade.Output]]:
        """Rebuild shader outputs and inputs for a subidentifier and return refreshed source port."""
        prim = self._source.GetPrim()
        stage = self._get_stage()
        source_path = self._source.GetAttr().GetPath()

        if not self._retarget_prim(prim, subidentifier, sdr_node, stage):
            return None

        source_attr = stage.GetAttributeAtPath(source_path)
        is_input = isinstance(self._source, UsdShade.Input)
        return UsdShade.Input(source_attr) if is_input else UsdShade.Output(source_attr)

    @classmethod
    def _retarget_prim(
        cls,
        prim,
        subidentifier: str,
        sdr_node: Optional[SdrShaderNodeWrapper],
        stage,
        skip_port_path: Optional[Sdf.Path] = None,
    ) -> bool:
        """Retarget *prim* to *subidentifier*, preserving input connections.

        When *skip_port_path* is set, that specific input's connection is not
        restored (the caller is about to wire it explicitly).
        """
        shader = UsdShade.Shader(prim)

        saved_input_connections: Dict[str, List[Sdf.Path]] = {}
        for inp in shader.GetInputs():
            if skip_port_path and inp.GetAttr().GetPath() == skip_port_path:
                continue
            raw_paths = inp.GetRawConnectedSourcePaths()
            if raw_paths:
                saved_input_connections[inp.GetBaseName()] = list(raw_paths)

        for output in shader.GetOutputs():
            attr = output.GetAttr()
            if attr:
                prim.RemoveProperty(attr.GetName())
        for inp in shader.GetInputs():
            attr = inp.GetAttr()
            if attr:
                prim.RemoveProperty(attr.GetName())

        shader.SetSourceAssetSubIdentifier(subidentifier, cls.MDL)

        if not sdr_node:
            sdr_node = wrap_shader_node(omni.UsdMdl.RegistryUtils.GetShaderNodeForPrim(prim))
            if not sdr_node:
                return False

        for output_name in sdr_node.GetShaderOutputNames():
            sdr_prop = sdr_node.GetShaderOutput(output_name)
            shader.CreateOutput(output_name, resolve_output_value_type(sdr_prop))

        for input_name in sdr_node.GetShaderInputNames():
            sdr_prop = sdr_node.GetShaderInput(input_name)
            new_input = shader.CreateInput(input_name, resolve_output_value_type(sdr_prop))
            if input_name in saved_input_connections:
                for source_path in saved_input_connections[input_name]:
                    source_attr = stage.GetAttributeAtPath(source_path)
                    if not source_attr:
                        continue
                    if UsdShade.Output.IsOutput(source_attr):
                        new_input.ConnectToSource(UsdShade.Output(source_attr))
                    else:
                        new_input.ConnectToSource(UsdShade.Input(source_attr))

        return True

    def _update_target_prim(
        self, subidentifier: str, sdr_node: Optional[SdrShaderNodeWrapper] = None
    ) -> Optional[Union[UsdShade.Input, UsdShade.Output]]:
        """Rebuild shader ports for the target prim and return refreshed target port."""
        prim = self._target.GetPrim()
        is_input = isinstance(self._target, UsdShade.Input)
        target_path = self._target.GetAttr().GetPath()
        stage = self._get_stage()

        if not self._retarget_prim(prim, subidentifier, sdr_node, stage):
            return None

        target_attr = stage.GetAttributeAtPath(target_path)
        return UsdShade.Input(target_attr) if is_input else UsdShade.Output(target_attr)

    # -- cascade ---------------------------------------------------------------

    def _cascade_retarget(self, start_prims, stage) -> None:
        """Walk the connection graph from *start_prims* and retarget connected polymorphic nodes.

        For each retargeted prim the walk checks both directions:

        * **Upstream** -- inputs connected to polymorphic sources whose output
          type no longer matches are retargeted to produce the expected type.
        * **Downstream** -- sibling prims whose inputs consume an output of the
          retargeted prim are retargeted to accept the new type.
        """
        queue = deque(start_prims)
        visited = {str(p.GetPath()) for p in start_prims}

        while queue:
            prim = queue.popleft()
            shader = UsdShade.Shader(prim)
            sdr_node = wrap_shader_node(omni.UsdMdl.RegistryUtils.GetShaderNodeForPrim(prim))
            if not shader or not sdr_node:
                continue

            self._cascade_upstream(prim, shader, sdr_node, stage, visited, queue)
            self._cascade_downstream(prim, sdr_node, stage, visited, queue)

    def _cascade_upstream(self, prim, shader, sdr_node, stage, visited, queue) -> None:
        """Retarget polymorphic sources whose output type mismatches the prim's input type."""
        for inp in shader.GetInputs():
            if not inp.HasConnectedSource():
                continue
            input_name = inp.GetBaseName()
            sdr_inp = sdr_node.GetShaderInput(input_name)
            if not sdr_inp:
                continue
            expected_type = resolve_property_type_name(sdr_inp)

            try:
                source_connectable, _, _ = inp.GetConnectedSource()
                source_prim = source_connectable.GetPrim() if source_connectable else None
            except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
                logger.debug("Cannot resolve connected source for %s.inputs:%s: %s", prim.GetPath(), input_name, exc)
                continue
            if not source_prim or not source_prim.IsValid():
                continue
            sp = str(source_prim.GetPath())
            if sp in visited:
                continue
            if not self._is_prim_polymorphic(source_prim):
                continue

            raw_paths = inp.GetRawConnectedSourcePaths()
            output_name = None
            for rp in raw_paths:
                if rp.GetPrimPath() == source_prim.GetPath():
                    output_name = strip_usd_namespace(rp.name)
                    break
            if not output_name:
                continue

            try:
                new_oload = self._find_overload_for_port(source_prim, output_name, expected_type, False)
                if not new_oload:
                    continue
                old_sub = UsdShade.Shader(source_prim).GetSourceAssetSubIdentifier(self.MDL)
                new_sub = new_oload.GetSubIdentifier()
                if old_sub == new_sub:
                    continue

                self._cascade_log.append((sp, old_sub))
                self._retarget_prim(source_prim, new_sub, new_oload, stage)
                visited.add(sp)
                queue.append(source_prim)
            except Exception:  # pylint: disable=broad-exception-caught
                logger.warning(
                    "Polymorphic cascade failed to retarget upstream node %s "
                    "(expected output '%s' to produce type '%s')",
                    sp,
                    output_name,
                    expected_type,
                    exc_info=True,
                )

    def _cascade_downstream(self, prim, sdr_node, stage, visited, queue) -> None:
        """Retarget polymorphic consumers whose input type mismatches the prim's output type."""
        prim_path = prim.GetPath()
        parent = prim.GetParent()
        if not parent:
            return

        for sibling in parent.GetChildren():
            sib_str = str(sibling.GetPath())
            if sib_str in visited:
                continue
            sib_shader = UsdShade.Shader(sibling)
            if not sib_shader:
                continue
            if not self._is_prim_polymorphic(sibling):
                continue

            for sib_inp in sib_shader.GetInputs():
                if not sib_inp.HasConnectedSource():
                    continue
                raw_paths = sib_inp.GetRawConnectedSourcePaths()
                for rp in raw_paths:
                    if rp.GetPrimPath() != prim_path:
                        continue
                    output_name = strip_usd_namespace(rp.name)
                    sdr_out = sdr_node.GetShaderOutput(output_name)
                    if not sdr_out:
                        break
                    expected = resolve_property_type_name(sdr_out)
                    input_name = sib_inp.GetBaseName()
                    try:
                        new_oload = self._find_overload_for_port(sibling, input_name, expected, True)
                        if not new_oload:
                            break
                        old_sub = UsdShade.Shader(sibling).GetSourceAssetSubIdentifier(self.MDL)
                        new_sub = new_oload.GetSubIdentifier()
                        if old_sub == new_sub:
                            break
                        self._cascade_log.append((sib_str, old_sub))
                        self._retarget_prim(sibling, new_sub, new_oload, stage)
                        visited.add(sib_str)
                        queue.append(sibling)
                    except Exception:  # pylint: disable=broad-exception-caught
                        logger.warning(
                            "Polymorphic cascade failed to retarget downstream node %s "
                            "(expected input '%s' to accept type '%s')",
                            sib_str,
                            input_name,
                            expected,
                            exc_info=True,
                        )
                    break

    # -- command execution / undo ----------------------------------------------

    @classmethod
    def _get_connected_port_constraints(cls, prim) -> List[tuple]:
        """Return [(port_name, expected_type, is_input), ...] for non-polymorphic connected ports on *prim*.

        Constraints from polymorphic neighbors are skipped because their
        port types may be stale artifacts of a previous retarget.
        """
        shader = UsdShade.Shader(prim)
        if not shader:
            return []
        constraints = []
        prim_path = prim.GetPath()
        parent = prim.GetParent()

        # Input constraints: upstream non-polymorphic source type constrains this input.
        for inp in shader.GetInputs():
            if not inp.HasConnectedSource():
                continue
            port_name = inp.GetBaseName()
            try:
                source_connectable, source_name, _ = inp.GetConnectedSource()
                if not source_connectable:
                    continue
                source_prim = source_connectable.GetPrim()
                if (
                    source_prim
                    and parent
                    and source_prim.GetPath() == parent.GetPath()
                    and source_prim.IsA(UsdShade.NodeGraph)
                ):
                    # The containing NodeGraph input mirrors the child input's
                    # current type. It is not a concrete constraint until the
                    # interface itself has an external source; the in-flight
                    # connection supplies that constraint via extra_constraints.
                    continue
                if source_prim and cls._is_prim_polymorphic(source_prim):
                    continue
                source_attr = source_connectable.GetOutput(source_name) if source_name else None
                if not source_attr:
                    source_attr = source_connectable.GetInput(source_name) if source_name else None
                if source_attr:
                    constraints.append((port_name, str(source_attr.GetTypeName()), True))
            except (RuntimeError, ValueError, TypeError, AttributeError):
                pass

        # Output constraints: downstream non-polymorphic consumer's input type constrains this output.
        if parent:
            for sibling in parent.GetChildren():
                if sibling.GetPath() == prim_path:
                    continue
                if cls._is_prim_polymorphic(sibling):
                    continue
                sib_shader = UsdShade.Shader(sibling)
                if not sib_shader:
                    continue
                for sib_inp in sib_shader.GetInputs():
                    if not sib_inp.HasConnectedSource():
                        continue
                    try:
                        raw_paths = sib_inp.GetRawConnectedSourcePaths()
                        for rp in raw_paths:
                            if rp.GetPrimPath() == prim_path:
                                output_name = strip_usd_namespace(rp.name)
                                constraints.append((output_name, str(sib_inp.GetTypeName()), False))
                    except (RuntimeError, ValueError, TypeError, AttributeError):
                        pass

        return constraints

    @classmethod
    def _narrow_overloads(
        cls,
        prim,
        extra_constraints: Optional[List[tuple]] = None,
    ) -> List[SdrShaderNodeWrapper]:
        """Return overloads of *prim* compatible with all connected port types.

        *extra_constraints* is a list of ``(port_name, expected_type, is_input)``
        tuples for the connection being made (not yet visible via USD queries).
        """
        all_overloads = cls._get_overloads_for_prim(prim)
        if not all_overloads:
            return []
        constraints = cls._get_connected_port_constraints(prim)
        if extra_constraints:
            constraints.extend(extra_constraints)
        if not constraints:
            return all_overloads
        compatible = []
        for oload in all_overloads:
            score = compute_polymorphic_constraint_score(oload, constraints)
            if score is not None:
                compatible.append((score, cls._overload_sort_key(oload), oload))
        compatible.sort(key=lambda item: (item[0], item[1]))
        return [oload for _, _, oload in compatible]

    def do(self) -> bool:
        """Retarget polymorphic prims to a compatible overload, then connect.

        All connections on the polymorphic prim (including the new one) are
        used to narrow the overload set.  The prim is always retargeted to
        the first compatible overload so that port types match.  The resolver
        independently determines concrete/unresolved status based on how
        many overloads remain compatible.
        """
        if self._failed:
            return False
        source = self._source
        target = self._target
        self._snapshot_target_connections()

        if self._is_internal_nodegraph_interface_connection(
            source, target
        ) and self._connect_internal_nodegraph_interface(source, target):
            return True

        source_is_shader = self._is_shader_port(self._source)
        target_is_shader = self._is_shader_port(self._target)
        self._subidentifier = self._port_subidentifier(self._source, self.MDL)
        self._target_subidentifier = self._port_subidentifier(self._target, self.MDL)

        self._new_subidentifier = self._subidentifier
        self._target_new_subidentifier = self._target_subidentifier
        self._cascade_log = []
        self._source_interface_count = 0
        self._target_interface_start = 0
        self._target_interface_end = 0

        # Build constraints for the connection being made.
        src_attr_name = self._port_base_name(self._source)
        tgt_attr_name = self._port_base_name(self._target)
        src_is_input = isinstance(self._source, UsdShade.Input)
        tgt_is_input = isinstance(self._target, UsdShade.Input)
        target_type = str(self._target.GetAttr().GetTypeName())
        source_type = str(self._source.GetAttr().GetTypeName())

        with Sdf.ChangeBlock():
            stage = self._get_stage()
            start_prims = []
            source_type = self._effective_interface_type(self._source, source_type)
            target_type = self._effective_interface_type(self._target, target_type)

            # A nodegraph interface port can stand in for an internal
            # polymorphic shader port. Push concrete external constraints
            # through that interface before authoring the new connection.
            self._retarget_nodegraph_interface(self._source, target_type, start_prims)
            source_interface_count = len(self._cascade_log)
            self._source_interface_count = source_interface_count
            source_type = self._effective_interface_type(self._source, source_type)

            # Step 1: retarget the source prim if polymorphic.
            if source_is_shader and self._is_prim_polymorphic(self._source.GetPrim()):
                extra = [(src_attr_name, target_type, src_is_input)]
                compatible = self._narrow_overloads(self._source.GetPrim(), extra)
                if compatible:
                    self._new_subidentifier = compatible[0].GetSubIdentifier()
                    if self._new_subidentifier and self._new_subidentifier != self._subidentifier:
                        source = self._update_shader_prim(self._new_subidentifier, compatible[0])
                        start_prims.append(self._source.GetPrim())
                else:
                    self._rollback_retargets(stage, source_interface_count, source_interface_count)
                    self._failed = True
                    return False

            source_type = str(source.GetAttr().GetTypeName()) if source else source_type
            target_interface_start = len(self._cascade_log)
            self._target_interface_start = target_interface_start
            self._retarget_nodegraph_interface(self._target, source_type, start_prims)
            self._target_interface_end = len(self._cascade_log)
            target_type = self._effective_interface_type(self._target, target_type)

            # Step 2: retarget the target prim if polymorphic.
            if target_is_shader and self._is_prim_polymorphic(self._target.GetPrim()):
                extra = [(tgt_attr_name, source_type, tgt_is_input)]
                compatible = self._narrow_overloads(self._target.GetPrim(), extra)
                if compatible:
                    self._target_new_subidentifier = compatible[0].GetSubIdentifier()
                    if self._target_new_subidentifier and self._target_new_subidentifier != self._target_subidentifier:
                        target = self._update_target_prim(self._target_new_subidentifier, compatible[0])
                        start_prims.append(self._target.GetPrim())
                else:
                    self._rollback_retargets(stage, source_interface_count, target_interface_start)
                    self._failed = True
                    return False

            # Step 3: make the connection.
            try:
                connected = bool(source) and bool(target) and bool(target.ConnectToSource(source))
            except (RuntimeError, ValueError, TypeError, Tf.ErrorException) as exc:
                logger.warning(
                    "failed to author polymorphic connection source='%s' target='%s': %s; "
                    "retargeting will be rolled back",
                    self._port_path_for_log(self._source),
                    self._port_path_for_log(self._target),
                    exc,
                )
                connected = False
            if not connected:
                self._rollback_retargets(stage, source_interface_count, target_interface_start)
                self._restore_target_connections(stage)
                self._failed = True
                return False

            # Step 4: cascade only if a retarget actually happened.
            if start_prims:
                self._cascade_retarget(start_prims, stage)

            return True

    def undo(self) -> None:
        """Disconnect and restore the previous shader subidentifiers when changed."""
        if self._failed:
            return
        with Sdf.ChangeBlock():
            stage = self._get_stage()
            self._restore_logged_retargets(stage, self._cascade_log[self._target_interface_end :])

            if self._target_subidentifier != self._target_new_subidentifier:
                if not self._update_target_prim(self._target_subidentifier):
                    logger.warning(
                        "polymorphic connection undo could not restore target prim '%s' to subidentifier='%s'",
                        self._prim_path_for_log(self._target),
                        self._target_subidentifier,
                    )

            self._restore_logged_retargets(
                stage, self._cascade_log[self._target_interface_start : self._target_interface_end]
            )

            if self._subidentifier != self._new_subidentifier:
                if not self._update_shader_prim(self._subidentifier):
                    logger.warning(
                        "polymorphic connection undo could not restore source prim '%s' to subidentifier='%s'",
                        self._prim_path_for_log(self._source),
                        self._subidentifier,
                    )

            self._restore_logged_retargets(stage, self._cascade_log[: self._source_interface_count])
            self._restore_target_connections(stage)
