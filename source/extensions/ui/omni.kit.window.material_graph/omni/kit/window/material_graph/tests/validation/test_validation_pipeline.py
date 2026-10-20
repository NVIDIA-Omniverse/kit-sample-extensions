# pylint: disable=relative-beyond-top-level,protected-access,no-member
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pxr import Sdf, UsdShade

from ...scripts.validation import pipeline
from ...scripts.validation.issue import ValidationIssue
from ...scripts.validation.severity import ValidationSeverity
from ..base import MaterialGraphTestBase


class TestValidationPipeline(MaterialGraphTestBase):
    """Focused coverage for validation traversal and dynamic USD boundary shapes."""

    async def test_connection_record_helpers_handle_tuple_fallback_and_invalid_shapes(self) -> None:
        """Connection helpers should normalize binding-version shapes and reject invalid records."""
        source = object()
        input_attr = SimpleNamespace(
            GetConnectedSources=lambda: ([source], ["invalid"]),
            GetConnectedSource=lambda: None,
        )
        self.assertEqual(list(pipeline._iter_connected_sources(input_attr)), [source])

        input_attr.GetConnectedSources = lambda: []
        input_attr.GetConnectedSource = lambda: (source, "out", UsdShade.AttributeType.Output)
        self.assertEqual(list(pipeline._iter_connected_sources(input_attr)), [source])

        prim = SimpleNamespace(IsValid=lambda: True, GetAttribute=MagicMock(return_value="attribute"))
        api = SimpleNamespace(GetPrim=lambda: prim)
        record = SimpleNamespace(source=api, sourceName="value", sourceType=UsdShade.AttributeType.Input)
        self.assertIs(pipeline._resolve_source_prim(record), prim)
        self.assertEqual(pipeline._source_attribute_from_connection(record, prim), "attribute")
        prim.GetAttribute.assert_called_once_with("inputs:value")

        self.assertIsNone(pipeline._resolve_source_prim(SimpleNamespace(source=None)))
        self.assertIsNone(pipeline._resolve_source_prim(SimpleNamespace(GetPrim=MagicMock(side_effect=RuntimeError))))
        self.assertIsNone(pipeline._source_attribute_from_connection(SimpleNamespace(), prim))

    async def test_reachable_and_model_context_traversal_include_nested_nodegraphs(self) -> None:
        """Validation scope should recurse through output-connected nodegraphs and model children."""
        material = UsdShade.Material.Define(self._stage, Sdf.Path("/Mat"))
        nodegraph = UsdShade.NodeGraph.Define(self._stage, Sdf.Path("/Mat/Graph"))
        internal = UsdShade.Shader.Define(self._stage, Sdf.Path("/Mat/Graph/Internal"))
        internal_output = internal.CreateOutput("out", Sdf.ValueTypeNames.Float)
        graph_output = nodegraph.CreateOutput("out", Sdf.ValueTypeNames.Float)
        graph_output.ConnectToSource(internal_output)
        material.CreateSurfaceOutput("test").ConnectToSource(graph_output)

        reachable = pipeline._collect_output_reachable_connectables(material.GetPrim())
        nodegraph_path = nodegraph.GetPrim().GetPath()
        internal_path = internal.GetPrim().GetPath()
        material_path = material.GetPrim().GetPath()
        self.assertIn(nodegraph_path, reachable)
        self.assertIn(internal_path, reachable)

        child_model = SimpleNamespace(get_child_prims=lambda: [internal.GetPrim()])
        root_model = SimpleNamespace(
            get_child_prims=lambda: [nodegraph.GetPrim(), nodegraph.GetPrim()],
            get_item_model=lambda path: child_model,
        )
        prims = pipeline._collect_context_prims(material.GetPrim(), root_model)
        self.assertEqual(
            {prim.GetPath() for prim in prims},
            {material_path, nodegraph_path, internal_path},
        )
        self.assertEqual(
            {prim.GetPath() for prim in pipeline._collect_context_prims(material.GetPrim(), None)},
            {material_path, nodegraph_path, internal_path},
        )

    async def test_reachability_can_be_limited_to_active_context_outputs(self) -> None:
        """Nodes used only by another render context must not affect active-context validation."""
        material = UsdShade.Material.Define(self._stage, Sdf.Path("/Mat"))
        mtlx = UsdShade.Shader.Define(self._stage, Sdf.Path("/Mat/Mtlx"))
        mdl = UsdShade.Shader.Define(self._stage, Sdf.Path("/Mat/Mdl"))
        mtlx_output = mtlx.CreateOutput("out", Sdf.ValueTypeNames.Token)
        mdl_output = mdl.CreateOutput("out", Sdf.ValueTypeNames.Token)
        mtlx_material_output = material.CreateSurfaceOutput("mtlx")
        mdl_material_output = material.CreateSurfaceOutput("mdl")
        mtlx_material_output.ConnectToSource(mtlx_output)
        mdl_material_output.ConnectToSource(mdl_output)

        reachable = pipeline._collect_output_reachable_connectables(
            material.GetPrim(), {mtlx_material_output.GetFullName()}
        )
        self.assertEqual(reachable, {mtlx.GetPrim().GetPath()})

    async def test_invalid_nodes_nodegraphs_connections_cycles_and_deduplication(self) -> None:
        """Core collectors should classify invalid graph state with stable paths and severities."""
        material = UsdShade.Material.Define(self._stage, Sdf.Path("/Mat"))
        nodegraph = UsdShade.NodeGraph.Define(self._stage, Sdf.Path("/Mat/Graph"))
        invalid = UsdShade.Shader.Define(self._stage, Sdf.Path("/Mat/Invalid"))
        invalid.CreateIdAttr("MissingDefinition")
        source = UsdShade.Shader.Define(self._stage, Sdf.Path("/Mat/Source"))
        source_output = source.CreateOutput("out", Sdf.ValueTypeNames.Float)
        target = UsdShade.Shader.Define(self._stage, Sdf.Path("/Mat/Target"))
        target_input = target.CreateInput("in", Sdf.ValueTypeNames.Color3f)
        target_input.ConnectToSource(source_output)
        target_output = target.CreateOutput("out", Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput("test").ConnectToSource(target_output)

        plugin = SimpleNamespace(
            is_supported_prim=lambda prim: prim == invalid.GetPrim(),
            get_shader_node_for_prim=lambda prim: None,
        )
        invalid_issues = pipeline._collect_invalid_nodes(
            [invalid.GetPrim()], plugin, "test", {invalid.GetPrim().GetPath()}
        )
        self.assertEqual(invalid_issues[0].severity, ValidationSeverity.ERROR)
        self.assertIn("identifier=MissingDefinition", invalid_issues[0].message)

        item_model = SimpleNamespace(has_invalid_connected_children=lambda: True)
        model = SimpleNamespace(get_item_model=lambda path: item_model)
        graph_issues = pipeline._collect_invalid_nodegraphs([nodegraph.GetPrim()], "test", model, set())
        self.assertEqual(graph_issues[0].severity, ValidationSeverity.WARNING)

        mismatch = pipeline._collect_invalid_connections(
            material.GetPrim(),
            [material.GetPrim(), source.GetPrim(), target.GetPrim()],
            plugin,
            "test",
            lambda *_args: False,
            pipeline._collect_output_reachable_connectables(material.GetPrim()),
        )
        self.assertEqual(
            {issue.code for issue in mismatch},
            {"INVALID_CONNECTION_TYPE_MISMATCH", "INVALID_CONNECTION_TYPE_MISMATCH_SOURCE"},
        )
        self.assertTrue(all("context 'test'" in issue.message for issue in mismatch))
        self.assertTrue(all(str(source_output.GetAttr().GetPath()) in issue.message for issue in mismatch))
        self.assertTrue(all(str(target_input.GetAttr().GetPath()) in issue.message for issue in mismatch))

        with (
            patch.object(pipeline, "find_cyclical_prims", return_value=[nodegraph.GetPrim()] * 8),
            patch.object(
                pipeline,
                "_collect_output_reachable_connectables",
                return_value={nodegraph.GetPrim().GetPath()},
            ),
        ):
            cycle_issues = pipeline._collect_cycle_issues(material.GetPrim(), "test")
        self.assertEqual(cycle_issues[0].code, "CYCLICAL_NODEGRAPHS")
        self.assertIn("context 'test'", cycle_issues[0].message)
        self.assertIn(str(nodegraph.GetPath()), cycle_issues[0].message)
        self.assertEqual(len(pipeline._dedupe(cycle_issues * 2)), 1)

    async def test_port_and_mixed_network_issues_include_context_and_prim_paths(self) -> None:
        """Every graph-integrity diagnostic should identify the context and affected USD object."""
        shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/Mat/Shader"))
        orphan = shader.CreateInput("orphan", Sdf.ValueTypeNames.Float)
        sdr_node = SimpleNamespace(GetShaderInputNames=lambda: [], GetShaderOutputNames=lambda: [])
        plugin = SimpleNamespace(
            get_shader_node_for_prim=lambda _prim: sdr_node,
            is_supported_prim=lambda _prim: False,
        )

        port_issues = pipeline._collect_invalid_shader_ports([shader.GetPrim()], plugin, "mtlx")
        self.assertEqual(len(port_issues), 1)
        self.assertIn("context 'mtlx'", port_issues[0].message)
        self.assertIn(str(orphan.GetAttr().GetPath()), port_issues[0].message)

        mixed_issues = pipeline._collect_mixed_networks([shader.GetPrim()], "mtlx", plugin)
        self.assertEqual(len(mixed_issues), 1)
        self.assertIn("context 'mtlx'", mixed_issues[0].message)
        self.assertIn(str(shader.GetPath()), mixed_issues[0].message)

        port_warning = pipeline._collect_invalid_shader_ports([shader.GetPrim()], plugin, "mtlx", set())
        self.assertEqual(port_warning[0].severity, ValidationSeverity.WARNING)
        self.assertEqual(pipeline._collect_mixed_networks([shader.GetPrim()], "mtlx", plugin, set()), [])

    async def test_connection_scope_issues_identify_both_ports_context_and_root(self) -> None:
        """Cross-context and cross-material connections should be distinct and actionable."""
        material = UsdShade.Material.Define(self._stage, Sdf.Path("/Mat"))
        hidden_source = UsdShade.Shader.Define(self._stage, Sdf.Path("/Mat/MdlSource"))
        external_source = UsdShade.Shader.Define(self._stage, Sdf.Path("/ExternalSource"))
        target = UsdShade.Shader.Define(self._stage, Sdf.Path("/Mat/MtlxTarget"))
        hidden_output = hidden_source.CreateOutput("out", Sdf.ValueTypeNames.Float)
        external_output = external_source.CreateOutput("out", Sdf.ValueTypeNames.Float)
        context_input = target.CreateInput("context", Sdf.ValueTypeNames.Float)
        external_input = target.CreateInput("external", Sdf.ValueTypeNames.Float)
        self.assertTrue(context_input.ConnectToSource(hidden_output))
        self.assertTrue(external_input.ConnectToSource(external_output))
        target_output = target.CreateOutput("out", Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput("mtlx").ConnectToSource(target_output)
        reachable = pipeline._collect_output_reachable_connectables(material.GetPrim())

        issues = pipeline._collect_invalid_connections(
            material.GetPrim(),
            [material.GetPrim(), target.GetPrim()],
            object(),
            "mtlx",
            lambda *_args: True,
            reachable,
        )
        by_code = {issue.code: issue for issue in issues}
        context_issue = by_code["INVALID_CONNECTION_OUTSIDE_CONTEXT"]
        root_issue = by_code["INVALID_CONNECTION_OUTSIDE_MATERIAL_ROOT"]

        self.assertEqual(context_issue.source_path, str(hidden_output.GetAttr().GetPath()))
        self.assertEqual(context_issue.target_path, str(context_input.GetAttr().GetPath()))
        self.assertEqual(context_issue.prim_path, context_issue.target_path)
        self.assertEqual(context_issue.root_path, "/Mat")
        self.assertIn("context 'mtlx'", context_issue.message)
        self.assertIn(context_issue.source_path, context_issue.message)
        self.assertIn(context_issue.target_path, context_issue.message)
        self.assertIn("active context graph", context_issue.message)

        self.assertEqual(root_issue.source_path, str(external_output.GetAttr().GetPath()))
        self.assertEqual(root_issue.target_path, str(external_input.GetAttr().GetPath()))
        self.assertEqual(root_issue.prim_path, root_issue.target_path)
        self.assertEqual(root_issue.root_path, "/Mat")
        self.assertIn("outside material root '/Mat'", root_issue.message)

    async def test_disconnected_fragment_connections_are_not_material_errors(self) -> None:
        """Connection issues become material errors only after their target reaches an output."""
        material = UsdShade.Material.Define(self._stage, Sdf.Path("/Mat"))
        hidden_source = UsdShade.Shader.Define(self._stage, Sdf.Path("/Mat/MdlSource"))
        target = UsdShade.Shader.Define(self._stage, Sdf.Path("/Mat/MtlxFragment"))
        hidden_output = hidden_source.CreateOutput("out", Sdf.ValueTypeNames.Float)
        target_input = target.CreateInput("in", Sdf.ValueTypeNames.Float)
        target_output = target.CreateOutput("out", Sdf.ValueTypeNames.Token)
        self.assertTrue(target_input.ConnectToSource(hidden_output))

        prims = [material.GetPrim(), target.GetPrim()]
        self.assertEqual(
            pipeline._collect_invalid_connections(
                material.GetPrim(), prims, object(), "mtlx", lambda *_args: True, set()
            ),
            [],
        )

        material.CreateSurfaceOutput("mtlx").ConnectToSource(target_output)
        reachable = pipeline._collect_output_reachable_connectables(material.GetPrim())
        issues = pipeline._collect_invalid_connections(
            material.GetPrim(), prims, object(), "mtlx", lambda *_args: True, reachable
        )
        self.assertEqual([issue.code for issue in issues], ["INVALID_CONNECTION_OUTSIDE_CONTEXT"])
        self.assertEqual(issues[0].source_path, str(hidden_output.GetAttr().GetPath()))
        self.assertEqual(issues[0].target_path, str(target_input.GetAttr().GetPath()))

    async def test_validate_invalid_root_and_plugin_issue_context(self) -> None:
        """Top-level validation should report invalid roots and attach context to plugin issues."""
        invalid_result = pipeline.validate_material_context(None, "test", object())
        self.assertEqual(invalid_result.issues[0].code, "MATERIAL_ROOT_INVALID")
        self.assertIn("context 'test'", invalid_result.issues[0].message)

        material = UsdShade.Material.Define(self._stage, Sdf.Path("/Mat"))
        issue = ValidationIssue(
            code="PLUGIN_ISSUE",
            message="plugin issue",
            severity=ValidationSeverity.WARNING,
        )
        plugin = SimpleNamespace(
            is_supported_prim=lambda prim: True,
            get_shader_node_for_prim=lambda prim: object(),
            get_validation_issues=lambda context, prim: [issue, issue],
        )
        with (
            patch.object(pipeline, "_collect_cycle_issues", return_value=[]),
            patch.object(pipeline, "_collect_mixed_networks", return_value=[]),
        ):
            result = pipeline.validate_material_context(material.GetPrim(), "test", plugin)
        plugin_issues = [entry for entry in result.issues if entry.code == "PLUGIN_ISSUE"]
        self.assertEqual(len(plugin_issues), 1)
        self.assertEqual(plugin_issues[0].context_name, "test")

    async def test_validation_failures_are_logged_and_return_visible_issues(self) -> None:
        """Unexpected collector failures should not terminate validation or look falsely clean."""
        material = UsdShade.Material.Define(self._stage, Sdf.Path("/Mat"))
        plugin = SimpleNamespace(
            is_supported_prim=lambda _prim: False,
            get_shader_node_for_prim=lambda _prim: None,
            get_validation_issues=MagicMock(side_effect=KeyError("plugin failed")),
        )

        with (
            patch.object(
                pipeline,
                "_collect_output_reachable_connectables",
                side_effect=OSError("reachability failed"),
            ),
            patch.object(pipeline, "_collect_invalid_nodes", return_value=[]),
            patch.object(pipeline, "_collect_invalid_nodegraphs", return_value=[]),
            patch.object(pipeline, "_collect_invalid_shader_ports", return_value=[]),
            patch.object(pipeline, "_collect_invalid_connections", return_value=[]),
            patch.object(pipeline, "_collect_cycle_issues", return_value=[]),
            patch.object(pipeline, "_collect_mixed_networks", return_value=[]),
            patch.object(pipeline, "log_exception") as log_failure,
        ):
            result = pipeline.validate_material_context(
                material.GetPrim(),
                "mtlx",
                plugin,
                model=SimpleNamespace(get_child_prims=lambda: []),
            )

        internal_issues = [issue for issue in result.issues if issue.code == "VALIDATION_INTERNAL_ERROR"]
        self.assertEqual(len(internal_issues), 2)
        self.assertTrue(all(issue.severity == ValidationSeverity.ERROR for issue in internal_issues))
        self.assertTrue(all(issue.context_name == "mtlx" for issue in internal_issues))
        self.assertEqual(log_failure.call_count, 2)
