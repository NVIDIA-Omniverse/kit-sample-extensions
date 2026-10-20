# pylint: disable=protected-access
from types import SimpleNamespace
from unittest.mock import patch

from pxr import Sdf, UsdShade

from ...scripts.plugins.core.polymorphic_state import PolymorphicState
from ...scripts.plugins.impl.mdl import polymorphic as polymorphic_module
from ...scripts.plugins.impl.mdl.polymorphic import MdlPolymorphicResolver
from ..base import MaterialGraphTestBase


class _TypeIndicator:
    """Small SDR type-indicator double used by resolver unit tests."""

    def __init__(self, type_name: str) -> None:
        self._type_name = type_name

    def GetNdrType(self) -> str:
        return self._type_name

    def GetSdrType(self) -> str:
        return self._type_name

    def HasSdfType(self) -> bool:
        return bool(self._type_name)

    def GetSdfType(self) -> str:
        return self._type_name


class _Property:
    """Small SDR property double."""

    def __init__(self, type_name: str) -> None:
        self._indicator = _TypeIndicator(type_name)

    def GetTypeAsSdfType(self) -> _TypeIndicator:
        return self._indicator


class _Node:
    """Small SDR node double with named typed ports."""

    def __init__(self, inputs: dict[str, str], outputs: dict[str, str], label: str = "") -> None:
        self._inputs = {name: _Property(type_name) for name, type_name in inputs.items()}
        self._outputs = {name: _Property(type_name) for name, type_name in outputs.items()}
        self._label = label

    def GetLabel(self) -> str:
        return self._label

    def GetShaderInputNames(self) -> list[str]:
        return list(self._inputs)

    def GetShaderOutputNames(self) -> list[str]:
        return list(self._outputs)

    def GetShaderInput(self, name: str) -> _Property | None:
        return self._inputs.get(name)

    def GetShaderOutput(self, name: str) -> _Property | None:
        return self._outputs.get(name)


