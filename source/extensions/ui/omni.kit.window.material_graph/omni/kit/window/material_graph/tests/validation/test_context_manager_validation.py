# pylint: disable=relative-beyond-top-level,protected-access,no-member
from unittest.mock import patch

from pxr import Sdf, UsdShade

from ...scripts.config.paths import Paths
from ...scripts.models.graph.isolation import MaterialGraphIsolationModel
from ..context.base import ContextManagerTestBase


class TestContextManagerValidation(ContextManagerTestBase):
    """Validation behavior for root/context checks and validator issue production."""

    async def setUp(self) -> None:
        """Load a shared scene for root validation tests."""
        await super().setUp()
        await self._load_scene("cube.usda")
        self._material_path = Sdf.Path("/World/Looks/PreviewSurfaceTexture")
        self._cube_path = Sdf.Path("/World/Cube")

    async def test_load_rejects_empty_path(self) -> None:
        """Empty path fails to load."""
        self.assertFalse(self._manager.load(Sdf.Path()))
        self.assertIn("Material prim not found", self._manager.get_last_error() or "")

    async def test_invalidate_root_clears_contexts(self) -> None:
        """_invalidate_root clears cached contexts and root prim."""
        self.assertTrue(self._manager.load(self._material_path))
        plugins = list(self._manager.get_plugins())
        self.assertTrue(plugins)
        context_name = plugins[0].name
        self.assertTrue(self._manager.add_context(context_name))

        self._manager._invalidate_root("No USD stage")
        self.assertEqual(self._manager.get_context_names(), [])
        self.assertIsNone(self._manager._root_prim)
        self.assertEqual(self._manager.get_last_error(), "No USD stage")

    async def test_validate_root_rejects_non_material(self) -> None:
        """_validate_root_or_invalidate rejects non-material prims."""
        self._manager._root_prim = self._get_prim_at_path(self._cube_path)
        self.assertFalse(self._manager._validate_root_or_invalidate())
        self.assertIsNone(self._manager._root_prim)
        self.assertEqual(self._manager.get_last_error(), "Root prim is not a Material")

    async def test_validate_root_rejects_missing_prim(self) -> None:
        """_validate_root_or_invalidate invalidates missing prims."""
        self.assertTrue(self._manager.load(self._material_path))
        self.assertTrue(self._stage.RemovePrim(self._material_path))
        self.assertFalse(self._manager._validate_root_or_invalidate())
        self.assertFalse(self._manager._root_prim and self._manager._root_prim.IsValid())
        self.assertEqual(self._manager.get_context_names(), [])

    async def test_validate_context_reports_unsupported_nodes(self) -> None:
        """Validation reports unsupported nodes for active context."""
        material = UsdShade.Material.Define(self._stage, Sdf.Path("/World/Looks/MatUnsupported"))
        shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/MatUnsupported/Shader"))
        shader.CreateOutput("out", Sdf.ValueTypeNames.Float)
        material.CreateSurfaceOutput("mdl").ConnectToSource(shader.ConnectableAPI(), "out")

        self.assertTrue(self._manager.load(material.GetPath()))
        self.assertTrue(self._manager.add_context("mdl"))

        result = self._manager.validate_context("mdl")
        codes = {issue.code for issue in result.issues}
        self.assertIn("MIXED_NETWORK_CONTEXT", codes)

    async def test_validate_context_reports_invalid_shader_ports(self) -> None:
        """Validation reports shader ports not defined by SDR or schema."""
        material = UsdShade.Material.Define(self._stage, Sdf.Path("/World/Looks/MatInvalidPorts"))
        shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/MatInvalidPorts/Shader"))
        shader.GetPrim().CreateAttribute("inputs:custom_not_declared", Sdf.ValueTypeNames.Float)
        shader.CreateOutput("out", Sdf.ValueTypeNames.Float)
        material.CreateSurfaceOutput("mdl").ConnectToSource(shader.ConnectableAPI(), "out")

        self.assertTrue(self._manager.load(material.GetPath()))
        self.assertTrue(self._manager.add_context("mdl"))
        handle = self._manager.get_context("mdl")

        class _DummySdrNode:
            """Minimal SDR node shim exposing declared port names."""

            @staticmethod
            def GetShaderInputNames():
                return ["in"]

            @staticmethod
            def GetShaderOutputNames():
                return ["out"]

        handle.plugin.get_shader_node_for_prim = lambda _prim: _DummySdrNode()

        result = self._manager.validate_context("mdl")
        self.assertTrue(any(issue.code == "INVALID_SHADER_PORT_DEFINITION" for issue in result.issues))

    async def test_universal_unresolved_shader_is_visible_and_reported(self) -> None:
        """An unresolved Universal shader should remain visible and report its missing definition."""
        await self._load_scene("error.usda")
        material_path = Sdf.Path("/World/Looks/PreviewSurfaceTexture")
        unresolved_path = material_path.AppendChild("error_float")

        self.assertTrue(self._manager.load(material_path))
        self.assertTrue(self._manager.add_context("universal"))
        handle = self._manager.get_context("universal")
        child_paths = {prim.GetPath() for prim in handle.context.model.get_child_prims()}

        self.assertIn(unresolved_path, child_paths)
        self.assertTrue(handle.context.model.valid)
        unresolved_model = handle.context.model.get_item_model(unresolved_path)
        self.assertIsNotNone(unresolved_model)
        self.assertFalse(unresolved_model.valid)
        result = self._manager.validate_context("universal")
        missing_issue = next(
            issue
            for issue in result.issues
            if issue.code == "INVALID_NODE_DEFINITION_MISSING" and issue.prim_path == str(unresolved_path)
        )
        self.assertEqual(missing_issue.prim_path, str(unresolved_path))
        self.assertIn("identifier=Error", missing_issue.message)
        self.assertNotIn("INVALID_CONNECTION_OUTSIDE_ROOT", {issue.code for issue in result.issues})

    async def test_missing_mdl_asset_keeps_graph_open_and_renders_error_node(self) -> None:
        """A missing MDL source asset remains a visible fallback node in an open graph."""

        missing_asset = Sdf.AssetPath("./__missing_material_graph_asset__.mdl")
        material, shader = self._define_mdl_reference_material("MatMissingAsset", missing_asset, "::missing_material()")

        mdl_plugin = next(plugin for plugin in self._manager.get_plugins() if plugin.name == "mdl")
        # The renderer logs an expected compiler error when asked to resolve a
        # deliberately absent module.  Model that failed lookup at the plugin
        # boundary so this extension regression does not contaminate the
        # process-wide MDLC error stream.
        with (
            patch.object(mdl_plugin, "get_shader_node_for_prim", return_value=None),
            patch.object(mdl_plugin, "_is_polymorphic_enabled", return_value=False),
        ):
            issue = self._assert_invalid_reference_graph(material, shader, "mdl")
        self.assertIn("__missing_material_graph_asset__.mdl", issue.message)
        self.assertIn("subIdentifier=::missing_material()", issue.message)

    async def test_missing_mdl_subidentifier_keeps_graph_open_and_renders_error_node(self) -> None:
        """A missing subidentifier in an existing MDL asset remains visible and actionable."""

        test_module = str(Paths.DATA_PATH / "tests" / "mdl" / "test_poly_abs.mdl")
        source_asset = Sdf.AssetPath(test_module, test_module)
        material, shader = self._define_mdl_reference_material(
            "MatMissingSubIdentifier", source_asset, "::definitely_missing_material()"
        )

        issue = self._assert_invalid_reference_graph(material, shader, "mdl")
        self.assertIn("test_poly_abs.mdl", issue.message)
        self.assertIn("subIdentifier=::definitely_missing_material()", issue.message)

    async def test_missing_materialx_identifier_keeps_graph_open_and_renders_error_node(self) -> None:
        """An unresolved MaterialX identifier remains visible and uses node validation styling."""

        material_path = Sdf.Path("/World/Looks/MatMissingMtlxIdentifier")
        material = UsdShade.Material.Define(self._stage, material_path)
        shader = UsdShade.Shader.Define(self._stage, material_path.AppendChild("MissingNode"))
        shader.CreateIdAttr("ND_definitely_missing_material_graph_test")
        shader.CreateOutput("out", Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput("mtlx").ConnectToSource(shader.ConnectableAPI(), "out")

        issue = self._assert_invalid_reference_graph(material, shader, "mtlx")
        self.assertIn("identifier=ND_definitely_missing_material_graph_test", issue.message)

    async def test_nested_graph_with_unresolved_shader_remains_open_and_reports_children(self) -> None:
        """Invalid descendants do not invalidate a NodeGraph container or prevent isolation."""

        material_path = Sdf.Path("/World/Looks/MatNestedMissingIdentifier")
        material = UsdShade.Material.Define(self._stage, material_path)
        nodegraph = UsdShade.NodeGraph.Define(self._stage, material_path.AppendChild("Compound"))
        shader = UsdShade.Shader.Define(self._stage, nodegraph.GetPrim().GetPath().AppendChild("MissingNode"))
        shader.CreateIdAttr("MissingNestedUniversalDefinition")
        shader_output = shader.CreateOutput("out", Sdf.ValueTypeNames.Float)
        graph_output = nodegraph.CreateOutput("out", Sdf.ValueTypeNames.Float)
        graph_output.ConnectToSource(shader_output)
        material.CreateSurfaceOutput("universal").ConnectToSource(graph_output)

        self.assertTrue(self._manager.load(material.GetPath()))
        self.assertTrue(self._manager.add_context("universal"))
        model = self._manager.get_context("universal").context.model
        model.active = True
        nodegraph_model = model.get_item_model(nodegraph.GetPrim().GetPath())
        self.assertIsNotNone(nodegraph_model)
        self.assertTrue(nodegraph_model.valid)
        self.assertTrue(nodegraph_model.has_invalid_connected_children())

        isolation = MaterialGraphIsolationModel(nodegraph_model, nodegraph_model)
        try:
            snapshot = isolation.export_snapshot(True)
            missing_node = next(entry for entry in snapshot if getattr(entry["node"], "prim", None) == shader.GetPrim())
            self.assertEqual(missing_node["valid_state"], 2)
            self.assertTrue(missing_node["ports"])
        finally:
            isolation.destroy()

        result = self._manager.validate_context("universal")
        issues_by_code = {issue.code: issue for issue in result.issues}
        self.assertEqual(
            issues_by_code["INVALID_NODE_DEFINITION_MISSING"].prim_path,
            str(shader.GetPrim().GetPath()),
        )
        self.assertEqual(
            issues_by_code["INVALID_NODEGRAPH_CHILDREN"].prim_path,
            str(nodegraph.GetPrim().GetPath()),
        )

    def _define_mdl_reference_material(
        self, name: str, source_asset: Sdf.AssetPath, subidentifier: str
    ) -> tuple[UsdShade.Material, UsdShade.Shader]:
        """Author a material driven by one source-asset MDL shader reference."""

        material_path = Sdf.Path(f"/World/Looks/{name}")
        material = UsdShade.Material.Define(self._stage, material_path)
        shader = UsdShade.Shader.Define(self._stage, material_path.AppendChild("MissingNode"))
        api = UsdShade.NodeDefAPI(shader.GetPrim())
        api.SetSourceAsset(source_asset, "mdl")
        api.SetSourceAssetSubIdentifier(subidentifier, "mdl")
        shader.CreateOutput("out", Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput("mdl").ConnectToSource(shader.ConnectableAPI(), "out")
        return material, shader

    def _assert_invalid_reference_graph(self, material: UsdShade.Material, shader: UsdShade.Shader, context_name: str):
        """Assert context load, fallback rendering, and validation for one bad reference."""

        self.assertTrue(self._manager.load(material.GetPath()))
        self.assertTrue(self._manager.add_context(context_name))
        handle = self._manager.get_context(context_name)
        self.assertTrue(handle.is_valid)
        model = handle.context.model
        model.active = True
        self.assertTrue(model.valid)

        shader_path = shader.GetPrim().GetPath()
        self.assertIn(shader_path, {prim.GetPath() for prim in model.get_child_prims()})
        shader_model = model.get_item_model(shader_path)
        self.assertIsNotNone(shader_model)
        self.assertFalse(shader_model.valid)

        isolation = MaterialGraphIsolationModel(model, model)
        try:
            snapshot = isolation.export_snapshot(True)
            node = next(entry for entry in snapshot if getattr(entry["node"], "prim", None) == shader.GetPrim())
            self.assertEqual(node["valid_state"], 2)
            self.assertTrue(node["ports"])
        finally:
            isolation.destroy()

        result = self._manager.validate_context(context_name)
        issue = next(
            issue
            for issue in result.issues
            if issue.code == "INVALID_NODE_DEFINITION_MISSING" and issue.prim_path == str(shader_path)
        )
        self.assertTrue(issue.message)
        return issue
