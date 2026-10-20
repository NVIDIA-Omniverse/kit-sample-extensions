"""Implement material graph extension logic for `plugins/impl/mdl/polymorphic.py`."""

from typing import Optional, Sequence, Tuple

import omni.UsdMdl
from pxr import Sdf, Usd, UsdShade

from ....config.logging import logger
from ....utils.sdr_wrappers import (
    compute_polymorphic_constraint_score,
    mdl_node_matches_polymorphic_constraints,
    mdl_polymorphic_family_key,
    resolve_property_type_name,
    wrap_shader_node,
)
from ....utils.usd_names import strip_usd_namespace
from ...core.polymorphic_state import PolymorphicState


class MdlPolymorphicResolver:
    """MDL polymorphic state resolver.

    This class is intentionally query-only. It computes polymorphic state and
    tentative compatibility, but does not mutate USD prims. Connect-time
    mutation is owned by the polymorphic connect command.
    """

    _MAX_CONSUMER_SEARCH_DEPTH = 8
    _MAX_RUNTIME_CACHE_ENTRIES = 8192

    def __init__(self, source_type: str) -> None:
        """Initialize instance state for this material graph component."""

        self._source_type = source_type
        self._family_overloads: dict[tuple[str, str], tuple[str, ...]] = {}
        self._runtime_epoch = 0
        self._narrow_cache: dict[tuple[int, str, tuple[str, ...]], tuple[str, ...]] = {}
        self._narrow_in_progress: set[tuple[int, str, tuple[str, ...]]] = set()
        self._known_port_type_cache: dict[tuple[int, str, str, bool], Optional[str]] = {}
        self._resolved_overloads_cache: dict[tuple[int, str], tuple[str, ...]] = {}
        self._polymorphic_family_cache: dict[tuple[int, str], bool] = {}
        self._sdr_node_cache: dict[tuple[str, str], Optional[object]] = {}
        self._graph_connection_indexes: dict[str, dict[str, dict[str, list[tuple]]]] = {}

    def clear_catalog_cache(self) -> None:
        """Clear overload families rebuilt from the catalog."""
        self.unregister_all_overloads()

    def unregister_all_overloads(self) -> None:
        """Clear registered overload families."""
        self._family_overloads.clear()
        self._sdr_node_cache.clear()
        self.invalidate_runtime_cache()

    def invalidate_runtime_cache(self) -> None:
        """Drop sync-time memoized polymorphic graph analysis."""
        self._invalidate_analysis_cache()
        self._graph_connection_indexes.clear()

    def _invalidate_analysis_cache(self) -> None:
        """Drop cached graph-analysis results while preserving catalog and SDR data."""
        self._runtime_epoch += 1
        self._narrow_cache.clear()
        self._narrow_in_progress.clear()
        self._known_port_type_cache.clear()
        self._resolved_overloads_cache.clear()
        self._polymorphic_family_cache.clear()

    def _get_sdr_node(self, source_asset: Sdf.AssetPath, subidentifier: str) -> Optional[object]:
        """Return a cached SDR node for one MDL overload."""
        source_key = self._source_asset_key(source_asset)
        if not source_key or not subidentifier:
            return None
        cache_key = (source_key, str(subidentifier))
        if cache_key in self._sdr_node_cache:
            return self._sdr_node_cache[cache_key]
        try:
            sdr_node = wrap_shader_node(omni.UsdMdl.RegistryUtils.GetShaderNode(source_asset, subidentifier))
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
            logger.debug("GetShaderNode failed for %s %s: %s", source_key, subidentifier, exc)
            sdr_node = None
        if sdr_node is not None:
            self._store_runtime_cache_value(self._sdr_node_cache, cache_key, sdr_node)
        return sdr_node

    def _store_runtime_cache_value(self, cache: dict, key: object, value: object) -> None:
        """Store one runtime cache value with a conservative bounded size policy."""
        cache[key] = value
        if len(cache) > self._MAX_RUNTIME_CACHE_ENTRIES:
            cache.pop(next(iter(cache)), None)

    @staticmethod
    def _new_graph_connection_index() -> dict[str, dict[str, list[tuple]]]:
        """Create the reusable connection constraint buckets for one nodegraph."""
        return {
            "input_constraints": {},
            "output_constraints": {},
            "poly_input_neighbors": {},
            "poly_output_neighbors": {},
            "interface_constraints": {},
        }

    @staticmethod
    def _append_index_entry(index: dict[str, dict[str, list[tuple]]], bucket: str, prim_key: str, entry: tuple) -> None:
        """Append a de-duplicated graph-index entry."""
        entries = index[bucket].setdefault(prim_key, [])
        if entry not in entries:
            entries.append(entry)

    @staticmethod
    def _port_name_from_source_path(path: Sdf.Path) -> str:
        """Return the bare port name from a raw UsdShade source path."""
        return strip_usd_namespace(str(path.name))

    def cache_graph_connection_index(self, nodegraph_prim: Optional[Usd.Prim]) -> None:
        """Precompute connection constraints for all direct children of one nodegraph."""
        if not nodegraph_prim or not nodegraph_prim.IsValid():
            return
        graph_key = str(nodegraph_prim.GetPath())
        if graph_key in self._graph_connection_indexes:
            self._graph_connection_indexes.pop(graph_key, None)
            self._invalidate_analysis_cache()
        index = self._new_graph_connection_index()
        try:
            children = [child for child in nodegraph_prim.GetChildren() if UsdShade.Shader(child)]
        except (RuntimeError, ValueError, TypeError, AttributeError):
            children = []
        child_paths = {child.GetPath() for child in children}

        for child in children:
            child_key = str(child.GetPath())
            shader = UsdShade.Shader(child)
            is_child_poly = self._is_prim_in_polymorphic_family(child)
            for inp in shader.GetInputs():
                if not inp.HasConnectedSource():
                    continue
                input_name = inp.GetBaseName()
                try:
                    source_connectable, source_name, _ = inp.GetConnectedSource()
                    source_prim = source_connectable.GetPrim() if source_connectable else None
                except (RuntimeError, ValueError, TypeError, AttributeError):
                    source_connectable = None
                    source_name = None
                    source_prim = None

                if source_prim and source_prim.IsValid():
                    source_path = source_prim.GetPath()
                    if not (source_path == nodegraph_prim.GetPath() and source_prim.IsA(UsdShade.NodeGraph)):
                        if source_path in child_paths and self._is_prim_in_polymorphic_family(source_prim):
                            source_port = (
                                str(source_name)
                                .removeprefix(UsdShade.Tokens.inputs)
                                .removeprefix(UsdShade.Tokens.outputs)
                                if source_name
                                else ""
                            )
                            if source_port:
                                self._append_index_entry(
                                    index,
                                    "poly_input_neighbors",
                                    child_key,
                                    (input_name, str(source_path), source_port),
                                )
                        else:
                            source_attr = (
                                source_connectable.GetOutput(source_name)
                                if source_connectable and source_name
                                else None
                            )
                            if not source_attr and source_connectable and source_name:
                                source_attr = source_connectable.GetInput(source_name)
                            if source_attr:
                                self._append_index_entry(
                                    index,
                                    "input_constraints",
                                    child_key,
                                    (input_name, str(source_attr.GetTypeName()), True),
                                )

                for raw_source_path in self._connected_source_paths(inp):
                    source_prim_path = raw_source_path.GetPrimPath()
                    if source_prim_path not in child_paths:
                        continue
                    source_key = str(source_prim_path)
                    output_name = self._port_name_from_source_path(raw_source_path)
                    if not output_name:
                        continue
                    if is_child_poly:
                        self._append_index_entry(
                            index,
                            "poly_output_neighbors",
                            source_key,
                            (output_name, child_key, input_name),
                        )
                    else:
                        self._append_index_entry(
                            index,
                            "output_constraints",
                            source_key,
                            (output_name, str(inp.GetTypeName()), False),
                        )

        self._append_indexed_nodegraph_interface_constraints(nodegraph_prim, index)
        self._graph_connection_indexes[graph_key] = index

    def _get_graph_connection_index(self, prim: Usd.Prim) -> Optional[dict[str, dict[str, list[tuple]]]]:
        """Return or lazily build the parent nodegraph connection index for a prim."""
        parent = prim.GetParent() if prim and prim.IsValid() else None
        if not parent:
            return None
        parent_key = str(parent.GetPath())
        index = self._graph_connection_indexes.get(parent_key)
        if index is not None:
            return index
        if parent.IsA(UsdShade.NodeGraph) or parent.IsA(UsdShade.Material):
            self.cache_graph_connection_index(parent)
            return self._graph_connection_indexes.get(parent_key)
        return None

    @staticmethod
    def _source_asset_key(source_asset: Sdf.AssetPath) -> str:
        """Execute source asset key behavior for material graph workflows."""

        return str(source_asset.path) if source_asset else ""

    @staticmethod
    def _base_name_from_subidentifier(subidentifier: Optional[str]) -> str:
        """Execute base name from subidentifier behavior for material graph workflows."""

        if not subidentifier:
            return ""
        return subidentifier.split("(")[0].strip()

    @staticmethod
    def _normalize_overload_subidentifier(overload: object) -> Optional[str]:
        """Execute normalize overload subidentifier behavior for material graph workflows."""

        if isinstance(overload, str):
            return overload
        if overload is None:
            return None
        get_identifier = getattr(overload, "GetIdentifier", None)
        if callable(get_identifier):
            value = get_identifier()
            if isinstance(value, str):
                return value
        get_name = getattr(overload, "GetName", None)
        if callable(get_name):
            value = get_name()
            if isinstance(value, str):
                return value
        identifier = getattr(overload, "identifier", None)
        return identifier if isinstance(identifier, str) else None

    @classmethod
    def _get_port_type_signature(cls, sdr_node: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Build ordered input/output type signature for one SDR node."""
        input_types: list[str] = []
        for name in sdr_node.GetShaderInputNames():
            shader_input = sdr_node.GetShaderInput(name)
            input_type = resolve_property_type_name(shader_input)
            if not input_type:
                return tuple(), tuple()
            input_types.append(input_type)

        output_types: list[str] = []
        for name in sdr_node.GetShaderOutputNames():
            shader_output = sdr_node.GetShaderOutput(name)
            output_type = resolve_property_type_name(shader_output)
            if not output_type:
                return tuple(), tuple()
            output_types.append(output_type)

        return tuple(input_types), tuple(output_types)

    @classmethod
    def _signature_type_pattern(cls, signature: tuple[tuple[str, ...], tuple[str, ...]]) -> tuple[int, ...]:
        """Normalize concrete types to a structural equality pattern."""
        inputs, outputs = signature
        type_to_slot: dict[str, int] = {}
        pattern: list[int] = []

        for type_name in inputs:
            if type_name not in type_to_slot:
                type_to_slot[type_name] = len(type_to_slot)
            pattern.append(type_to_slot[type_name])

        # Keep IO boundary explicit so equal-length collisions cannot blur layouts.
        pattern.append(-1)

        for type_name in outputs:
            if type_name not in type_to_slot:
                type_to_slot[type_name] = len(type_to_slot)
            pattern.append(type_to_slot[type_name])

        return tuple(pattern)

    @classmethod
    def _has_consistent_port_types(
        cls, subidentifiers: Sequence[str], sdr_nodes_by_subidentifier: Optional[dict[str, object]]
    ) -> bool:
        """Return True when all overloads share one SDR input/output type shape."""
        if not sdr_nodes_by_subidentifier:
            return False
        reference_signature: Optional[tuple[tuple[str, ...], tuple[str, ...]]] = None
        reference_pattern: Optional[tuple[int, ...]] = None
        signatures: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
        for subidentifier in subidentifiers:
            sdr_node = sdr_nodes_by_subidentifier.get(subidentifier)
            if not sdr_node:
                return False
            signature = cls._get_port_type_signature(sdr_node)
            signatures[subidentifier] = signature
            if not signature[0] and not signature[1]:
                return False
            pattern = cls._signature_type_pattern(signature)
            if reference_signature is None:
                reference_signature = signature
                reference_pattern = pattern
                continue
            if pattern != reference_pattern:
                return False
        return reference_signature is not None

    def cache_family_overloads(
        self,
        source_asset_path: str,
        family_key: str,
        subidentifiers: Sequence[str],
        sdr_nodes_by_subidentifier: Optional[dict[str, object]] = None,
    ) -> tuple[str, ...]:
        """Register overloads for one editor-visible polymorphic family."""
        unique = tuple(sorted({str(item) for item in subidentifiers if item}))
        if len(unique) <= 1:
            return tuple()
        if sdr_nodes_by_subidentifier is not None and not self._has_consistent_port_types(
            unique, sdr_nodes_by_subidentifier
        ):
            return tuple()
        if source_asset_path and family_key:
            self._family_overloads[(source_asset_path, family_key)] = unique
        return unique

    def _get_prim_source_asset(self, prim: Usd.Prim) -> Sdf.AssetPath:
        """Execute get prim source asset behavior for material graph workflows."""

        api = UsdShade.NodeDefAPI(prim)
        if not api:
            return Sdf.AssetPath()
        return api.GetSourceAsset(self._source_type)

    def get_source_asset_for_prim(self, prim: Optional[Usd.Prim]) -> Sdf.AssetPath:
        """Return the MDL source asset for a shader prim."""
        if not prim or not prim.IsValid():
            return Sdf.AssetPath()
        return self._get_prim_source_asset(prim)

    def _get_prim_subidentifier(self, prim: Usd.Prim) -> str:
        """Execute get prim subidentifier behavior for material graph workflows."""

        api = UsdShade.NodeDefAPI(prim)
        if not api:
            return ""
        value = api.GetSourceAssetSubIdentifier(self._source_type)
        return str(value) if value else ""

    def _get_family_key(self, source_asset: Sdf.AssetPath, subidentifier: str) -> str:
        """Return the catalog-compatible overload family key for a subidentifier."""
        if not source_asset or not subidentifier:
            return ""
        return mdl_polymorphic_family_key(self._get_sdr_node(source_asset, subidentifier), subidentifier)

    def _get_cached_overloads(self, source_asset: Sdf.AssetPath, family_key: str) -> tuple[str, ...]:
        """Return cached or registry-discovered overloads for one editor family."""

        source_key = self._source_asset_key(source_asset)
        if not source_key or not family_key:
            return tuple()
        cached = self._family_overloads.get((source_key, family_key), tuple())
        if cached:
            return cached
        try:
            subidentifiers = omni.UsdMdl.RegistryUtils.GetSubIdentifiersForAsset(source_asset)
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
            logger.debug("GetSubIdentifiersForAsset failed for %s: %s", source_key, exc)
            return tuple()
        matches = []
        sdr_nodes_by_subidentifier: dict[str, object] = {}
        for subidentifier in subidentifiers or []:
            sdr_node = self._get_sdr_node(source_asset, subidentifier)
            if not sdr_node:
                continue
            if mdl_polymorphic_family_key(sdr_node, subidentifier) != family_key:
                continue
            matches.append(subidentifier)
            sdr_nodes_by_subidentifier[subidentifier] = sdr_node
        return self.cache_family_overloads(source_key, family_key, matches, sdr_nodes_by_subidentifier)

    def _get_resolved_overloads_for_prim(self, prim: Usd.Prim) -> tuple[str, ...]:
        """Execute get resolved overloads for prim behavior for material graph workflows."""
        prim_path = str(prim.GetPath())
        cache_key = (self._runtime_epoch, prim_path)
        cached = self._resolved_overloads_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            overloads = omni.UsdMdl.RegistryUtils.GetOverloads(prim)
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
            logger.debug("GetOverloads failed for %s: %s", prim.GetPath(), exc)
            return tuple()
        resolved = []
        for overload in overloads or []:
            subidentifier = overload.GetSubIdentifier()
            if subidentifier:
                resolved.append(subidentifier)
        result = tuple(sorted(set(resolved)))
        self._store_runtime_cache_value(self._resolved_overloads_cache, cache_key, result)
        return result

    def _all_input_sources_resolved(self, prim: Usd.Prim, _visited: Optional[set] = None) -> bool:
        """Return True only when every connected input source is non-polymorphic or resolved.

        Walks upstream through the connection graph so that an unresolved
        polymorphic node anywhere in the chain prevents downstream nodes from
        being considered concrete.  A *visited* set prevents infinite loops in
        degenerate (cyclic) graphs.
        """
        if _visited is None:
            _visited = set()
        prim_path = str(prim.GetPath())
        if prim_path in _visited:
            return False
        _visited.add(prim_path)

        shader = UsdShade.Shader(prim)
        if not shader:
            return True

        for inp in shader.GetInputs():
            if not inp.HasConnectedSource():
                continue
            try:
                source_connectable, _, _ = inp.GetConnectedSource()
                source_prim = source_connectable.GetPrim() if source_connectable else None
            except (RuntimeError, ValueError, TypeError, AttributeError):
                continue
            if not source_prim or not source_prim.IsValid():
                continue

            source_asset = self._get_prim_source_asset(source_prim)
            source_sub = self._get_prim_subidentifier(source_prim)
            source_family = self._get_family_key(source_asset, source_sub)
            source_cached = self._get_cached_overloads(source_asset, source_family)
            if len(source_cached) <= 1:
                continue

            source_resolved = self._get_resolved_overloads_for_prim(source_prim)
            source_effective = source_resolved or source_cached
            if len(source_effective) != 1:
                return False

            if not self._all_input_sources_resolved(source_prim, _visited):
                return False

        return True

    def _is_prim_in_polymorphic_family(self, prim: Usd.Prim) -> bool:
        """Return True if *prim* belongs to a polymorphic overload family."""
        prim_path = str(prim.GetPath())
        cache_key = (self._runtime_epoch, prim_path)
        cached = self._polymorphic_family_cache.get(cache_key)
        if cached is not None:
            return cached
        source_asset = self._get_prim_source_asset(prim)
        sub = self._get_prim_subidentifier(prim)
        if not source_asset or not sub:
            self._store_runtime_cache_value(self._polymorphic_family_cache, cache_key, False)
            return False
        family_key = self._get_family_key(source_asset, sub)
        result = len(self._get_cached_overloads(source_asset, family_key)) > 1
        self._store_runtime_cache_value(self._polymorphic_family_cache, cache_key, result)
        return result

    def _get_known_port_type(
        self,
        neighbor_prim: Usd.Prim,
        port_name: str,
        is_input: bool,
        _visited: Optional[set] = None,
    ) -> Optional[str]:
        """Return the port type if it's the same across all of the neighbor's narrowed candidates, else None."""
        use_cache = not _visited
        prim_key = str(neighbor_prim.GetPath())
        cache_key = (self._runtime_epoch, prim_key, port_name, bool(is_input))
        if use_cache and cache_key in self._known_port_type_cache:
            return self._known_port_type_cache[cache_key]
        source_asset = self._get_prim_source_asset(neighbor_prim)
        sub = self._get_prim_subidentifier(neighbor_prim)
        if not source_asset or not sub:
            return None
        family_key = self._get_family_key(source_asset, sub)
        cached = self._get_cached_overloads(source_asset, family_key)
        if len(cached) <= 1:
            return None
        narrowed = self._narrow_by_connections(neighbor_prim, cached, _visited)
        seen: set[str] = set()
        for s in narrowed:
            sdr_node = self._get_sdr_node(source_asset, s)
            if not sdr_node:
                return None
            prop = sdr_node.GetShaderInput(port_name) if is_input else sdr_node.GetShaderOutput(port_name)
            if not prop:
                return None
            seen.add(resolve_property_type_name(prop))
            if len(seen) > 1:
                return None
        result = next(iter(seen)) if len(seen) == 1 else None
        if use_cache and result is not None:
            self._store_runtime_cache_value(self._known_port_type_cache, cache_key, result)
        return result

    def _filter_candidates(
        self,
        prim: Usd.Prim,
        cached_candidates: tuple[str, ...],
        constraints: list[tuple[str, str, bool]],
    ) -> tuple[str, ...]:
        """Return candidates matching all constraints."""
        source_asset = self._get_prim_source_asset(prim)
        scored: list[tuple[int, str]] = []
        for sub in cached_candidates:
            sdr_node = self._get_sdr_node(source_asset, sub)
            if not sdr_node:
                continue
            score = self._candidate_constraint_score(sdr_node, constraints)
            if score is not None:
                scored.append((score, sub))
        if not scored:
            return tuple()
        best_score = min(score for score, _sub in scored)
        return tuple(sub for score, sub in scored if score == best_score)

    @staticmethod
    def _candidate_constraint_score(sdr_node: object, constraints: list[tuple[str, str, bool]]) -> Optional[int]:
        """Return summed match score for a candidate, or None if incompatible."""
        return compute_polymorphic_constraint_score(sdr_node, constraints)

    def _narrow_by_indexed_connections(
        self,
        prim: Usd.Prim,
        cached_candidates: tuple[str, ...],
        index: dict[str, dict[str, list[tuple]]],
        _visited: set,
    ) -> tuple[str, ...]:
        """Narrow candidates from a precomputed parent-nodegraph connection index."""
        prim_key = str(prim.GetPath())
        constraints: list[tuple[str, str, bool]] = []
        constraints.extend(index["input_constraints"].get(prim_key, ()))
        constraints.extend(index["output_constraints"].get(prim_key, ()))
        constraints.extend(index["interface_constraints"].get(prim_key, ()))

        stage = prim.GetStage()
        for port_name, source_prim_key, source_port in index["poly_input_neighbors"].get(prim_key, ()):
            source_prim = stage.GetPrimAtPath(Sdf.Path(source_prim_key)) if stage else None
            if not source_prim:
                continue
            known = self._get_known_port_type(source_prim, source_port, False, _visited)
            if known:
                constraints.append((port_name, known, True))

        for output_name, sibling_prim_key, sibling_input_name in index["poly_output_neighbors"].get(prim_key, ()):
            sibling_prim = stage.GetPrimAtPath(Sdf.Path(sibling_prim_key)) if stage else None
            if not sibling_prim:
                continue
            known = self._get_known_port_type(sibling_prim, sibling_input_name, True, _visited)
            if known:
                constraints.append((output_name, known, False))

        if not constraints:
            return cached_candidates
        return self._filter_candidates(prim, cached_candidates, constraints)

    def _narrow_by_connections(
        self,
        prim: Usd.Prim,
        cached_candidates: tuple[str, ...],
        _visited: Optional[set] = None,
    ) -> tuple[str, ...]:
        """Narrow candidates using non-polymorphic constraints and known polymorphic port types.

        For polymorphic neighbors, the constraint is only used if the
        specific port type is unambiguous across the neighbor's own
        narrowed candidates.  A visited set prevents infinite recursion
        when evaluating chains of connected polymorphic nodes.
        """
        prim_key = str(prim.GetPath())
        cache_key = (self._runtime_epoch, prim_key, tuple(cached_candidates))
        cached = self._narrow_cache.get(cache_key)
        if cached is not None:
            return cached
        if cache_key in self._narrow_in_progress:
            return cached_candidates
        self._narrow_in_progress.add(cache_key)
        try:
            if _visited is None:
                _visited = set()
            if prim_key in _visited:
                return cached_candidates
            else:
                _visited.add(prim_key)
                shader = UsdShade.Shader(prim)
                if not shader:
                    result = cached_candidates
                else:
                    index = self._get_graph_connection_index(prim)
                    if index is not None:
                        result = self._narrow_by_indexed_connections(prim, cached_candidates, index, _visited)
                        self._store_runtime_cache_value(self._narrow_cache, cache_key, result)
                        return result
                    constraints: list[tuple[str, str, bool]] = []
                    prim_path = prim.GetPath()
                    parent = prim.GetParent()

                    for inp in shader.GetInputs():
                        if not inp.HasConnectedSource():
                            continue
                        port_name = inp.GetBaseName()
                        try:
                            source_connectable, source_name, _ = inp.GetConnectedSource()
                            if not source_connectable:
                                continue
                            source_prim = source_connectable.GetPrim()
                            if not source_prim:
                                continue
                            if self._is_prim_in_polymorphic_family(source_prim):
                                src_port = (
                                    (
                                        str(source_name)
                                        .removeprefix(UsdShade.Tokens.inputs)
                                        .removeprefix(UsdShade.Tokens.outputs)
                                    )
                                    if source_name
                                    else None
                                )
                                if src_port:
                                    known = self._get_known_port_type(source_prim, src_port, False, _visited)
                                    if known:
                                        constraints.append((port_name, known, True))
                                continue
                            if (
                                parent
                                and source_prim.GetPath() == parent.GetPath()
                                and source_prim.IsA(UsdShade.NodeGraph)
                            ):
                                # The containing NodeGraph input is only an interface. Its
                                # authored type mirrors the current child port and should
                                # not make an internal unresolved polymorphic connection
                                # concrete until the interface itself has an external
                                # source. _append_nodegraph_interface_constraints handles
                                # that external-source case below.
                                continue
                            source_attr = source_connectable.GetOutput(source_name) if source_name else None
                            if not source_attr:
                                source_attr = source_connectable.GetInput(source_name) if source_name else None
                            if source_attr:
                                constraints.append((port_name, str(source_attr.GetTypeName()), True))
                        except (RuntimeError, ValueError, TypeError, AttributeError):
                            pass
                    if parent:
                        for sibling in parent.GetChildren():
                            if sibling.GetPath() == prim_path:
                                continue
                            sib_shader = UsdShade.Shader(sibling)
                            if not sib_shader:
                                continue
                            is_sib_poly = self._is_prim_in_polymorphic_family(sibling)
                            for sib_inp in sib_shader.GetInputs():
                                if not sib_inp.HasConnectedSource():
                                    continue
                                try:
                                    for rp in sib_inp.GetRawConnectedSourcePaths():
                                        if rp.GetPrimPath() != prim_path:
                                            continue
                                        output_name = (
                                            str(rp.name)
                                            .removeprefix(UsdShade.Tokens.inputs)
                                            .removeprefix(UsdShade.Tokens.outputs)
                                        )
                                        if is_sib_poly:
                                            known = self._get_known_port_type(
                                                sibling, sib_inp.GetBaseName(), True, _visited
                                            )
                                            if known:
                                                constraints.append((output_name, known, False))
                                        else:
                                            constraints.append((output_name, str(sib_inp.GetTypeName()), False))
                                except (RuntimeError, ValueError, TypeError, AttributeError):
                                    pass

                        if parent.IsA(UsdShade.NodeGraph):
                            self._append_nodegraph_interface_constraints(parent, prim_path, constraints)

                    if not constraints:
                        result = cached_candidates
                    else:
                        result = self._filter_candidates(prim, cached_candidates, constraints)
                self._store_runtime_cache_value(self._narrow_cache, cache_key, result)
                return result
        finally:
            self._narrow_in_progress.discard(cache_key)

    @staticmethod
    def _connected_source_paths(port: object) -> list[Sdf.Path]:
        """Return raw connected source paths for a UsdShade input/output port."""
        try:
            return list(port.GetRawConnectedSourcePaths() or [])
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return []

    @staticmethod
    def _connected_source_types(port: object, stage: Usd.Stage) -> list[str]:
        """Return connected source type names using UsdShade resolution first."""
        types: list[str] = []
        try:
            source, source_name, _ = port.GetConnectedSource()
        except (RuntimeError, ValueError, TypeError, AttributeError):
            source = None
            source_name = None
        if source and source_name:
            source_port = source.GetOutput(source_name) or source.GetInput(source_name)
            if source_port:
                return [str(source_port.GetTypeName())]
        for source_path in MdlPolymorphicResolver._connected_source_paths(port):
            source_attr = stage.GetAttributeAtPath(source_path)
            if source_attr:
                types.append(str(source_attr.GetTypeName()))
        return list(dict.fromkeys(types))

    @classmethod
    def _iter_consumer_prims(cls, root: Usd.Prim, excluded_subtree: Sdf.Path) -> list[Usd.Prim]:
        """Return potential consumer prims from a bounded breadth-first traversal."""

        try:
            max_depth = max(0, int(cls._MAX_CONSUMER_SEARCH_DEPTH))
        except (TypeError, ValueError):
            max_depth = 0
        prims: list[Usd.Prim] = []
        queue: list[tuple[Usd.Prim, int]] = [(root, 0)]
        index = 0
        while index < len(queue):
            prim, depth = queue[index]
            index += 1
            prim_path = prim.GetPath()
            if prim_path.HasPrefix(excluded_subtree):
                continue
            prims.append(prim)
            if depth >= max_depth:
                continue
            try:
                children = prim.GetChildren()
            except (RuntimeError, ValueError, TypeError, AttributeError):
                continue
            for child in children:
                queue.append((child, depth + 1))
        return prims

    def _append_indexed_nodegraph_interface_constraints(
        self,
        nodegraph_prim: Usd.Prim,
        index: dict[str, dict[str, list[tuple]]],
    ) -> None:
        """Precompute child constraints that flow through nodegraph interface ports."""
        stage = nodegraph_prim.GetStage()
        nodegraph = UsdShade.NodeGraph(nodegraph_prim)
        if not (stage and nodegraph):
            return

        for ng_input in nodegraph.GetInputs():
            if not ng_input.HasConnectedSource():
                continue
            external_source_types = self._connected_source_types(ng_input, stage)
            if not external_source_types:
                continue
            for child in nodegraph_prim.GetChildren():
                shader = UsdShade.Shader(child)
                if not shader:
                    continue
                child_key = str(child.GetPath())
                for child_input in shader.GetInputs():
                    for raw_path in self._connected_source_paths(child_input):
                        if (
                            raw_path.GetPrimPath() == nodegraph_prim.GetPath()
                            and self._port_name_from_source_path(raw_path) == ng_input.GetBaseName()
                        ):
                            for source_type in external_source_types:
                                self._append_index_entry(
                                    index,
                                    "interface_constraints",
                                    child_key,
                                    (child_input.GetBaseName(), source_type, True),
                                )

        root = nodegraph_prim.GetParent()
        if not root:
            return
        consumer_apis = []
        for prim in self._iter_consumer_prims(root, nodegraph_prim.GetPath()):
            api = UsdShade.ConnectableAPI(prim)
            if api:
                consumer_apis.append(api)
        for ng_output in nodegraph.GetOutputs():
            child_output_paths = [
                raw_path
                for raw_path in self._connected_source_paths(ng_output)
                if raw_path.GetPrimPath().GetParentPath() == nodegraph_prim.GetPath()
            ]
            if not child_output_paths:
                continue
            for api in consumer_apis:
                for consumer_input in api.GetInputs():
                    for raw_path in self._connected_source_paths(consumer_input):
                        if (
                            raw_path.GetPrimPath() == nodegraph_prim.GetPath()
                            and self._port_name_from_source_path(raw_path) == ng_output.GetBaseName()
                        ):
                            expected_type = str(consumer_input.GetTypeName())
                            for child_output_path in child_output_paths:
                                self._append_index_entry(
                                    index,
                                    "interface_constraints",
                                    str(child_output_path.GetPrimPath()),
                                    (self._port_name_from_source_path(child_output_path), expected_type, False),
                                )

    def _append_nodegraph_interface_constraints(
        self,
        nodegraph_prim: Usd.Prim,
        child_prim_path: Sdf.Path,
        constraints: list[tuple[str, str, bool]],
    ) -> None:
        """Add constraints that flow through a containing NodeGraph's interface ports."""
        stage = nodegraph_prim.GetStage()
        nodegraph = UsdShade.NodeGraph(nodegraph_prim)
        if not (stage and nodegraph):
            return

        for ng_input in nodegraph.GetInputs():
            if not ng_input.HasConnectedSource():
                continue
            external_source_types = self._connected_source_types(ng_input, stage)
            if not external_source_types:
                continue
            child = stage.GetPrimAtPath(child_prim_path)
            if not (child and child.IsValid()):
                continue
            shader = UsdShade.Shader(child)
            if not shader:
                continue
            for child_input in shader.GetInputs():
                for raw_path in self._connected_source_paths(child_input):
                    if (
                        raw_path.GetPrimPath() == nodegraph_prim.GetPath()
                        and strip_usd_namespace(raw_path.name) == ng_input.GetBaseName()
                    ):
                        for source_type in external_source_types:
                            constraints.append((child_input.GetBaseName(), source_type, True))

        root = nodegraph_prim.GetParent()
        if not root:
            return
        consumer_apis = []
        for prim in self._iter_consumer_prims(root, nodegraph_prim.GetPath()):
            api = UsdShade.ConnectableAPI(prim)
            if api:
                consumer_apis.append(api)
        for ng_output in nodegraph.GetOutputs():
            child_output_names = [
                strip_usd_namespace(raw_path.name)
                for raw_path in self._connected_source_paths(ng_output)
                if raw_path.GetPrimPath() == child_prim_path
            ]
            if not child_output_names:
                continue
            for api in consumer_apis:
                for consumer_input in api.GetInputs():
                    for raw_path in self._connected_source_paths(consumer_input):
                        if (
                            raw_path.GetPrimPath() == nodegraph_prim.GetPath()
                            and strip_usd_namespace(raw_path.name) == ng_output.GetBaseName()
                        ):
                            expected_type = str(consumer_input.GetTypeName())
                            for output_name in child_output_names:
                                constraints.append((output_name, expected_type, False))

    def get_state_for_prim(self, prim: Optional[Usd.Prim]) -> PolymorphicState:
        """Compute polymorphic state for a shader prim."""
        if not prim or not prim.IsValid():
            return PolymorphicState()
        source_asset = self._get_prim_source_asset(prim)
        current_subidentifier = self._get_prim_subidentifier(prim)
        base_name = self._base_name_from_subidentifier(current_subidentifier)
        family_key = self._get_family_key(source_asset, current_subidentifier)
        cached_candidates = self._get_cached_overloads(source_asset, family_key)
        is_polymorphic = len(cached_candidates) > 1

        if is_polymorphic:
            effective_candidates = self._narrow_by_connections(prim, cached_candidates)
        else:
            effective_candidates = cached_candidates

        is_concrete = len(effective_candidates) == 1
        return PolymorphicState(
            is_polymorphic=is_polymorphic,
            is_concrete=is_concrete,
            base_name=base_name,
            current_subidentifier=current_subidentifier,
            candidates=effective_candidates,
        )

    def _has_compatible_overload_for_port(
        self,
        prim: Usd.Prim,
        candidates: tuple[str, ...],
        port_name: str,
        expected_type: str,
        is_input: bool,
    ) -> bool:
        """Return True if any candidate overload has *port_name* with *expected_type*.

        Only checks the narrowed *candidates* (already filtered by existing
        connections), not the full family.
        """
        source_asset = self._get_prim_source_asset(prim)
        if not source_asset:
            return False
        for sub in candidates:
            sdr_node = self._get_sdr_node(source_asset, sub)
            if not sdr_node:
                continue
            if mdl_node_matches_polymorphic_constraints(sdr_node, ((port_name, expected_type, is_input),)):
                return True
        return False

    def can_connect_models(self, source_model: object, target_model: object) -> bool:
        """Allow tentative connections when a polymorphic endpoint has a matching overload."""
        source_state = self.get_state_for_prim(source_model.prim)
        target_state = self.get_state_for_prim(target_model.prim)

        src_unresolved = source_state.is_polymorphic and not source_state.is_concrete
        tgt_unresolved = target_state.is_polymorphic and not target_state.is_concrete

        if not src_unresolved and not tgt_unresolved:
            return False

        src_proxy = source_model.proxy_attribute
        tgt_proxy = target_model.proxy_attribute
        src_port_name = src_proxy.name.removeprefix(UsdShade.Tokens.inputs).removeprefix(UsdShade.Tokens.outputs)
        tgt_port_name = tgt_proxy.name.removeprefix(UsdShade.Tokens.inputs).removeprefix(UsdShade.Tokens.outputs)

        if src_unresolved:
            is_src_input = src_proxy.name.startswith(UsdShade.Tokens.inputs)
            if not self._has_compatible_overload_for_port(
                source_model.prim,
                source_state.candidates,
                src_port_name,
                str(tgt_proxy.type_name),
                is_src_input,
            ):
                return False

        if tgt_unresolved:
            is_tgt_input = tgt_proxy.name.startswith(UsdShade.Tokens.inputs)
            if not self._has_compatible_overload_for_port(
                target_model.prim,
                target_state.candidates,
                tgt_port_name,
                str(src_proxy.type_name),
                is_tgt_input,
            ):
                return False

        return True
