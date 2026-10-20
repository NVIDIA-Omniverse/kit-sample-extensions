from unittest.mock import patch

import omni.kit.commands
import omni.kit.undo
from pxr import Sdf, Usd, UsdShade

from ...scripts.commands.impl.nodegraph import _normalize_connected_sources
from ...scripts.commands.impl.nodegraph import group as group_module
from ...scripts.commands.impl.nodegraph import helpers as helpers_module
from ...scripts.commands.impl.nodegraph.group import MaterialGraph_GroupNodeGraphCommand
from ...scripts.commands.result import CommandResult
from ...scripts.utils.sdr_wrappers import SdrRegistryWrapper
from .base import CommandsTestBase


class TestGroupNodeGraphCommand(CommandsTestBase):
    """GroupNodeGraph and UngroupNodeGraph commands move shader nodes into/out of a NodeGraph prim.
    We test that group creates a new nodegraph and moves nodes, ungroup restores them, undo/redo
    round-trips correctly, and _normalize_connected_sources handles tuple vs list return shapes."""

    async def setUp(self) -> None:
        """Load the simple scene for group/ungroup tests."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")

    def _create_shader(self, identifier: str) -> Sdf.Path:
        """Create a shader node under the material and return its path."""
        sdr_node = SdrRegistryWrapper().GetShaderNodeByIdentifier(identifier)
        self.assertIsNotNone(sdr_node)
        omni.kit.commands.execute(
            "MaterialGraph_NewUsdShadeNodeCommand",
            parent_path=self._material_path,
            node=sdr_node,
            position=(1, 2),
        )
        return self._material_path.AppendChild(identifier)

    async def test_group_nodes_creates_nodegraph(self) -> None:
        """Group moves nodes into a new nodegraph."""
        shader_a = self._create_shader("UsdPreviewSurface")
        shader_b = self._create_shader("UsdUVTexture")

        material_prim = self._get_prim_at_path(self._material_path)
        before_nodegraphs = {child.GetPath() for child in material_prim.GetChildren() if child.IsA(UsdShade.NodeGraph)}

        omni.kit.commands.execute(
            "MaterialGraph_GroupNodeGraphCommand",
            parent_path=self._material_path,
            selected_paths=[shader_a, shader_b],
            position=(5, 6),
        )

        after_nodegraphs = {child.GetPath() for child in material_prim.GetChildren() if child.IsA(UsdShade.NodeGraph)}
        created_path = next(iter(after_nodegraphs - before_nodegraphs), None)
        self.assertIsNotNone(created_path)

        moved_paths = [
            created_path.AppendChild(shader_a.name),
            created_path.AppendChild(shader_b.name),
        ]

        def _after() -> None:
            """Validate nodegraph grouping after redo."""
            self.assertTrue(self._stage.GetPrimAtPath(created_path))
            for moved in moved_paths:
                self.assertTrue(self._stage.GetPrimAtPath(moved))

        def _before() -> None:
            """Validate nodegraph ungrouped state after undo."""
            self.assertFalse(self._stage.GetPrimAtPath(created_path))
            self.assertTrue(self._stage.GetPrimAtPath(shader_a))
            self.assertTrue(self._stage.GetPrimAtPath(shader_b))

        await self._assert_undo_redo(_before, _after)

    async def test_group_inside_nodegraph_preserves_interface_port_names(self) -> None:
        """Nested grouping should reuse parent interface names instead of child_port names."""
        parent_graph_path = self._material_path.AppendChild("ParentGraph")
        parent_graph = UsdShade.NodeGraph.Define(self._stage, parent_graph_path)
        parent_input = parent_graph.CreateInput("a", Sdf.ValueTypeNames.Float)
        parent_output = parent_graph.CreateOutput("out", Sdf.ValueTypeNames.Float)
        shader = UsdShade.Shader.Define(self._stage, parent_graph_path.AppendChild("abs"))
        shader_path = shader.GetPrim().GetPath()
        shader_input = shader.CreateInput("a", Sdf.ValueTypeNames.Float)
        shader_output = shader.CreateOutput("out", Sdf.ValueTypeNames.Float)
        shader_input.ConnectToSource(parent_input)
        parent_output.ConnectToSource(shader_output)

        omni.kit.commands.execute(
            "MaterialGraph_GroupNodeGraphCommand",
            parent_path=parent_graph_path,
            selected_paths=[shader_path],
            position=(5, 6),
        )

        def _nested_graph() -> UsdShade.NodeGraph:
            """Return the single nested graph created by grouping."""
            nested_graphs = [child for child in parent_graph.GetPrim().GetChildren() if child.IsA(UsdShade.NodeGraph)]
            self.assertEqual(len(nested_graphs), 1)
            return UsdShade.NodeGraph(nested_graphs[0])

        nested = _nested_graph()
        output_names = [output.GetBaseName() for output in nested.GetOutputs()]
        self.assertIn("out", output_names)
        self.assertFalse(nested.GetPrim().HasAttribute("outputs:abs_out"))

        def _after() -> None:
            """Validate nested grouping after redo."""
            nested = _nested_graph()
            self.assertTrue(nested.GetPrim().HasAttribute("inputs:a"))
            self.assertFalse(nested.GetPrim().HasAttribute("inputs:abs_a"))

        def _before() -> None:
            """Validate nested grouping is undone."""
            nested_graphs = [child for child in parent_graph.GetPrim().GetChildren() if child.IsA(UsdShade.NodeGraph)]
            self.assertEqual(nested_graphs, [])
            self.assertTrue(self._stage.GetPrimAtPath(shader_path))

        await self._assert_undo_redo(_before, _after)

    async def test_failed_group_move_rolls_children_back_before_cleanup(self) -> None:
        """A false move result after mutation must never delete already-moved children."""
        shader_a = self._create_shader("UsdPreviewSurface")
        shader_b = self._create_shader("UsdUVTexture")
        material = self._stage.GetPrimAtPath(self._material_path)
        nodegraphs_before = {child.GetPath() for child in material.GetChildren() if child.IsA(UsdShade.NodeGraph)}
        original_execute = group_module.execute_command
        first_move = True

        def _execute_then_report_failure(command_name: str, **kwargs):
            nonlocal first_move
            result = original_execute(command_name, **kwargs)
            if command_name == "MovePrims" and first_move:
                first_move = False
                self.assertTrue(result.success)
                return CommandResult(False, None, message="injected post-move failure", error_code="injected")
            return result

        command = MaterialGraph_GroupNodeGraphCommand(
            parent_path=self._material_path,
            selected_paths=[shader_a, shader_b],
            position=(5, 6),
            stage=self._stage,
        )
        with patch.object(group_module, "execute_command", side_effect=_execute_then_report_failure):
            self.assertIsNone(command.do())

        self.assertTrue(self._stage.GetPrimAtPath(shader_a))
        self.assertTrue(self._stage.GetPrimAtPath(shader_b))
        nodegraphs_after = {child.GetPath() for child in material.GetChildren() if child.IsA(UsdShade.NodeGraph)}
        self.assertEqual(nodegraphs_after, nodegraphs_before)

    async def test_ungroup_restores_children(self) -> None:
        """Ungroup moves children back to parent."""
        shader_a = self._create_shader("UsdPreviewSurface")
        shader_b = self._create_shader("UsdUVTexture")

        material_prim = self._get_prim_at_path(self._material_path)
        before_nodegraphs = {child.GetPath() for child in material_prim.GetChildren() if child.IsA(UsdShade.NodeGraph)}

        omni.kit.commands.execute(
            "MaterialGraph_GroupNodeGraphCommand",
            parent_path=self._material_path,
            selected_paths=[shader_a, shader_b],
            position=(5, 6),
        )

        after_nodegraphs = {child.GetPath() for child in material_prim.GetChildren() if child.IsA(UsdShade.NodeGraph)}
        created_path = next(iter(after_nodegraphs - before_nodegraphs), None)
        self.assertIsNotNone(created_path)

        moved_paths = [
            created_path.AppendChild(shader_a.name),
            created_path.AppendChild(shader_b.name),
        ]
        nodegraph_prim = self._stage.GetPrimAtPath(created_path)
        nodegraph_prim.SetMetadata("displayName", "Audited NodeGraph")
        nodegraph_prim.SetCustomDataByKey("audit:marker", "preserve")
        custom_attr = nodegraph_prim.CreateAttribute("audit:animated", Sdf.ValueTypeNames.Float, custom=True)
        custom_attr.Set(1.25)
        custom_attr.Set(2.5, Usd.TimeCode(1.0))

        success, ungrouped = omni.kit.commands.execute(
            "MaterialGraph_UngroupNodeGraphCommand",
            nodegraph_path=created_path,
        )

        self.assertTrue(success)
        self.assertTrue(ungrouped)

        def _after() -> None:
            """Validate nodegraph removal after redo."""
            self.assertFalse(self._stage.GetPrimAtPath(created_path))
            self.assertTrue(self._stage.GetPrimAtPath(shader_a))
            self.assertTrue(self._stage.GetPrimAtPath(shader_b))

        def _before() -> None:
            """Validate nodegraph contents after undo."""
            self.assertTrue(self._stage.GetPrimAtPath(created_path))
            for moved in moved_paths:
                self.assertTrue(self._stage.GetPrimAtPath(moved))
            restored = self._stage.GetPrimAtPath(created_path)
            self.assertEqual(restored.GetMetadata("displayName"), "Audited NodeGraph")
            self.assertEqual(restored.GetCustomDataByKey("audit:marker"), "preserve")
            restored_attr = restored.GetAttribute("audit:animated")
            self.assertTrue(restored_attr)
            self.assertTrue(restored_attr.IsCustom())
            self.assertEqual(restored_attr.Get(), 1.25)
            self.assertEqual(restored_attr.Get(Usd.TimeCode(1.0)), 2.5)

        await self._assert_undo_redo(_before, _after)

    async def test_failed_group_rewire_restores_exact_edit_layer(self) -> None:
        """A nested connection-command failure must roll back the complete grouping transaction."""
        source_path = self._create_shader("UsdPreviewSurface")
        consumer_path = self._create_shader("UsdUVTexture")
        source = UsdShade.Shader(self._stage.GetPrimAtPath(source_path))
        consumer = UsdShade.Shader(self._stage.GetPrimAtPath(consumer_path))
        source_output = source.CreateOutput("audit", Sdf.ValueTypeNames.Float)
        consumer_input = consumer.CreateInput("audit", Sdf.ValueTypeNames.Float)
        self.assertTrue(consumer_input.ConnectToSource(source_output))
        layer = self._stage.GetEditTarget().GetLayer()
        before = layer.ExportToString()

        failure = CommandResult(False, None, message="injected rewire failure", error_code="injected")
        with patch.object(helpers_module, "ConnectPortToSource", return_value=failure):
            success, grouped = omni.kit.commands.execute(
                "MaterialGraph_GroupNodeGraphCommand",
                parent_path=self._material_path,
                selected_paths=[source_path],
                position=(5, 6),
                stage=self._stage,
            )

        # Kit reports that the command invocation itself completed; the empty
        # payload is the Material Graph operation failure.
        self.assertTrue(success)
        self.assertIsNone(grouped)
        self.assertEqual(layer.ExportToString(), before)
        self.assertTrue(self._stage.GetPrimAtPath(source_path))
        self.assertTrue(self._stage.GetPrimAtPath(consumer_path))
        omni.kit.undo.undo()
        omni.kit.undo.redo()
        self.assertEqual(layer.ExportToString(), before)

    async def test_failed_ungroup_move_restores_exact_edit_layer(self) -> None:
        """Ungroup must compensate all rewiring when its structural move fails."""
        shader_a = self._create_shader("UsdPreviewSurface")
        shader_b = self._create_shader("UsdUVTexture")
        material = self._stage.GetPrimAtPath(self._material_path)
        before_graphs = {child.GetPath() for child in material.GetChildren() if child.IsA(UsdShade.NodeGraph)}
        grouped = MaterialGraph_GroupNodeGraphCommand(
            parent_path=self._material_path,
            selected_paths=[shader_a, shader_b],
            position=(5, 6),
            stage=self._stage,
        ).do()
        self.assertTrue(grouped)
        nodegraph_path = grouped.GetPath()
        layer = self._stage.GetEditTarget().GetLayer()
        before = layer.ExportToString()
        undo_count = len(omni.kit.undo.get_undo_stack())
        failure = CommandResult(False, None, message="injected move failure", error_code="injected")

        with patch.object(helpers_module, "MovePrims", return_value=failure):
            self.assertFalse(helpers_module._ungroup_nodegraph(self._stage, grouped))

        self.assertEqual(layer.ExportToString(), before)
        self.assertTrue(self._stage.GetPrimAtPath(nodegraph_path))
        after_graphs = {child.GetPath() for child in material.GetChildren() if child.IsA(UsdShade.NodeGraph)}
        self.assertEqual(after_graphs - before_graphs, {nodegraph_path})
        self.assertEqual(len(omni.kit.undo.get_undo_stack()), undo_count)
        self.assertEqual(layer.ExportToString(), before)

    async def test_normalize_connected_sources_tuple(self) -> None:
        """Connected sources normalization should handle tuple shapes."""

        class DummyPort:
            """Dummy port returning tuple-form connections."""

            def GetConnectedSources(self) -> tuple[list[int], None]:
                """Return tuple-form connected sources."""
                return ([1, 2, 3], None)

        self.assertEqual(_normalize_connected_sources(DummyPort()), [1, 2, 3])

    async def test_normalize_connected_sources_list(self) -> None:
        """Normalize handles list-shaped GetConnectedSources."""

        class DummyPort:
            """Dummy port returning list-form connections."""

            def GetConnectedSources(self) -> list[int]:
                """Return list-form connected sources."""
                return [1, 2]

        self.assertEqual(_normalize_connected_sources(DummyPort()), [1, 2])
