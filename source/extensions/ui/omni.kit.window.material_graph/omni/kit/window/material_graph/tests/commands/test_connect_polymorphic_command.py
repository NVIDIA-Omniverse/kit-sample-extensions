"""Tests for the polymorphic connect command and its cascade retargeting.

The ``MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand`` retargets MDL
shader overloads when connecting ports and cascades resolved types through
connected polymorphic neighbours.  These tests verify:

* Target retargeting when a concrete source is connected to a polymorphic target.
* Downstream cascade: retargeting a source propagates to consumers.
* Upstream cascade: retargeting a target propagates to sources.
* No retargeting when the source is unresolved polymorphic.
* Undo restores original subidentifiers for all retargeted prims.
* ``_get_overloads_for_prim`` discovers overloads via the asset registry.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import omni.kit.commands
import omni.kit.undo
import omni.UsdMdl
from pxr import Sdf, UsdShade

from ...scripts.config.paths import Paths
from ...scripts.plugins.impl.mdl.plugin import MdlPlugin
from ...scripts.utils.sdr_wrappers import resolve_output_value_type, wrap_shader_node
from .base import CommandsTestBase


class TestPolymorphicConnectCommand(CommandsTestBase):
    """Polymorphic connect with retargeting and cascade."""

    # -- helpers ---------------------------------------------------------------

    _BASE = Sdf.Path("/World/Looks/Material_MDL")
    _TEST_POLY_ABS = "test_poly_abs"
    _AUX_DEFINITIONS = Sdf.AssetPath("nvidia/aux_definitions.mdl")

    async def setUp(self) -> None:
        """Load the polymorphic MDL test scene."""
        await super().setUp()
        await self._load_scene("polymorphic.usda")

    @staticmethod
    def _command_result_succeeded(result: object) -> bool:
        """Return True when omni.kit.commands.execute reports command success and a truthy payload."""
        if isinstance(result, tuple) and result and isinstance(result[0], bool):
            return bool(result[0] and (len(result) == 1 or result[1]))
        return bool(result)

    def _shader(self, name: str) -> UsdShade.Shader:
        return UsdShade.Shader(self._get_prim_at_path(self._BASE.AppendChild(name)))

    def _sub(self, name: str) -> str:
        """Return the current mdl subidentifier for shader *name*."""
        return self._shader(name).GetSourceAssetSubIdentifier("mdl")

    def _input(self, shader_name: str, port_name: str) -> UsdShade.Input:
        return self._shader(shader_name).GetInput(port_name)

    def _output(self, shader_name: str, port_name: str) -> UsdShade.Output:
        return self._shader(shader_name).GetOutput(port_name)

    def _input_type(self, shader_name: str, port_name: str) -> str:
        inp = self._input(shader_name, port_name)
        return str(inp.GetAttr().GetTypeName()) if inp else ""

    def _output_type(self, shader_name: str, port_name: str) -> str:
        out = self._output(shader_name, port_name)
        return str(out.GetAttr().GetTypeName()) if out else ""

    def _register_test_poly_abs_family(self) -> tuple[Sdf.AssetPath, list[str]]:
        """Register the real polymorphic test_abs MDL family and return its source asset and variants."""
        test_module = str(Paths.DATA_PATH / "tests" / "mdl" / "test_poly_abs.mdl")
        source_asset = Sdf.AssetPath(test_module, test_module)
        plugin = MdlPlugin(load_catalog=False)
        try:
            self.assertTrue(plugin._ensure_modules_registered([source_asset], id(self)))
        finally:
            plugin.destroy()

        subidentifiers = list(omni.UsdMdl.RegistryUtils.GetSubIdentifiersForAsset(source_asset) or [])
        family = [sub for sub in subidentifiers if str(sub).split("(")[0].strip() == self._TEST_POLY_ABS]
        self.assertIn(f"{self._TEST_POLY_ABS}(int)", family)
        self.assertIn(f"{self._TEST_POLY_ABS}(color)", family)
        return source_asset, family

    def _define_test_poly_abs_shader(self, name: str, subidentifier: str) -> UsdShade.Shader:
        """Define a test_poly_abs shader with ports matching *subidentifier*."""
        source_asset, _ = self._register_test_poly_abs_family()
        sdr_node = wrap_shader_node(omni.UsdMdl.RegistryUtils.GetShaderNode(source_asset, subidentifier))
        self.assertIsNotNone(sdr_node)

        shader = UsdShade.Shader.Define(self._stage, self._BASE.AppendChild(name))
        api = UsdShade.NodeDefAPI(shader.GetPrim())
        api.SetSourceAsset(source_asset, "mdl")
        api.SetSourceAssetSubIdentifier(subidentifier, "mdl")
        for output_name in sdr_node.GetShaderOutputNames():
            shader.CreateOutput(output_name, resolve_output_value_type(sdr_node.GetShaderOutput(output_name)))
        for input_name in sdr_node.GetShaderInputNames():
            shader.CreateInput(input_name, resolve_output_value_type(sdr_node.GetShaderInput(input_name)))
        return shader

    def _define_aux_shader(self, name: str, subidentifier: str) -> UsdShade.Shader:
        """Define a built-in auxiliary MDL shader with its declared SDR ports."""
        sdr_node = wrap_shader_node(omni.UsdMdl.RegistryUtils.GetShaderNode(self._AUX_DEFINITIONS, subidentifier))
        self.assertIsNotNone(sdr_node, subidentifier)
        shader = UsdShade.Shader.Define(self._stage, self._BASE.AppendChild(name))
        api = UsdShade.NodeDefAPI(shader.GetPrim())
        api.SetSourceAsset(self._AUX_DEFINITIONS, "mdl")
        api.SetSourceAssetSubIdentifier(subidentifier, "mdl")
        for output_name in sdr_node.GetShaderOutputNames():
            shader.CreateOutput(output_name, resolve_output_value_type(sdr_node.GetShaderOutput(output_name)))
        for input_name in sdr_node.GetShaderInputNames():
            shader.CreateInput(input_name, resolve_output_value_type(sdr_node.GetShaderInput(input_name)))
        return shader

    def _define_bool_source(self, name: str = "bool_const") -> UsdShade.Output:
        """Define a simple shader output port with bool type."""
        shader = UsdShade.Shader.Define(self._stage, self._BASE.AppendChild(name))
        return shader.CreateOutput("out", Sdf.ValueTypeNames.Bool)

    def _define_int_source(self, name: str = "int_const") -> UsdShade.Output:
        """Define a simple shader output port with int type."""
        shader = UsdShade.Shader.Define(self._stage, self._BASE.AppendChild(name))
        return shader.CreateOutput("out", Sdf.ValueTypeNames.Int)

    # -- overload discovery ----------------------------------------------------

    async def test_get_overloads_for_prim_returns_multiple(self) -> None:
        """_get_overloads_for_prim returns >1 overloads for a polymorphic node."""
        from ...scripts.commands.impl.connections.connect_polymorphic import (
            MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand as Cmd,
        )

        prim = self._get_prim_at_path(self._BASE.AppendChild("normalize"))
        overloads = Cmd._get_overloads_for_prim(prim)
        self.assertGreater(len(overloads), 1, "normalize must have multiple overloads")

    async def test_get_overloads_for_prim_non_polymorphic(self) -> None:
        """_get_overloads_for_prim returns <=1 for a non-polymorphic node."""
        from ...scripts.commands.impl.connections.connect_polymorphic import (
            MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand as Cmd,
        )

        prim = self._get_prim_at_path(self._BASE.AppendChild("normal"))
        overloads = Cmd._get_overloads_for_prim(prim)
        self.assertLessEqual(len(overloads), 1, "normal must not have multiple overloads")

    async def test_constructor_overload_discovery_keeps_arity_families_separate(self) -> None:
        """Constructor overload discovery must match the catalog's single/multi-input families."""
        from ...scripts.commands.impl.connections.connect_polymorphic import (
            MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand as Cmd,
        )

        single = self._define_aux_shader("construct_float3_single", "construct_float3(color)")
        multi = self._define_aux_shader("construct_float3_multi", "construct_float3(float,float,float)")
        single_subs = {overload.GetSubIdentifier() for overload in Cmd._get_overloads_for_prim(single.GetPrim())}
        multi_subs = {overload.GetSubIdentifier() for overload in Cmd._get_overloads_for_prim(multi.GetPrim())}

        self.assertEqual(single_subs, {"construct_float3(color)", "construct_float3(int3)"})
        self.assertEqual(multi_subs, {"construct_float3(float,float,float)"})

    # -- target retargeting ----------------------------------------------------

    async def test_connect_concrete_to_polymorphic_retargets_target(self) -> None:
        """Connecting concrete float3 to a polymorphic float2 input retargets the target."""
        self.assertEqual(self._sub("dot"), "dot(float2,float2)")
        target = self._input("dot", "b")
        source = self._output("normal", "out")

        omni.kit.commands.execute(
            "MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand",
            target=target,
            source=source,
        )

        self.assertIn("float3", self._sub("dot"), "dot must retarget to float3 variant")
        self.assertEqual(self._input_type("dot", "b"), "float3")
        self.assertTrue(self._input("dot", "b").HasConnectedSource())

    async def test_float_connects_to_all_reported_constructor_inputs(self) -> None:
        """NVBUG 6683949: float must connect to every reported Float2/Float3 constructor form."""
        source = UsdShade.Shader.Define(self._stage, self._BASE.AppendChild("nvbug6683949_float_source"))
        source_output = source.CreateOutput("out", Sdf.ValueTypeNames.Float)
        cases = (
            ("construct_float3", "construct_float3(color)", "a"),
            ("construct_float3_from_floats_x", "construct_float3(float,float,float)", "x"),
            ("construct_float3_from_floats_y", "construct_float3(float,float,float)", "y"),
            ("construct_float3_from_floats_z", "construct_float3(float,float,float)", "z"),
            ("construct_float2_from_floats_x", "construct_float2(float,float)", "x"),
            ("construct_float2_from_floats_y", "construct_float2(float,float)", "y"),
        )

        for name, subidentifier, input_name in cases:
            with self.subTest(subidentifier=subidentifier):
                target_shader = self._define_aux_shader(name, subidentifier)
                target = target_shader.GetInput(input_name)
                result = omni.kit.commands.execute(
                    "MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand",
                    target=target,
                    source=source_output,
                )
                self.assertTrue(self._command_result_succeeded(result))
                refreshed_target = UsdShade.Shader(target_shader.GetPrim()).GetInput(input_name)
                self.assertTrue(refreshed_target.HasConnectedSource())
                self.assertEqual(
                    UsdShade.NodeDefAPI(target_shader.GetPrim()).GetSourceAssetSubIdentifier("mdl"), subidentifier
                )

    async def test_connect_bool_to_polymorphic_input_retargets_target_to_int(self) -> None:
        """Connecting bool to a polymorphic input retargets to the int overload."""
        abs_shader = self._define_test_poly_abs_shader("abs_bool_target", f"{self._TEST_POLY_ABS}(color)")
        target = abs_shader.GetInput("a")
        source = self._define_bool_source()

        result = omni.kit.commands.execute(
            "MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand",
            target=target,
            source=source,
        )

        self.assertTrue(self._command_result_succeeded(result))
        self.assertEqual(abs_shader.GetSourceAssetSubIdentifier("mdl"), f"{self._TEST_POLY_ABS}(int)")
        refreshed_target = UsdShade.Shader(abs_shader.GetPrim()).GetInput("a")
        self.assertEqual(str(refreshed_target.GetAttr().GetTypeName()), "int")
        self.assertTrue(refreshed_target.HasConnectedSource())

    async def test_connect_bool_to_polymorphic_input_without_int_overload_is_rejected(self) -> None:
        """Bool should not connect to a polymorphic input unless an int overload is available."""
        target = self._input("normalize", "a")
        source = self._define_bool_source("bool_const_no_int")

        result = omni.kit.commands.execute(
            "MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand",
            target=target,
            source=source,
        )

        self.assertFalse(self._command_result_succeeded(result))
        self.assertEqual(self._sub("normalize"), "normalize(float2)")
        self.assertFalse(self._input("normalize", "a").HasConnectedSource())

    async def test_connect_int_to_polymorphic_input_prefers_exact_int_over_float(self) -> None:
        """Int sources should select an int overload when one exists before float promotion."""
        abs_shader = self._define_test_poly_abs_shader("abs_int_target", f"{self._TEST_POLY_ABS}(color)")
        target = abs_shader.GetInput("a")
        source = self._define_int_source()

        result = omni.kit.commands.execute(
            "MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand",
            target=target,
            source=source,
        )

        self.assertTrue(self._command_result_succeeded(result))
        self.assertEqual(abs_shader.GetSourceAssetSubIdentifier("mdl"), f"{self._TEST_POLY_ABS}(int)")
        refreshed_target = UsdShade.Shader(abs_shader.GetPrim()).GetInput("a")
        self.assertEqual(str(refreshed_target.GetAttr().GetTypeName()), "int")
        self.assertTrue(refreshed_target.HasConnectedSource())

    async def test_find_overload_for_port_prefers_exact_int_over_float(self) -> None:
        """Cascade retargeting should prefer exact int overloads over int-to-float promotion."""
        from ...scripts.commands.impl.connections.connect_polymorphic import (
            MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand as Cmd,
        )

        abs_shader = self._define_test_poly_abs_shader("abs_find_int", f"{self._TEST_POLY_ABS}(color)")

        overload = Cmd._find_overload_for_port(abs_shader.GetPrim(), "a", "int", True)

        self.assertIsNotNone(overload)
        self.assertEqual(overload.GetSubIdentifier(), f"{self._TEST_POLY_ABS}(int)")

    # -- cascade downstream ----------------------------------------------------

    async def test_cascade_downstream(self) -> None:
        """Retargeting normalize cascades downstream to dot."""
        self.assertEqual(self._sub("normalize"), "normalize(float2)")
        self.assertEqual(self._sub("dot"), "dot(float2,float2)")

        target = self._input("normalize", "a")
        source = self._output("data_lookup_float3", "out")

        omni.kit.commands.execute(
            "MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand",
            target=target,
            source=source,
        )

        self.assertIn("float3", self._sub("normalize"))
        self.assertIn("float3", self._sub("dot"), "dot must cascade to float3")

    # -- cascade upstream ------------------------------------------------------

    async def test_cascade_upstream(self) -> None:
        """Retargeting dot cascades upstream to normalize."""
        self.assertEqual(self._sub("normalize"), "normalize(float2)")
        self.assertEqual(self._sub("dot"), "dot(float2,float2)")

        target = self._input("dot", "b")
        source = self._output("normal", "out")

        omni.kit.commands.execute(
            "MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand",
            target=target,
            source=source,
        )

        self.assertIn("float3", self._sub("dot"))
        self.assertIn("float3", self._sub("normalize"), "normalize must cascade to float3")

    # -- no retarget when source is unresolved ---------------------------------

    async def test_no_retarget_unresolved_source(self) -> None:
        """Connecting unresolved polymorphic source to polymorphic target does not retarget."""
        original_dot_sub = self._sub("dot")
        original_norm_sub = self._sub("normalize")

        target = self._input("dot", "b")
        source = self._output("normalize", "out")

        omni.kit.commands.execute(
            "MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand",
            target=target,
            source=source,
        )

        self.assertEqual(self._sub("dot"), original_dot_sub, "dot must not retarget")
        self.assertEqual(self._sub("normalize"), original_norm_sub, "normalize must not retarget")
        self.assertTrue(
            self._input("dot", "b").HasConnectedSource(),
            "connection must still be authored even without retargeting",
        )

    # -- undo ------------------------------------------------------------------

    async def test_undo_restores_subidentifiers(self) -> None:
        """Undo after retarget + cascade restores all original subidentifiers."""
        orig_norm = self._sub("normalize")
        orig_dot = self._sub("dot")

        target = self._input("dot", "b")
        source = self._output("normal", "out")

        omni.kit.commands.execute(
            "MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand",
            target=target,
            source=source,
        )

        self.assertIn("float3", self._sub("dot"))
        self.assertIn("float3", self._sub("normalize"))

        self.assertTrue(omni.kit.undo.undo())
        await self._app.next_update_async()

        self.assertEqual(self._sub("dot"), orig_dot, "dot subidentifier must be restored")
        self.assertEqual(self._sub("normalize"), orig_norm, "normalize subidentifier must be restored")
        self.assertFalse(
            self._input("dot", "b").HasConnectedSource(),
            "dot.inputs:b must be disconnected after undo",
        )

    async def test_undo_redo_roundtrip(self) -> None:
        """Undo then redo re-applies the retarget and cascade."""
        target = self._input("normalize", "a")
        source = self._output("data_lookup_float3", "out")

        omni.kit.commands.execute(
            "MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand",
            target=target,
            source=source,
        )

        def _after() -> None:
            self.assertIn("float3", self._sub("normalize"))
            self.assertIn("float3", self._sub("dot"))
            self.assertTrue(self._input("normalize", "a").HasConnectedSource())

        def _before() -> None:
            self.assertEqual(self._sub("normalize"), "normalize(float2)")
            self.assertEqual(self._sub("dot"), "dot(float2,float2)")

        await self._assert_undo_redo(_before, _after)

    async def test_rewire_undo_restores_previous_source(self) -> None:
        """Replacing a source must be exactly reversible without a pre-disconnect."""
        target_shader = UsdShade.Shader.Define(self._stage, self._BASE.AppendChild("rewire_target"))
        old_shader = UsdShade.Shader.Define(self._stage, self._BASE.AppendChild("rewire_old"))
        new_shader = UsdShade.Shader.Define(self._stage, self._BASE.AppendChild("rewire_new"))
        target = target_shader.CreateInput("in", Sdf.ValueTypeNames.Float)
        old_source = old_shader.CreateOutput("out", Sdf.ValueTypeNames.Float)
        new_source = new_shader.CreateOutput("out", Sdf.ValueTypeNames.Float)
        self.assertTrue(target.ConnectToSource(old_source))

        result = omni.kit.commands.execute(
            "MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand",
            target=target,
            source=new_source,
        )

        self.assertTrue(self._command_result_succeeded(result))
        self.assertEqual(target.GetRawConnectedSourcePaths(), [new_source.GetAttr().GetPath()])
        self.assertTrue(omni.kit.undo.undo())
        await self._app.next_update_async()
        self.assertEqual(target.GetRawConnectedSourcePaths(), [old_source.GetAttr().GetPath()])

    async def test_unresolved_polymorphic_detection_handles_registry_shapes_and_failures(self) -> None:
        """Registry ambiguity and failures should produce conservative unresolved state."""
        from ...scripts.commands.impl.connections.connect_polymorphic import (
            MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand as Cmd,
        )

        prim = self._shader("normalize").GetPrim()
        float2 = SimpleNamespace(GetSubIdentifier=lambda: "normalize(float2)")
        float3 = SimpleNamespace(GetSubIdentifier=lambda: "normalize(float3)")
        with patch("omni.UsdMdl.RegistryUtils.GetOverloads", side_effect=[[float2, float3], [float2]]):
            self.assertFalse(Cmd._is_prim_unresolved_polymorphic(prim))
        with patch("omni.UsdMdl.RegistryUtils.GetOverloads", side_effect=[[float2, float3], [float2, float3]]):
            self.assertTrue(Cmd._is_prim_unresolved_polymorphic(prim))
        with patch("omni.UsdMdl.RegistryUtils.GetOverloads", side_effect=RuntimeError("registry unavailable")):
            self.assertFalse(Cmd._is_prim_unresolved_polymorphic(prim))
        with patch(
            "omni.UsdMdl.RegistryUtils.GetOverloads",
            side_effect=[[float2, float3], RuntimeError("resolution unavailable")],
        ):
            self.assertTrue(Cmd._is_prim_unresolved_polymorphic(prim))

    async def test_overload_selection_and_sort_fallbacks_are_deterministic(self) -> None:
        """Source overload selection should skip missing ports and choose a matching type."""
        from ...scripts.commands.impl.connections.connect_polymorphic import (
            MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand as Cmd,
        )

        target = self._input("dot", "b")
        source = self._output("normalize", "out")
        command = Cmd(target=target, source=source)
        missing = SimpleNamespace(
            GetSubIdentifier=lambda: "a(float)",
            GetShaderOutput=lambda _name: None,
        )
        prop = object()
        matching = SimpleNamespace(
            GetSubIdentifier=lambda: "b(float)",
            GetShaderOutput=lambda _name: prop,
        )
        with (
            patch("omni.UsdMdl.RegistryUtils.GetOverloads", return_value=[object()]),
            patch(
                "omni.kit.window.material_graph.scripts.commands.impl.connections.connect_polymorphic.wrap_shader_nodes",
                return_value=[matching, missing],
            ),
            patch(
                "omni.kit.window.material_graph.scripts.commands.impl.connections.connect_polymorphic.mdl_property_matches_polymorphic_constraint",
                return_value=True,
            ),
        ):
            self.assertIs(command._get_overload(), matching)

        broken = SimpleNamespace(
            GetSubIdentifier=MagicMock(side_effect=RuntimeError("bad identifier")),
            GetIdentifier=lambda: "fallback-id",
        )
        self.assertEqual(Cmd._overload_sort_key(broken), "fallback-id")
        self.assertEqual(Cmd._overload_sort_key(SimpleNamespace()), "")

    async def test_nodegraph_forwarding_resolves_input_and_output_ports(self) -> None:
        """NodeGraph interfaces should resolve to their real internal shader ports."""
        from ...scripts.commands.impl.connections.connect_polymorphic import (
            MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand as Cmd,
        )

        graph = UsdShade.NodeGraph.Define(self._stage, "/World/ForwardGraph")
        child = UsdShade.Shader.Define(self._stage, "/World/ForwardGraph/Child")
        graph_input = graph.CreateInput("value", Sdf.ValueTypeNames.Float)
        child_input = child.CreateInput("value", Sdf.ValueTypeNames.Float)
        self.assertTrue(child_input.ConnectToSource(graph_input))
        graph_output = graph.CreateOutput("result", Sdf.ValueTypeNames.Float)
        child_output = child.CreateOutput("result", Sdf.ValueTypeNames.Float)
        self.assertTrue(graph_output.ConnectToSource(child_output))

        self.assertEqual(Cmd._iter_nodegraph_forwarded_ports(self._stage, graph_input), [child_input])
        self.assertEqual(Cmd._iter_nodegraph_forwarded_ports(self._stage, graph_output), [child_output])
        self.assertEqual(Cmd._iter_nodegraph_forwarded_ports(self._stage, child_input), [child_input])
        self.assertEqual(Cmd._iter_nodegraph_forwarded_ports(self._stage, None), [])

    async def test_source_info_resolution_handles_input_output_and_missing_attributes(self) -> None:
        """UsdShade source descriptors should map back to the correct wrapper type."""
        from ...scripts.commands.impl.connections.connect_polymorphic import (
            MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand as Cmd,
        )

        shader = UsdShade.Shader.Define(self._stage, "/World/SourceInfo")
        input_port = shader.CreateInput("in", Sdf.ValueTypeNames.Float)
        output_port = shader.CreateOutput("out", Sdf.ValueTypeNames.Float)
        api = shader.ConnectableAPI()
        input_info = SimpleNamespace(
            source=api,
            sourceName="in",
            sourceType=UsdShade.AttributeType.Input,
        )
        output_info = SimpleNamespace(
            source=api,
            sourceName="out",
            sourceType=UsdShade.AttributeType.Output,
        )
        missing_info = SimpleNamespace(
            source=api,
            sourceName="missing",
            sourceType=UsdShade.AttributeType.Output,
        )
        self.assertEqual(Cmd._source_info_to_port(self._stage, input_info).GetAttr(), input_port.GetAttr())
        self.assertEqual(Cmd._source_info_to_port(self._stage, output_info).GetAttr(), output_port.GetAttr())
        self.assertIsNone(Cmd._source_info_to_port(self._stage, missing_info))

    async def test_connected_constraints_include_concrete_upstream_and_downstream_types(self) -> None:
        """Existing concrete neighbors should constrain both sides of an overload."""
        from ...scripts.commands.impl.connections.connect_polymorphic import (
            MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand as Cmd,
        )

        graph = UsdShade.NodeGraph.Define(self._stage, "/World/ConstraintGraph")
        source = UsdShade.Shader.Define(self._stage, "/World/ConstraintGraph/Source")
        target = UsdShade.Shader.Define(self._stage, "/World/ConstraintGraph/Target")
        consumer = UsdShade.Shader.Define(self._stage, "/World/ConstraintGraph/Consumer")
        source_output = source.CreateOutput("out", Sdf.ValueTypeNames.Float)
        target_input = target.CreateInput("value", Sdf.ValueTypeNames.Float)
        target_output = target.CreateOutput("result", Sdf.ValueTypeNames.Color3f)
        consumer_input = consumer.CreateInput("surface", Sdf.ValueTypeNames.Color3f)
        self.assertTrue(target_input.ConnectToSource(source_output))
        self.assertTrue(consumer_input.ConnectToSource(target_output))

        with patch.object(Cmd, "_is_prim_polymorphic", return_value=False):
            constraints = Cmd._get_connected_port_constraints(target.GetPrim())
        self.assertIn(("value", "float", True), constraints)
        self.assertIn(("result", "color3f", False), constraints)

        with patch.object(Cmd, "_is_prim_polymorphic", return_value=True):
            self.assertEqual(Cmd._get_connected_port_constraints(target.GetPrim()), [])
        self.assertTrue(graph.GetPrim().IsValid())

    async def test_failed_connection_rolls_back_and_restores_previous_sources(self) -> None:
        """A thrown USD connection failure should run both retarget and source restoration."""
        from ...scripts.commands.impl.connections.connect_polymorphic import (
            MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand as Cmd,
        )

        def attr(name: str):
            return SimpleNamespace(
                GetConnections=lambda: [],
                GetName=lambda: name,
                GetTypeName=lambda: Sdf.ValueTypeNames.Float,
            )

        source = SimpleNamespace(GetAttr=lambda: attr("outputs:out"), GetPrim=lambda: object())
        target = SimpleNamespace(
            GetAttr=lambda: attr("inputs:in"),
            GetPrim=lambda: object(),
            ConnectToSource=MagicMock(side_effect=RuntimeError("authoring rejected")),
        )
        command = Cmd(target=target, source=source)
        with (
            patch.object(command, "_is_internal_nodegraph_interface_connection", return_value=False),
            patch.object(command, "_is_shader_port", return_value=False),
            patch.object(command, "_port_subidentifier", return_value=""),
            patch.object(command, "_effective_interface_type", side_effect=lambda _port, fallback: fallback),
            patch.object(command, "_retarget_nodegraph_interface"),
            patch.object(command, "_get_stage", return_value=self._stage),
            patch.object(command, "_rollback_retargets") as rollback,
            patch.object(command, "_restore_target_connections") as restore,
        ):
            self.assertFalse(command.do())
            self.assertFalse(command.do())
        rollback.assert_called_once()
        restore.assert_called_once_with(self._stage)
        target.ConnectToSource.assert_called_once()
        self.assertEqual(command._port_path_for_log(source), "<unknown>")
        self.assertEqual(command._prim_path_for_log(source), "<unknown>")