class TestMdlPolymorphicResolver(MaterialGraphTestBase):
    """Fast, headless contracts for MDL polymorphic graph analysis."""

    async def test_identifier_and_signature_helpers(self) -> None:
        """Identifiers and port signatures should normalize deterministically."""
        resolver = MdlPolymorphicResolver("mdl")
        by_identifier = SimpleNamespace(GetIdentifier=lambda: "mix(float)")
        by_name = SimpleNamespace(GetName=lambda: "mix(color3f)")

        self.assertEqual(resolver._base_name_from_subidentifier(" mix(float) "), "mix")
        self.assertEqual(resolver._base_name_from_subidentifier(None), "")
        self.assertEqual(resolver._normalize_overload_subidentifier("mix(int)"), "mix(int)")
        self.assertEqual(resolver._normalize_overload_subidentifier(by_identifier), "mix(float)")
        self.assertEqual(resolver._normalize_overload_subidentifier(by_name), "mix(color3f)")
        self.assertEqual(
            resolver._get_port_type_signature(_Node({"a": "float", "b": "float"}, {"out": "color3f"})),
            (("float", "float"), ("color3f",)),
        )
        self.assertEqual(resolver._signature_type_pattern((("float", "float"), ("color3f",))), (0, 0, -1, 1))

    async def test_signature_consistency_compares_type_shape(self) -> None:
        """Families should require the same equality pattern, not identical concrete types."""
        resolver = MdlPolymorphicResolver("mdl")
        same_shape = {
            "mix(float)": _Node({"a": "float", "b": "float"}, {"out": "float"}),
            "mix(color3f)": _Node({"a": "color3f", "b": "color3f"}, {"out": "color3f"}),
        }
        mixed_shape = dict(same_shape)
        mixed_shape["mix(color3f)"] = _Node({"a": "color3f", "b": "float"}, {"out": "color3f"})

        self.assertTrue(MdlPolymorphicResolver._has_consistent_port_types(tuple(same_shape), same_shape))
        self.assertFalse(MdlPolymorphicResolver._has_consistent_port_types(tuple(mixed_shape), mixed_shape))
        self.assertFalse(MdlPolymorphicResolver._has_consistent_port_types(("missing",), same_shape))
        self.assertFalse(MdlPolymorphicResolver._has_consistent_port_types(tuple(), None))

        expected = ("mix(color3f)", "mix(float)")
        self.assertEqual(resolver.cache_family_overloads("test.mdl", "mix", tuple(same_shape), same_shape), expected)
        self.assertEqual(resolver._family_overloads[("test.mdl", "mix")], expected)
        resolver.unregister_all_overloads()
        self.assertEqual(resolver.cache_family_overloads("test.mdl", "mix", tuple(mixed_shape), mixed_shape), tuple())
        self.assertNotIn(("test.mdl", "mix"), resolver._family_overloads)
        self.assertEqual(resolver.cache_family_overloads("test.mdl", "mix", tuple(same_shape), {}), tuple())
        self.assertNotIn(("test.mdl", "mix"), resolver._family_overloads)

    async def test_family_and_runtime_caches_are_invalidated(self) -> None:
        """Catalog and graph invalidation should clear only the intended cache layers."""
        resolver = MdlPolymorphicResolver("mdl")
        self.assertEqual(resolver.cache_family_overloads("test.mdl", "mix", ["mix(float)"]), tuple())
        expected = ("mix(color3f)", "mix(float)")
        self.assertEqual(
            resolver.cache_family_overloads("test.mdl", "mix", ["mix(float)", "mix(color3f)", "mix(float)"]),
            expected,
        )
        resolver._narrow_cache[(0, "/World/A", expected)] = expected
        resolver._graph_connection_indexes["/World"] = resolver._new_graph_connection_index()
        resolver.invalidate_runtime_cache()
        self.assertFalse(resolver._narrow_cache)
        self.assertFalse(resolver._graph_connection_indexes)
        self.assertEqual(resolver._family_overloads[("test.mdl", "mix")], expected)

        resolver.unregister_all_overloads()
        self.assertFalse(resolver._family_overloads)
        self.assertFalse(resolver._sdr_node_cache)

    async def test_sdr_lookup_caches_success_and_contains_registry_errors(self) -> None:
        """Repeated SDR lookup should be cached while registry failures remain contained."""
        resolver = MdlPolymorphicResolver("mdl")
        sentinel = object()
        with (
            patch("omni.UsdMdl.RegistryUtils.GetShaderNode", return_value=object()) as get_node,
            patch(
                "omni.kit.window.material_graph.scripts.plugins.impl.mdl.polymorphic.wrap_shader_node",
                return_value=sentinel,
            ),
        ):
            self.assertIs(resolver._get_sdr_node(Sdf.AssetPath("test.mdl"), "mix(float)"), sentinel)
            self.assertIs(resolver._get_sdr_node(Sdf.AssetPath("test.mdl"), "mix(float)"), sentinel)
            get_node.assert_called_once()

        with patch("omni.UsdMdl.RegistryUtils.GetShaderNode", side_effect=RuntimeError("missing")):
            self.assertIsNone(resolver._get_sdr_node(Sdf.AssetPath("test.mdl"), "missing(float)"))
        self.assertIsNone(resolver._get_sdr_node(Sdf.AssetPath(), "mix(float)"))

    async def test_registry_overload_discovery_filters_and_caches_family(self) -> None:
        """Registry discovery should retain only overloads in the requested family."""
        resolver = MdlPolymorphicResolver("mdl")
        asset = Sdf.AssetPath("test.mdl")
        overloads = ["mix(float)", "other(float)", "mix(color3f)"]
        with (
            patch("omni.UsdMdl.RegistryUtils.GetSubIdentifiersForAsset", return_value=overloads) as discover,
            patch.object(resolver, "_get_sdr_node", return_value=_Node({"a": "float"}, {"out": "float"})),
        ):
            self.assertEqual(resolver._get_cached_overloads(asset, "mix"), ("mix(color3f)", "mix(float)"))
            self.assertEqual(resolver._get_cached_overloads(asset, "mix"), ("mix(color3f)", "mix(float)"))
            discover.assert_called_once()

        with patch("omni.UsdMdl.RegistryUtils.GetSubIdentifiersForAsset", side_effect=RuntimeError("bad asset")):
            self.assertEqual(resolver._get_cached_overloads(Sdf.AssetPath("bad.mdl"), "mix"), tuple())

    async def test_constructor_family_discovery_does_not_cross_arity_boundaries(self) -> None:
        """Multi-input constructors sharing a base name must remain non-polymorphic."""
        resolver = MdlPolymorphicResolver("mdl")
        asset = Sdf.AssetPath("aux.mdl")
        nodes = {
            "construct_float3(color)": _Node({"a": "color3f"}, {"out": "float3"}, "Float3 from color"),
            "construct_float3(int3)": _Node({"a": "int3"}, {"out": "float3"}, "Float3 from int3"),
            "construct_float3(float,float,float)": _Node(
                {"x": "float", "y": "float", "z": "float"}, {"out": "float3"}, "Float3 from floats"
            ),
        }
        single_input_family = ("construct_float3(color)", "construct_float3(int3)")
        resolver.cache_family_overloads(asset.path, "Float3", single_input_family)
        shader = UsdShade.Shader.Define(self._stage, "/World/Constructor")

        with (
            patch("omni.UsdMdl.RegistryUtils.GetSubIdentifiersForAsset", return_value=list(nodes)),
            patch.object(resolver, "_get_prim_source_asset", return_value=asset),
            patch.object(resolver, "_get_sdr_node", side_effect=lambda _asset, sub: nodes[sub]),
            patch.object(resolver, "_narrow_by_connections", side_effect=lambda _prim, candidates: candidates),
        ):
            with patch.object(resolver, "_get_prim_subidentifier", return_value="construct_float3(float,float,float)"):
                multi_input_state = resolver.get_state_for_prim(shader.GetPrim())
            with patch.object(resolver, "_get_prim_subidentifier", return_value="construct_float3(color)"):
                single_input_state = resolver.get_state_for_prim(shader.GetPrim())

        self.assertFalse(multi_input_state.is_polymorphic)
        self.assertEqual(multi_input_state.candidates, tuple())
        self.assertTrue(single_input_state.is_polymorphic)
        self.assertEqual(single_input_state.candidates, single_input_family)

    async def test_resolved_overloads_are_deduplicated_and_cached(self) -> None:
        """Resolved registry candidates should have stable ordering and one lookup per epoch."""
        resolver = MdlPolymorphicResolver("mdl")
        shader = UsdShade.Shader.Define(self._stage, "/World/Shader")

        def overload(value: str):
            return SimpleNamespace(GetSubIdentifier=lambda: value)

        with patch(
            "omni.UsdMdl.RegistryUtils.GetOverloads",
            return_value=[overload("mix(float)"), overload("mix(color3f)"), overload("mix(float)")],
        ) as get_overloads:
            expected = ("mix(color3f)", "mix(float)")
            self.assertEqual(resolver._get_resolved_overloads_for_prim(shader.GetPrim()), expected)
            self.assertEqual(resolver._get_resolved_overloads_for_prim(shader.GetPrim()), expected)
            get_overloads.assert_called_once()

    async def test_state_uses_connection_narrowing_for_polymorphic_family(self) -> None:
        """State should distinguish unresolved families from one narrowed concrete candidate."""
        resolver = MdlPolymorphicResolver("mdl")
        shader = UsdShade.Shader.Define(self._stage, "/World/Shader")
        candidates = ("mix(float)", "mix(color3f)")
        with (
            patch.object(resolver, "_get_prim_source_asset", return_value=Sdf.AssetPath("test.mdl")),
            patch.object(resolver, "_get_prim_subidentifier", return_value="mix(float)"),
            patch.object(resolver, "_get_family_key", return_value="mix"),
            patch.object(resolver, "_get_cached_overloads", return_value=candidates),
            patch.object(resolver, "_narrow_by_connections", return_value=("mix(float)",)) as narrow,
        ):
            state = resolver.get_state_for_prim(shader.GetPrim())

        self.assertEqual(
            state,
            PolymorphicState(
                is_polymorphic=True,
                is_concrete=True,
                base_name="mix",
                current_subidentifier="mix(float)",
                candidates=("mix(float)",),
            ),
        )
        narrow.assert_called_once_with(shader.GetPrim(), candidates)
        self.assertEqual(resolver.get_state_for_prim(None), PolymorphicState())

    async def test_candidate_filter_keeps_only_best_compatible_score(self) -> None:
        """Candidate narrowing should retain all candidates tied for the best score."""
        resolver = MdlPolymorphicResolver("mdl")
        shader = UsdShade.Shader.Define(self._stage, "/World/Shader")
        nodes = {name: object() for name in ("a", "b", "c")}
        scores = {nodes["a"]: 2, nodes["b"]: 1, nodes["c"]: None}
        with (
            patch.object(resolver, "_get_prim_source_asset", return_value=Sdf.AssetPath("test.mdl")),
            patch.object(resolver, "_get_sdr_node", side_effect=lambda _asset, name: nodes[name]),
            patch.object(resolver, "_candidate_constraint_score", side_effect=lambda node, _constraints: scores[node]),
        ):
            self.assertEqual(resolver._filter_candidates(shader.GetPrim(), ("a", "b", "c"), []), ("b",))

    async def test_known_port_type_requires_candidate_agreement(self) -> None:
        """A neighbor port is known only when every narrowed overload agrees on its type."""
        resolver = MdlPolymorphicResolver("mdl")
        shader = UsdShade.Shader.Define(self._stage, "/World/Neighbor")
        nodes = {
            "mix(float)": _Node({"value": "float"}, {"out": "float"}),
            "mix(float2)": _Node({"value": "float"}, {"out": "float"}),
        }
        with (
            patch.object(resolver, "_get_prim_source_asset", return_value=Sdf.AssetPath("test.mdl")),
            patch.object(resolver, "_get_prim_subidentifier", return_value="mix(float)"),
            patch.object(resolver, "_get_cached_overloads", return_value=tuple(nodes)),
            patch.object(resolver, "_narrow_by_connections", return_value=tuple(nodes)),
            patch.object(resolver, "_get_sdr_node", side_effect=lambda _asset, name: nodes[name]),
        ):
            self.assertEqual(resolver._get_known_port_type(shader.GetPrim(), "out", False), "float")
            self.assertEqual(resolver._get_known_port_type(shader.GetPrim(), "out", False), "float")

        nodes["mix(float2)"] = _Node({"value": "color3f"}, {"out": "color3f"})
        resolver.invalidate_runtime_cache()
        with (
            patch.object(resolver, "_get_prim_source_asset", return_value=Sdf.AssetPath("test.mdl")),
            patch.object(resolver, "_get_prim_subidentifier", return_value="mix(float)"),
            patch.object(resolver, "_get_cached_overloads", return_value=tuple(nodes)),
            patch.object(resolver, "_narrow_by_connections", return_value=tuple(nodes)),
            patch.object(resolver, "_get_sdr_node", side_effect=lambda _asset, name: nodes[name]),
        ):
            self.assertIsNone(resolver._get_known_port_type(shader.GetPrim(), "out", False))

    async def test_indexed_narrowing_combines_static_and_neighbor_constraints(self) -> None:
        """The precomputed graph index should feed all known constraints to filtering."""
        resolver = MdlPolymorphicResolver("mdl")
        shader = UsdShade.Shader.Define(self._stage, "/World/Shader")
        source = UsdShade.Shader.Define(self._stage, "/World/Source")
        sibling = UsdShade.Shader.Define(self._stage, "/World/Sibling")
        index = resolver._new_graph_connection_index()
        key = str(shader.GetPath())
        index["input_constraints"][key] = [("value", "float", True)]
        index["poly_input_neighbors"][key] = [("other", str(source.GetPath()), "out")]
        index["poly_output_neighbors"][key] = [("result", str(sibling.GetPath()), "in")]
        captured = []
        with (
            patch.object(resolver, "_get_known_port_type", side_effect=["color3f", "float2"]),
            patch.object(
                resolver,
                "_filter_candidates",
                side_effect=lambda _prim, candidates, constraints: captured.append(constraints) or candidates,
            ),
        ):
            self.assertEqual(
                resolver._narrow_by_indexed_connections(shader.GetPrim(), ("a", "b"), index, set()),
                ("a", "b"),
            )
        self.assertEqual(
            captured[0],
            [("value", "float", True), ("other", "color3f", True), ("result", "float2", False)],
        )

    async def test_connected_source_helpers_resolve_real_usd_types(self) -> None:
        """Source path fallback and resolved USD source lookup should agree on port type."""
        resolver = MdlPolymorphicResolver("mdl")
        source = UsdShade.Shader.Define(self._stage, "/World/Source")
        target = UsdShade.Shader.Define(self._stage, "/World/Target")
        output = source.CreateOutput("out", Sdf.ValueTypeNames.Float)
        input_port = target.CreateInput("in", Sdf.ValueTypeNames.Float)
        self.assertTrue(input_port.ConnectToSource(output))

        self.assertEqual(resolver._connected_source_paths(input_port), [output.GetAttr().GetPath()])
        self.assertEqual(resolver._connected_source_types(input_port, self._stage), ["float"])
        broken = SimpleNamespace(
            GetConnectedSource=lambda: (_ for _ in ()).throw(RuntimeError("broken")),
            GetRawConnectedSourcePaths=lambda: [output.GetAttr().GetPath()],
        )
        self.assertEqual(resolver._connected_source_types(broken, self._stage), ["float"])

    async def test_graph_index_captures_real_connection_constraints(self) -> None:
        """A cached NodeGraph index should record concrete upstream types for its child."""
        resolver = MdlPolymorphicResolver("mdl")
        graph = UsdShade.NodeGraph.Define(self._stage, "/World/Graph")
        source = UsdShade.Shader.Define(self._stage, "/World/Graph/Source")
        target = UsdShade.Shader.Define(self._stage, "/World/Graph/Target")
        output = source.CreateOutput("out", Sdf.ValueTypeNames.Float)
        input_port = target.CreateInput("value", Sdf.ValueTypeNames.Float)
        self.assertTrue(input_port.ConnectToSource(output))

        with patch.object(resolver, "_is_prim_in_polymorphic_family", return_value=False):
            resolver.cache_graph_connection_index(graph.GetPrim())
        index = resolver._graph_connection_indexes[str(graph.GetPath())]
        self.assertIn(("value", "float", True), index["input_constraints"][str(target.GetPath())])

    async def test_nodegraph_interfaces_propagate_external_types(self) -> None:
        """External graph input/output connections should constrain the internal child ports."""
        resolver = MdlPolymorphicResolver("mdl")
        graph = UsdShade.NodeGraph.Define(self._stage, "/World/Graph")
        child = UsdShade.Shader.Define(self._stage, "/World/Graph/Child")
        external = UsdShade.Shader.Define(self._stage, "/World/External")
        consumer = UsdShade.Shader.Define(self._stage, "/World/Consumer")

        external_output = external.CreateOutput("out", Sdf.ValueTypeNames.Float)
        graph_input = graph.CreateInput("value", Sdf.ValueTypeNames.Float)
        child_input = child.CreateInput("value", Sdf.ValueTypeNames.Float)
        self.assertTrue(graph_input.ConnectToSource(external_output))
        self.assertTrue(child_input.ConnectToSource(graph_input))

        child_output = child.CreateOutput("out", Sdf.ValueTypeNames.Color3f)
        graph_output = graph.CreateOutput("result", Sdf.ValueTypeNames.Color3f)
        consumer_input = consumer.CreateInput("surface", Sdf.ValueTypeNames.Color3f)
        self.assertTrue(graph_output.ConnectToSource(child_output))
        self.assertTrue(consumer_input.ConnectToSource(graph_output))

        constraints = []
        resolver._append_nodegraph_interface_constraints(graph.GetPrim(), child.GetPath(), constraints)
        self.assertIn(("value", "float", True), constraints)
        self.assertIn(("out", "color3f", False), constraints)

        index = resolver._new_graph_connection_index()
        resolver._append_indexed_nodegraph_interface_constraints(graph.GetPrim(), index)
        self.assertIn(("value", "float", True), index["interface_constraints"][str(child.GetPath())])
        self.assertIn(("out", "color3f", False), index["interface_constraints"][str(child.GetPath())])

    async def test_consumer_traversal_is_bounded_and_excludes_subtree(self) -> None:
        """Interface consumer search should exclude the graph subtree and respect depth."""
        resolver = MdlPolymorphicResolver("mdl")
        root = self._stage.DefinePrim("/World/Root")
        graph = self._stage.DefinePrim("/World/Root/Graph")
        self._stage.DefinePrim("/World/Root/Graph/Child")
        self._stage.DefinePrim("/World/Root/A")
        self._stage.DefinePrim("/World/Root/A/B")

        paths = [str(prim.GetPath()) for prim in resolver._iter_consumer_prims(root, graph.GetPath())]
        self.assertEqual(paths, ["/World/Root", "/World/Root/A", "/World/Root/A/B"])
        with patch.object(MdlPolymorphicResolver, "_MAX_CONSUMER_SEARCH_DEPTH", 1):
            shallow = [str(prim.GetPath()) for prim in resolver._iter_consumer_prims(root, graph.GetPath())]
        self.assertEqual(shallow, ["/World/Root", "/World/Root/A"])

    async def test_all_input_sources_requires_resolved_upstream_family(self) -> None:
        """An unresolved polymorphic node upstream should keep its consumer unresolved."""
        resolver = MdlPolymorphicResolver("mdl")
        source = UsdShade.Shader.Define(self._stage, "/World/Source")
        target = UsdShade.Shader.Define(self._stage, "/World/Target")
        output = source.CreateOutput("out", Sdf.ValueTypeNames.Float)
        input_port = target.CreateInput("in", Sdf.ValueTypeNames.Float)
        self.assertTrue(input_port.ConnectToSource(output))

        with (
            patch.object(resolver, "_get_prim_source_asset", return_value=Sdf.AssetPath("test.mdl")),
            patch.object(resolver, "_get_prim_subidentifier", return_value="mix(float)"),
            patch.object(resolver, "_get_family_key", return_value="mix"),
            patch.object(resolver, "_get_cached_overloads", return_value=("mix(float)", "mix(color3f)")),
            patch.object(resolver, "_get_resolved_overloads_for_prim", return_value=tuple()),
        ):
            self.assertFalse(resolver._all_input_sources_resolved(target.GetPrim()))

        with (
            patch.object(resolver, "_get_prim_source_asset", return_value=Sdf.AssetPath("test.mdl")),
            patch.object(resolver, "_get_prim_subidentifier", return_value="mix(float)"),
            patch.object(resolver, "_get_family_key", return_value="mix"),
            patch.object(resolver, "_get_cached_overloads", return_value=("mix(float)", "mix(color3f)")),
            patch.object(resolver, "_get_resolved_overloads_for_prim", return_value=("mix(float)",)),
        ):
            self.assertTrue(resolver._all_input_sources_resolved(target.GetPrim()))

    async def test_tentative_connection_requires_matching_unresolved_overloads(self) -> None:
        """Both unresolved endpoints must offer a compatible port overload."""
        resolver = MdlPolymorphicResolver("mdl")
        source_prim = UsdShade.Shader.Define(self._stage, "/World/Source").GetPrim()
        target_prim = UsdShade.Shader.Define(self._stage, "/World/Target").GetPrim()
        source = SimpleNamespace(
            prim=source_prim,
            proxy_attribute=SimpleNamespace(name="outputs:out", type_name=Sdf.ValueTypeNames.Float),
        )
        target = SimpleNamespace(
            prim=target_prim,
            proxy_attribute=SimpleNamespace(name="inputs:in", type_name=Sdf.ValueTypeNames.Float),
        )
        unresolved = PolymorphicState(is_polymorphic=True, is_concrete=False, candidates=("mix(float)",))
        with (
            patch.object(resolver, "get_state_for_prim", side_effect=[unresolved, unresolved]),
            patch.object(resolver, "_has_compatible_overload_for_port", side_effect=[True, True]) as compatible,
        ):
            self.assertTrue(resolver.can_connect_models(source, target))
            self.assertEqual(compatible.call_count, 2)

        with (
            patch.object(resolver, "get_state_for_prim", side_effect=[unresolved, unresolved]),
            patch.object(resolver, "_has_compatible_overload_for_port", return_value=False),
        ):
            self.assertFalse(resolver.can_connect_models(source, target))

    async def test_legacy_narrowing_collects_concrete_and_polymorphic_neighbors(self) -> None:
        """The non-index fallback should constrain both upstream inputs and downstream consumers."""
        resolver = MdlPolymorphicResolver("mdl")
        graph = UsdShade.NodeGraph.Define(self._stage, "/World/Graph")
        source = UsdShade.Shader.Define(self._stage, "/World/Graph/Source")
        target = UsdShade.Shader.Define(self._stage, "/World/Graph/Target")
        sibling = UsdShade.Shader.Define(self._stage, "/World/Graph/Sibling")
        source_output = source.CreateOutput("out", Sdf.ValueTypeNames.Float)
        target_input = target.CreateInput("value", Sdf.ValueTypeNames.Float)
        target_output = target.CreateOutput("result", Sdf.ValueTypeNames.Color3f)
        sibling_input = sibling.CreateInput("surface", Sdf.ValueTypeNames.Color3f)
        self.assertTrue(target_input.ConnectToSource(source_output))
        self.assertTrue(sibling_input.ConnectToSource(target_output))
        captured = []

        with (
            patch.object(resolver, "_get_graph_connection_index", return_value=None),
            patch.object(resolver, "_is_prim_in_polymorphic_family", return_value=False),
            patch.object(resolver, "_append_nodegraph_interface_constraints") as append_interface,
            patch.object(
                resolver,
                "_filter_candidates",
                side_effect=lambda _prim, candidates, constraints: captured.append(constraints) or candidates,
            ),
        ):
            self.assertEqual(resolver._narrow_by_connections(target.GetPrim(), ("a", "b")), ("a", "b"))

        self.assertIn(("value", "float", True), captured[0])
        self.assertIn(("result", "color3f", False), captured[0])
        append_interface.assert_called_once_with(graph.GetPrim(), target.GetPath(), captured[0])

        resolver.invalidate_runtime_cache()
        captured.clear()
        with (
            patch.object(resolver, "_get_graph_connection_index", return_value=None),
            patch.object(resolver, "_is_prim_in_polymorphic_family", return_value=True),
            patch.object(resolver, "_get_known_port_type", side_effect=["float", "color3f"]),
            patch.object(resolver, "_append_nodegraph_interface_constraints"),
            patch.object(
                resolver,
                "_filter_candidates",
                side_effect=lambda _prim, candidates, constraints: captured.append(constraints) or ("a",),
            ),
        ):
            self.assertEqual(resolver._narrow_by_connections(target.GetPrim(), ("a", "b")), ("a",))
        self.assertEqual(captured[0], [("value", "float", True), ("result", "color3f", False)])

    async def test_resolver_failure_and_cache_boundaries_are_contained(self) -> None:
        """Malformed registry data and bounded caches should degrade to deterministic empty state."""
        resolver = MdlPolymorphicResolver("mdl")
        self.assertEqual(
            resolver._normalize_overload_subidentifier(SimpleNamespace(identifier="mix(float)")), "mix(float)"
        )
        self.assertIsNone(resolver._normalize_overload_subidentifier(object()))
        self.assertEqual(resolver._get_port_type_signature(_Node({"a": ""}, {"out": "float"})), (tuple(), tuple()))
        self.assertEqual(resolver._get_port_type_signature(_Node({"a": "float"}, {"out": ""})), (tuple(), tuple()))

        with patch.object(MdlPolymorphicResolver, "_MAX_RUNTIME_CACHE_ENTRIES", 2):
            cache = {}
            resolver._store_runtime_cache_value(cache, "a", 1)
            resolver._store_runtime_cache_value(cache, "b", 2)
            resolver._store_runtime_cache_value(cache, "c", 3)
        self.assertEqual(cache, {"b": 2, "c": 3})
        self.assertFalse(resolver.get_source_asset_for_prim(None))

        shader = UsdShade.Shader.Define(self._stage, "/World/FailureShader")
        with patch("omni.UsdMdl.RegistryUtils.GetOverloads", side_effect=RuntimeError("registry failed")):
            self.assertEqual(resolver._get_resolved_overloads_for_prim(shader.GetPrim()), tuple())
        self.assertFalse(resolver._all_input_sources_resolved(shader.GetPrim(), {str(shader.GetPath())}))

        with (
            patch.object(resolver, "_get_prim_source_asset", return_value=Sdf.AssetPath()),
            patch.object(resolver, "_get_prim_subidentifier", return_value=""),
        ):
            self.assertFalse(resolver._is_prim_in_polymorphic_family(shader.GetPrim()))
            self.assertIsNone(resolver._get_known_port_type(shader.GetPrim(), "out", False))

        candidates = ("mix(float)", "mix(color3f)")
        with patch.object(resolver, "_get_prim_source_asset", return_value=Sdf.AssetPath()):
            self.assertFalse(
                resolver._has_compatible_overload_for_port(shader.GetPrim(), candidates, "out", "float", False)
            )
        with (
            patch.object(resolver, "_get_prim_source_asset", return_value=Sdf.AssetPath("test.mdl")),
            patch.object(resolver, "_get_sdr_node", side_effect=[None, object()]),
            patch.object(polymorphic_module, "mdl_node_matches_polymorphic_constraints", return_value=True),
        ):
            self.assertTrue(
                resolver._has_compatible_overload_for_port(shader.GetPrim(), candidates, "out", "float", False)
            )
