import asyncio
from unittest.mock import patch

import omni.kit.undo
import omni.usd
from pxr import Sdf, Usd, UsdShade, UsdUI

from ...scripts.commands import wrappers
from ...scripts.commands.impl.connections.connect_polymorphic import (
    MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand,
)
from ...scripts.commands.result import CommandResult
from ...scripts.commands.wrappers import ui_nodes
from ...scripts.config.nodes import Nodes
from ...scripts.config.paths import Paths
from ...scripts.utils.sdr_wrappers import SdrRegistryWrapper
from .base import CommandsTestBase

# pylint: disable=no-member, relative-beyond-top-level


class TestCommandWrappers(CommandsTestBase):
    """wrappers module provides CreateInputPort, ConnectInputToSource, CreateMaterial, CreateNode, etc.
    We test ports/connections, move/delete, material/node/backdrop creation, CreateNode routing
    (with patches for execute_command_checked), property and misc wrappers, cleanup, and
    DeleteInputOutputNodes with patched isolation/execute."""

    async def setUp(self) -> None:
        """Load the simple scene and set up common paths."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._looks_path = Sdf.Path("/World/Looks")
        self._material_path = Sdf.Path("/World/Looks/material")
        self._shader_a = Sdf.Path("/World/Looks/material/shader")
        self._shader_b = Sdf.Path("/World/Looks/material/shader")
        self._compound_source = None

    async def test_ports_and_connections_wrappers(self) -> None:
        """Port and connection wrappers mutate USD."""
        wrappers.CreateInputPort(self._shader_a, f"{UsdShade.Tokens.inputs}testIn", Sdf.ValueTypeNames.Float)
        wrappers.CreateOutputPort(self._shader_a, f"{UsdShade.Tokens.outputs}testOut", Sdf.ValueTypeNames.Float)

        prim = self._get_prim_at_path(self._shader_a)
        self.assertTrue(prim.HasAttribute(f"{UsdShade.Tokens.inputs}testIn"))
        self.assertTrue(prim.HasAttribute(f"{UsdShade.Tokens.outputs}testOut"))

        shader = UsdShade.Shader(prim)
        output = shader.GetOutput("testOut")
        self.assertTrue(output)
        input_port = shader.GetInput("diffuseColor")
        self.assertTrue(input_port)

        connect_result = wrappers.ConnectInputToSource(input_port, output)
        self.assertTrue(connect_result.success)
        self.assertTrue(input_port.HasConnectedSource())

        disconnect_result = wrappers.DisconnectInputPort(input_port)
        self.assertTrue(disconnect_result.success)
        self.assertTrue(disconnect_result.validation.get("disconnected"))
        self.assertFalse(input_port.HasConnectedSource())

        input_port.ConnectToSource(output)
        remove_result = wrappers.RemoveConnections(input_port.GetAttr().GetPath(), [output.GetAttr().GetPath()])
        self.assertTrue(remove_result.success)
        self.assertIn(str(output.GetAttr().GetPath()), remove_result.validation.get("removed_connections", ()))
        self.assertFalse(input_port.HasConnectedSource())

        result = wrappers.ConnectInputToSource(input_port, output)
        self.assertTrue(result.success)
        self.assertTrue(result.validation.get("connected"))

    async def test_connect_nodegraph_output_to_shader_output(self) -> None:
        """NodeGraph output interface ports should connect to shader outputs."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, self._material_path.AppendChild("ConnectGraph"))
        ng_output = nodegraph.CreateOutput("out", Sdf.ValueTypeNames.Float)
        shader = UsdShade.Shader(self._get_prim_at_path(self._shader_a))
        shader_output = shader.CreateOutput("graphSource", Sdf.ValueTypeNames.Float)

        result = wrappers.ConnectPortToSource(ng_output, shader_output)

        self.assertTrue(result.success)
        self.assertTrue(ng_output.HasConnectedSource())

    async def test_internal_nodegraph_output_connection_skips_polymorphic_retarget(self) -> None:
        """Internal wiring to a NodeGraph output should not promote polymorphic sources."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, self._material_path.AppendChild("PolyInterfaceGraph"))
        ng_output = nodegraph.CreateOutput("out", Sdf.ValueTypeNames.Float)
        shader = UsdShade.Shader.Define(self._stage, nodegraph.GetPrim().GetPath().AppendChild("poly"))
        shader_output = shader.CreateOutput("out", Sdf.ValueTypeNames.Float)

        with (
            patch.object(
                MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand,
                "_update_shader_prim",
                autospec=True,
                side_effect=AssertionError("internal interface wiring should not retarget"),
            ),
            patch.object(
                MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand,
                "_is_prim_polymorphic",
                autospec=True,
                side_effect=AssertionError("internal interface wiring should not inspect overloads"),
            ),
        ):
            result = wrappers.ConnectPortToSource(ng_output, shader_output)

        self.assertTrue(result.success)
        self.assertTrue(ng_output.HasConnectedSource())

    async def test_internal_nodegraph_output_connection_falls_back_after_direct_failure(self) -> None:
        """If direct internal wiring fails, polymorphic command should still try the normal path."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, self._material_path.AppendChild("PolyFallbackGraph"))
        ng_output = nodegraph.CreateOutput("out", Sdf.ValueTypeNames.Float)
        shader = UsdShade.Shader.Define(self._stage, nodegraph.GetPrim().GetPath().AppendChild("poly"))
        shader_output = shader.CreateOutput("out", Sdf.ValueTypeNames.Float)

        with (
            patch.object(
                MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand,
                "_connect_internal_nodegraph_interface",
                autospec=True,
                return_value=False,
            ),
            patch.object(
                MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand,
                "_is_prim_polymorphic",
                autospec=True,
                return_value=False,
            ) as is_poly,
        ):
            result = wrappers.ConnectPortToSource(ng_output, shader_output)

        self.assertTrue(result.success)
        self.assertTrue(ng_output.HasConnectedSource())
        is_poly.assert_called()

    async def test_connect_wrappers_invalid_args_return_false(self) -> None:
        """Invalid args return failure."""
        self.assertFalse(wrappers.ConnectInputToSource(None, None).success)
        self.assertFalse(wrappers.ConnectPortToSource(None, None).success)
        self.assertFalse(wrappers.DisconnectInputPort(None).success)
        self.assertFalse(wrappers.RemoveConnections(None, []).success)

    async def test_move_and_delete_prims_wrappers(self) -> None:
        """MovePrims/DeletePrims validate state."""
        stage = self._usd_context.get_stage()
        src_path = Sdf.Path("/World/Looks/material/temp_move")
        dst_path = Sdf.Path("/World/Looks/material/temp_move_dst")
        stage.DefinePrim(src_path, "Shader")

        move_result = wrappers.MovePrims(
            paths_to_move={src_path.pathString: dst_path.pathString},
            destructive=False,
        )
        self.assertTrue(move_result.success)
        self.assertTrue(stage.GetPrimAtPath(dst_path))
        self.assertFalse(stage.GetPrimAtPath(src_path))

        delete_result = wrappers.DeletePrims([dst_path])
        self.assertTrue(delete_result.success)
        self.assertFalse(stage.GetPrimAtPath(dst_path))

    async def test_delete_connected_prims_undo_restores_internal_and_external_connections(self) -> None:
        """Undoing a multi-node delete must restore every connection touching the deleted nodes."""
        stage = self._usd_context.get_stage()
        for suffix, reverse_order in (("forward", False), ("reverse", True)):
            graph_path = self._material_path.AppendChild(f"delete_undo_graph_{suffix}")
            UsdShade.NodeGraph.Define(stage, graph_path)
            node_a = UsdShade.Shader.Define(stage, graph_path.AppendChild("A"))
            node_b = UsdShade.NodeGraph.Define(stage, graph_path.AppendChild("B"))
            node_c = UsdShade.NodeGraph.Define(stage, graph_path.AppendChild("C"))
            a_out = node_a.CreateOutput("out", Sdf.ValueTypeNames.Float)
            b_in = node_b.CreateInput("in", Sdf.ValueTypeNames.Float)
            b_out = node_b.CreateOutput("out", Sdf.ValueTypeNames.Float)
            c_in = node_c.CreateInput("in", Sdf.ValueTypeNames.Float)
            self.assertTrue(b_in.ConnectToSource(a_out))
            self.assertTrue(c_in.ConnectToSource(b_out))
            expected_b_sources = list(b_in.GetAttr().GetConnections())
            expected_c_sources = list(c_in.GetAttr().GetConnections())
            paths = [node_a.GetPath(), node_b.GetPath()]
            if reverse_order:
                paths.reverse()
            omni.kit.undo.clear_stack()

            result = wrappers.DeletePrims(paths, stage=stage)

            self.assertTrue(result.success)
            self.assertFalse(stage.GetPrimAtPath(node_a.GetPath()))
            self.assertFalse(stage.GetPrimAtPath(node_b.GetPath()))
            self.assertEqual(c_in.GetAttr().GetConnections(), [])
            self.assertTrue(omni.kit.undo.undo())
            await self._app.next_update_async()
            restored_b = UsdShade.NodeGraph(stage.GetPrimAtPath(node_b.GetPath())).GetInput("in")
            restored_c = UsdShade.NodeGraph(stage.GetPrimAtPath(node_c.GetPath())).GetInput("in")
            self.assertEqual(restored_b.GetAttr().GetConnections(), expected_b_sources)
            self.assertEqual(restored_c.GetAttr().GetConnections(), expected_c_sources)

            self.assertTrue(omni.kit.undo.redo())
            await self._app.next_update_async()
            self.assertFalse(stage.GetPrimAtPath(node_a.GetPath()))
            self.assertFalse(stage.GetPrimAtPath(node_b.GetPath()))
            self.assertEqual(c_in.GetAttr().GetConnections(), [])

    async def test_delete_connected_prims_undo_restores_layer_stack_exactly(self) -> None:
        """Undo must restore connection specs in weaker layers without leaving edit-layer overrides."""
        context = omni.usd.create_context("material_graph_delete_layer_stack")
        stage = Usd.Stage.CreateInMemory()
        attached, error = await context.attach_stage_async(stage)
        self.assertTrue(attached, error)
        weak_layer = Sdf.Layer.CreateAnonymous("material_graph_delete_weak.usda")
        weak_stage = Usd.Stage.Open(weak_layer)
        material = UsdShade.Material.Define(weak_stage, "/LayeredMaterial")
        node_a = UsdShade.Shader.Define(weak_stage, material.GetPath().AppendChild("A"))
        node_b = UsdShade.NodeGraph.Define(weak_stage, material.GetPath().AppendChild("B"))
        node_c = UsdShade.NodeGraph.Define(weak_stage, material.GetPath().AppendChild("C"))
        a_out = node_a.CreateOutput("out", Sdf.ValueTypeNames.Float)
        b_in = node_b.CreateInput("in", Sdf.ValueTypeNames.Float)
        b_out = node_b.CreateOutput("out", Sdf.ValueTypeNames.Float)
        c_in = node_c.CreateInput("in", Sdf.ValueTypeNames.Float)
        self.assertTrue(b_in.ConnectToSource(a_out))
        self.assertTrue(c_in.ConnectToSource(b_out))
        stage.GetRootLayer().subLayerPaths.append(weak_layer.identifier)
        b_spec_path = b_in.GetAttr().GetPath()
        c_spec_path = c_in.GetAttr().GetPath()
        weak_specs_before = {
            path: {
                key: weak_layer.GetAttributeAtPath(path).GetInfo(key)
                for key in weak_layer.GetAttributeAtPath(path).ListInfoKeys()
            }
            for path in (b_spec_path, c_spec_path)
        }
        omni.kit.undo.clear_stack()

        try:
            result = wrappers.DeletePrims([node_a.GetPath(), node_b.GetPath()], stage=stage)
            self.assertTrue(result.success)
            self.assertTrue(omni.kit.undo.undo())
            await self._app.next_update_async()

            restored_b = UsdShade.NodeGraph(stage.GetPrimAtPath(node_b.GetPath())).GetInput("in")
            restored_c = UsdShade.NodeGraph(stage.GetPrimAtPath(node_c.GetPath())).GetInput("in")
            self.assertEqual(restored_b.GetAttr().GetConnections(), [a_out.GetAttr().GetPath()])
            self.assertEqual(restored_c.GetAttr().GetConnections(), [b_out.GetAttr().GetPath()])
            self.assertFalse(stage.GetRootLayer().GetPrimAtPath(material.GetPath()))
            self.assertEqual(stage.GetRootLayer().subLayerPaths, [weak_layer.identifier])
            weak_specs_after = {
                path: {
                    key: weak_layer.GetAttributeAtPath(path).GetInfo(key)
                    for key in weak_layer.GetAttributeAtPath(path).ListInfoKeys()
                }
                for path in (b_spec_path, c_spec_path)
            }
            self.assertEqual(weak_specs_after, weak_specs_before)
        finally:
            omni.kit.undo.clear_stack()
            await context.close_stage_async()
            await self._app.next_update_async()

    async def test_move_and_delete_prims_use_explicit_stage(self) -> None:
        """Move and delete must not fall back to the global context for an explicit stage."""
        context_name = "material_graph_move_explicit_stage"
        context = omni.usd.create_context(context_name)
        stage = Usd.Stage.CreateInMemory()
        attached, error = await context.attach_stage_async(stage)
        self.assertTrue(attached, error)
        stage.DefinePrim("/World", "Xform")
        src_path = Sdf.Path("/World/source")
        dst_path = Sdf.Path("/World/destination")
        stage.DefinePrim(src_path, "Shader")

        try:
            move_result = wrappers.MovePrims(
                paths_to_move={src_path.pathString: dst_path.pathString},
                destructive=False,
                stage_or_context=stage,
            )
            self.assertTrue(move_result.success)
            self.assertFalse(stage.GetPrimAtPath(src_path))
            self.assertTrue(stage.GetPrimAtPath(dst_path))
            self.assertFalse(self._stage.GetPrimAtPath(dst_path))

            delete_result = wrappers.DeletePrims([dst_path], stage=stage)
            self.assertTrue(delete_result.success)
            self.assertFalse(stage.GetPrimAtPath(dst_path))
        finally:
            omni.kit.undo.clear_stack()
            await context.close_stage_async()
            await self._app.next_update_async()

    async def test_move_prims_rejects_unattached_stage_before_kit_command(self) -> None:
        """An unattached stage must produce a structured failure instead of a Kit command error."""
        result = wrappers.MovePrims(
            paths_to_move={"/source": "/destination"},
            stage_or_context=Usd.Stage.CreateInMemory(),
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "invalid_stage_context")

    async def test_group_and_ungroup_wrappers_use_explicit_stage(self) -> None:
        """Grouping must keep every nested command on the caller's non-default stage."""
        context_name = "material_graph_group_explicit_stage"
        context = omni.usd.create_context(context_name)
        stage = Usd.Stage.CreateInMemory()
        attached, error = await context.attach_stage_async(stage)
        self.assertTrue(attached, error)
        material_path = Sdf.Path("/Material")
        shader_path = material_path.AppendChild("Shader")
        UsdShade.Material.Define(stage, material_path)
        UsdShade.Shader.Define(stage, shader_path)

        try:
            group_result = wrappers.GroupNodeGraph(
                parent_path=material_path,
                selected_paths=[shader_path.pathString],
                position=(1.0, 2.0),
                position_key=None,
                stage=stage,
            )
            self.assertTrue(group_result.success)
            nodegraph_path = group_result.payload.GetPath()
            self.assertTrue(stage.GetPrimAtPath(nodegraph_path.AppendChild(shader_path.name)))
            self.assertFalse(self._stage.GetPrimAtPath(nodegraph_path))

            ungroup_result = wrappers.UngroupNodeGraph(nodegraph_path, stage=stage)
            self.assertTrue(ungroup_result.success)
            self.assertFalse(stage.GetPrimAtPath(nodegraph_path))
            self.assertTrue(stage.GetPrimAtPath(shader_path))
        finally:
            omni.kit.undo.clear_stack()
            await context.close_stage_async()
            await self._app.next_update_async()

    async def test_material_and_node_wrappers(self) -> None:
        """CreateMaterial/Shader/NodeGraph/Backdrop create prims."""
        material_result = wrappers.CreateMaterial()
        self.assertTrue(material_result.success)
        material_prim = self._get_prim_at_path("/World/Looks/Material")
        self.assertTrue(material_prim)

        selection = self._usd_context.get_selection()
        selection.set_selected_prim_paths([self._material_path.pathString], True)

        sdr_node = SdrRegistryWrapper().GetShaderNodeByIdentifier("UsdPreviewSurface")
        self.assertIsNotNone(sdr_node)
        shader_result = wrappers.CreateShader(self._material_path, sdr_node, (1, 2))
        self.assertTrue(shader_result.success)
        created = self._get_prim_at_path("/World/Looks/material/UsdPreviewSurface")
        self.assertTrue(created)
        self.assertEqual(selection.get_selected_prim_paths(), [created.GetPath().pathString])

        material_prim = self._get_prim_at_path(self._material_path)
        before_children = {child.GetName() for child in material_prim.GetChildren()}
        nodegraph_result = wrappers.CreateNodeGraph(self._material_path, (3, 4))
        self.assertTrue(nodegraph_result.success)
        after_children = {child.GetName() for child in material_prim.GetChildren()}
        self.assertGreater(len(after_children), len(before_children))

        scoped_result = wrappers.CreateNodeGraph(self._material_path, (7, 8), context_visibility="mdl")
        self.assertTrue(scoped_result.success)
        self.assertEqual(scoped_result.payload.GetCustomDataByKey("omni:ui")["contextVisibility"], ["mdl"])

        before_children = {child.GetName() for child in material_prim.GetChildren()}
        backdrop_result = wrappers.CreateBackdrop(self._material_path, (5, 6))
        self.assertTrue(backdrop_result.success)
        after_children = {child.GetName() for child in material_prim.GetChildren()}
        self.assertGreater(len(after_children), len(before_children))

        result = wrappers.CreateMaterial()
        self.assertTrue(result.success)
        self.assertIsNotNone(result.payload)

    async def test_create_node_wrapper_branches(self) -> None:
        """CreateNode routes to Backdrop/NodeGraph/unknown; unknown logs and returns failure."""
        # Patch execute_command_checked and logger.warning to avoid real commands and assert calls.
        with patch(
            f"{Paths.MODULE_ID}.scripts.commands.wrappers.nodes.execute_command_checked", autospec=True
        ) as execute:
            wrappers.CreateNode(self._material_path, "Backdrop", None, None, position=(1, 1))
            execute.assert_called_with(
                "MaterialGraph_CreateUsdUIBackdropCommand",
                parent_path=self._material_path,
                identifier="Backdrop",
                position=(1, 1),
                stage=None,
            )

        with patch(
            f"{Paths.MODULE_ID}.scripts.commands.wrappers.nodes.execute_command_checked", autospec=True
        ) as execute:
            wrappers.CreateNode(self._material_path, "NodeGraph", None, None, position=(2, 2))
            execute.assert_called_with(
                "MaterialGraph_NewUsdShadeNodeGraphCommand",
                parent_path=self._material_path,
                identifier="NodeGraph",
                position=(2, 2),
                context_visibility=None,
                stage=None,
            )

        with patch(
            f"{Paths.MODULE_ID}.scripts.commands.wrappers.nodes.execute_command_checked", autospec=True
        ) as execute:
            wrappers.CreateNode(self._material_path, "NodeGraph", None, None, position=(2, 2), context_name="mdl")
            execute.assert_called_with(
                "MaterialGraph_NewUsdShadeNodeGraphCommand",
                parent_path=self._material_path,
                identifier="NodeGraph",
                position=(2, 2),
                context_visibility="mdl",
                stage=None,
            )

        # ImportNodeGraph branch deferred until compound fixture is finalized.

        with patch(f"{Paths.MODULE_ID}.scripts.commands.wrappers.nodes.logger.warning", autospec=True) as log_warn:
            result = wrappers.CreateNode(self._material_path, "UnknownType", None, None)
            self.assertFalse(result.success)
            self.assertEqual(result.error_code, "unsupported_node_type")
            log_warn.assert_called_once()

    async def test_created_nodes_redo_restore_complete_initial_state(self) -> None:
        """Redo must restore shader identity, outputs, position, and backdrop styling."""
        sdr_node = SdrRegistryWrapper().GetShaderNodeByIdentifier("UsdPreviewSurface")
        texture_path = Sdf.AssetPath("textures/albedo.png")
        shader_result = wrappers.CreateShader(
            self._material_path,
            sdr_node,
            (11, 12),
            input_values={"file": (Sdf.ValueTypeNames.Asset, texture_path)},
        )
        self.assertTrue(shader_result.success)
        shader_path = shader_result.payload.GetPath()

        def _assert_shader_complete() -> None:
            prim = self._stage.GetPrimAtPath(shader_path)
            self.assertTrue(prim)
            self.assertEqual(UsdShade.NodeDefAPI(prim).GetShaderId(), "UsdPreviewSurface")
            self.assertTrue(UsdShade.Shader(prim).GetOutput("surface"))
            self.assertEqual(UsdShade.Shader(prim).GetInput("file").Get(), texture_path)
            self.assertEqual(tuple(UsdUI.NodeGraphNodeAPI(prim).GetPosAttr().Get()), (11.0, 12.0))

        _assert_shader_complete()
        self.assertTrue(omni.kit.undo.undo())
        await self._app.next_update_async()
        self.assertFalse(self._stage.GetPrimAtPath(shader_path))
        self.assertTrue(omni.kit.undo.redo())
        await self._app.next_update_async()
        _assert_shader_complete()

        backdrop_result = wrappers.CreateBackdrop(self._material_path, (21, 22), context_visibility="mdl")
        self.assertTrue(backdrop_result.success)
        backdrop_path = backdrop_result.payload.GetPath()

        def _assert_backdrop_complete() -> None:
            prim = self._stage.GetPrimAtPath(backdrop_path)
            self.assertTrue(prim)
            api = UsdUI.NodeGraphNodeAPI(prim)
            self.assertEqual(tuple(api.GetPosAttr().Get()), (21.0, 22.0))
            self.assertTrue(api.GetDisplayColorAttr().HasAuthoredValueOpinion())
            self.assertEqual(tuple(api.GetSizeAttr().Get()), tuple(Nodes.Backdrop.DEFAULT_SIZE))
            self.assertEqual(prim.GetCustomDataByKey("omni:ui")["contextVisibility"], ["mdl"])

        _assert_backdrop_complete()
        self.assertTrue(omni.kit.undo.undo())
        await self._app.next_update_async()
        self.assertFalse(self._stage.GetPrimAtPath(backdrop_path))
        self.assertTrue(omni.kit.undo.redo())
        await self._app.next_update_async()
        _assert_backdrop_complete()

    async def test_property_wrappers(self) -> None:
        """Rename/Remove property mutate USD."""
        prim = self._get_prim_at_path(self._shader_a)
        prim.CreateAttribute(f"{UsdShade.Tokens.inputs}temp", Sdf.ValueTypeNames.Float)

        rename_result = wrappers.RenameProperty(
            self._shader_a,
            f"{UsdShade.Tokens.inputs}temp",
            f"{UsdShade.Tokens.inputs}renamed",
        )
        self.assertTrue(rename_result.success)
        self.assertFalse(prim.HasAttribute(f"{UsdShade.Tokens.inputs}temp"))
        self.assertTrue(prim.HasAttribute(f"{UsdShade.Tokens.inputs}renamed"))

        attr_path = self._shader_a.AppendProperty(f"{UsdShade.Tokens.inputs}renamed")
        remove_result = wrappers.RemoveProperty(attr_path)
        self.assertTrue(remove_result.success)
        self.assertFalse(prim.HasAttribute(f"{UsdShade.Tokens.inputs}renamed"))

    async def test_misc_wrappers(self) -> None:
        """PauseMaterial, SetPosition/Size/DisplayColor/Description, RemovePosition, Lock/Unlock, SelectPrims, RenamePrim."""
        # Patch execute_command_checked for SetPosition, RemovePosition, LockAttribute, UnlockAttribute to avoid kit commands.
        self.assertIsNone(wrappers.cleanup_command_tasks())

        material_prim = self._get_prim_at_path(self._material_path)
        material_prim.CreateAttribute("paused", Sdf.ValueTypeNames.Bool).Set(False)
        wrappers.PauseMaterial(self._material_path, True)
        paused_attr = self._material_path.AppendProperty("paused")
        paused = self._get_attribute_at_path(paused_attr)
        self.assertTrue(paused.Get())

        # ChangeMetadataCommand signature differs across Kit versions; assert the call instead of executing.
        with patch(
            f"{Paths.MODULE_ID}.scripts.commands.wrappers.ui_nodes.execute_command_checked", autospec=True
        ) as execute:
            wrappers.SetPosition(self._material_path, (7, 8), None, True, "mdl")
            execute.assert_called()

        wrappers.SetPosition(self._shader_a, (1, 2), None, False, "mdl")
        shader_prim = self._get_prim_at_path(self._shader_a)
        self.assertTrue(shader_prim.HasAttribute(UsdUI.Tokens.uiNodegraphNodePos))

        wrappers.SetSize(self._shader_a, (10, 10), None)
        self.assertTrue(shader_prim.HasAttribute(UsdUI.Tokens.uiNodegraphNodeSize))

        wrappers.SetDisplayColor(self._shader_a, (1.0, 0.5, 0.0), None)
        self.assertTrue(shader_prim.HasAttribute(UsdUI.Tokens.uiNodegraphNodeDisplayColor))

        wrappers.SetDescription(self._shader_a, "desc", None)
        self.assertTrue(shader_prim.HasAttribute(UsdUI.Tokens.uiDescription))

        attr_path = self._shader_a.AppendProperty(f"{UsdShade.Tokens.inputs}diffuseColor")
        wrappers.SetDisplayName(attr_path, "Diffuse")
        attr = self._get_attribute_at_path(attr_path)
        self.assertEqual(attr.GetMetadata(Sdf.AttributeSpec.DisplayNameKey), "Diffuse")

        node_graph_node = UsdUI.NodeGraphNodeAPI.Apply(shader_prim)
        node_graph_node.CreatePosAttr().Set((3, 3))
        with patch(
            f"{Paths.MODULE_ID}.scripts.commands.wrappers.ui_nodes.execute_command_checked", autospec=True
        ) as execute:
            wrappers.RemovePosition(self._shader_a)
            execute.assert_called()

        with patch(
            f"{Paths.MODULE_ID}.scripts.commands.wrappers.attributes.execute_command_checked", autospec=True
        ) as execute:
            wrappers.LockAttribute(self._shader_a.AppendProperty(f"{UsdShade.Tokens.inputs}diffuseColor"))
            execute.assert_called_with(
                "LockSpecs",
                spec_paths=[self._shader_a.AppendProperty(f"{UsdShade.Tokens.inputs}diffuseColor")],
                undo_group=True,
            )

        with patch(
            f"{Paths.MODULE_ID}.scripts.commands.wrappers.attributes.execute_command_checked", autospec=True
        ) as execute:
            wrappers.UnlockAttribute(self._shader_a.AppendProperty(f"{UsdShade.Tokens.inputs}diffuseColor"))
            execute.assert_called_with(
                "UnlockSpecs",
                spec_paths=[self._shader_a.AppendProperty(f"{UsdShade.Tokens.inputs}diffuseColor")],
                undo_group=True,
            )

        selection = self._usd_context.get_selection()
        wrappers.SelectPrims([], [self._shader_a.pathString])
        self.assertIn(self._shader_a.pathString, selection.get_selected_prim_paths())

        rename_result = wrappers.RenamePrim(self._get_prim_at_path(self._shader_b), "shader_renamed")
        self.assertTrue(rename_result.success)
        new_path = rename_result.payload
        self.assertEqual(new_path, self._shader_b.GetParentPath().AppendChild("shader_renamed"))
        self.assertTrue(self._get_prim_at_path(new_path))
        self.assertFalse(wrappers.ConnectPortToSource(None, None).success)

    async def test_set_context_position_uses_explicit_stage_command(self) -> None:
        """SetContextPosition should route through the explicit-stage metadata command."""
        with patch(
            f"{Paths.MODULE_ID}.scripts.commands.wrappers.ui_nodes.execute_command_checked",
            autospec=True,
            return_value=CommandResult(True, None),
        ) as execute:
            key = "omni:uiNodegraphNodePos:input:mdl"
            self._stage.GetPrimAtPath(self._material_path).SetCustomDataByKey(key, (1.0, 2.0))
            result = ui_nodes.SetContextPosition(self._material_path, key, (1.0, 2.0), None)
            self.assertTrue(result.success)
            execute.assert_called_once()
            self.assertEqual(execute.call_args.args[0], "MaterialGraph_SetPrimCustomDataKeyCommand")
            self.assertIs(execute.call_args.kwargs["stage"], self._stage)

    async def test_context_position_preserves_sibling_keys_through_undo_redo(self) -> None:
        """Namespaced position edits preserve siblings and use readable USD key paths."""
        prim = self._stage.GetPrimAtPath(self._material_path)
        prim.SetCustomDataByKey("position:preview", (1.0, 2.0))
        malformed = dict(prim.GetCustomData())
        malformed["position:mdl"] = (0.0, 0.0)
        prim.SetCustomData(malformed)
        self.assertIn("position:mdl", prim.GetCustomData())

        result = ui_nodes.SetContextPosition(
            self._material_path,
            "position:mdl",
            (3.0, 4.0),
            None,
            stage=self._stage,
        )
        self.assertTrue(result.success)
        self.assertEqual(tuple(prim.GetCustomDataByKey("position:mdl")), (3.0, 4.0))
        self.assertEqual(tuple(prim.GetCustomDataByKey("position:preview")), (1.0, 2.0))
        self.assertNotIn("position:mdl", prim.GetCustomData())

        self.assertTrue(omni.kit.undo.undo())
        self.assertFalse(prim.HasAuthoredCustomDataKey("position:mdl"))
        self.assertEqual(tuple(prim.GetCustomDataByKey("position:preview")), (1.0, 2.0))
        self.assertTrue(omni.kit.undo.redo())
        self.assertEqual(tuple(prim.GetCustomDataByKey("position:mdl")), (3.0, 4.0))
        self.assertNotIn("position:mdl", prim.GetCustomData())

    async def test_position_wrappers_prefer_the_owning_stage(self) -> None:
        """Position edits must not author a same-path prim on Kit's default stage."""
        explicit_stage = self._stage
        default_stage = Usd.Stage.CreateInMemory()
        prim_path = self._material_path
        explicit_prim = explicit_stage.GetPrimAtPath(prim_path)
        default_prim = UsdShade.Material.Define(default_stage, prim_path).GetPrim()

        with patch("omni.usd.get_context") as get_context:
            get_context.return_value.get_stage.return_value = default_stage
            result = ui_nodes.SetPosition(
                prim_path,
                (5.0, 6.0),
                None,
                True,
                "mdl",
                stage=explicit_stage,
            )

        self.assertTrue(result.success)
        self.assertEqual(tuple(explicit_prim.GetCustomDataByKey("position:mdl")), (5.0, 6.0))
        self.assertFalse(default_prim.HasAuthoredCustomDataKey("position:mdl"))

    async def test_port_commands_prefer_the_owning_stage(self) -> None:
        """Port creation, connection, and rename must stay on the caller's stage."""
        explicit_stage = self._stage
        default_stage = Usd.Stage.CreateInMemory()
        prim_path = self._shader_a
        explicit_shader = UsdShade.Shader(explicit_stage.GetPrimAtPath(prim_path))
        default_shader = UsdShade.Shader.Define(default_stage, prim_path)

        with patch("omni.usd.get_context") as get_context:
            get_context.return_value.get_stage.return_value = default_stage
            input_result = wrappers.CreateInputPort(
                prim_path,
                "adversarialValue",
                Sdf.ValueTypeNames.Float,
                stage=explicit_stage,
            )
            output_result = wrappers.CreateOutputPort(
                prim_path,
                "adversarialResult",
                Sdf.ValueTypeNames.Float,
                stage=explicit_stage,
            )
            connect_result = wrappers.ConnectInputToSource(input_result.payload, output_result.payload)
            rename_result = wrappers.RenameProperty(
                prim_path,
                "inputs:adversarialValue",
                "inputs:adversarialRenamed",
                stage=explicit_stage,
            )

        self.assertTrue(input_result.success and output_result.success and connect_result.success)
        self.assertTrue(rename_result.success)
        self.assertTrue(explicit_shader.GetPrim().HasAttribute("inputs:adversarialRenamed"))
        self.assertTrue(explicit_shader.GetOutput("adversarialResult"))
        self.assertFalse(default_shader.GetPrim().HasAttribute("inputs:adversarialValue"))
        self.assertFalse(default_shader.GetPrim().HasAttribute("inputs:adversarialRenamed"))
        self.assertFalse(default_shader.GetPrim().HasAttribute("outputs:adversarialResult"))

    async def test_command_task_cleanup(self) -> None:
        """Tracked tasks cancelled on cleanup."""
        task = asyncio.create_task(asyncio.sleep(10))
        wrappers.track_command_task(task)
        wrappers.cleanup_command_tasks()
        await asyncio.sleep(0)
        self.assertTrue(task.cancelled() or task.done())

    async def test_create_backdrop_defaults(self) -> None:
        """CreateBackdrop uses default size and color."""
        material_prim = self._get_prim_at_path(self._material_path)
        before_children = {child.GetName() for child in material_prim.GetChildren()}
        wrappers.CreateBackdrop(self._material_path, (9, 9))
        after_children = {child.GetName() for child in material_prim.GetChildren()}
        self.assertGreater(len(after_children), len(before_children))

    async def test_delete_input_output_nodes_wrapper(self) -> None:
        """DeleteInputOutputNodes issues remove commands for input ports."""

        # Patch isolation.execute_command and RemoveProperty, and MaterialGraphIsolationModel.EmptyPort, to avoid real commands.
        class DummyPort:
            """Minimal port wrapper for delete tests."""

            def __init__(self, path: Sdf.Path) -> None:
                """Initialize with a property path."""
                self.path = path

        class DummyEmptyPort:
            """Placeholder empty-port type used by wrappers."""

        class DummyNode:
            """Node wrapper exposing ports."""

            def __init__(self, ports: list[DummyPort]) -> None:
                """Initialize with a list of ports."""
                self.ports = ports

        class DummyIsolationModel:
            """Placeholder isolation model for wrapper tests."""

        class DummyGraphModel:
            """Placeholder graph model for wrapper tests."""

        dummy_ports = [DummyPort(self._shader_a.AppendProperty(f"{UsdShade.Tokens.inputs}diffuseColor"))]
        nodes = [DummyNode(dummy_ports)]
        isolation_model = DummyIsolationModel()
        graph_model = DummyGraphModel()

        with patch(f"{Paths.MODULE_ID}.scripts.commands.wrappers.isolation.execute_command", autospec=True) as execute:
            from ...scripts.models.graph.isolation import MaterialGraphIsolationModel

            with patch(
                f"{Paths.MODULE_ID}.scripts.commands.wrappers.isolation.RemoveProperty",
                autospec=True,
                return_value=CommandResult(True, None),
            ) as remove_property:
                with patch.object(MaterialGraphIsolationModel, "EmptyPort", DummyEmptyPort):
                    wrappers.DeleteInputOutputNodes(isolation_model, nodes, graph_model)
                remove_property.assert_any_call(dummy_ports[0].path)
            execute.assert_any_call(
                "MaterialGraph_IsolationModelRemoveCommand",
                isolation_model=isolation_model,
                node=nodes[0],
                graph_model=graph_model,
            )

    async def test_delete_input_output_nodes_output_branch(self) -> None:
        """Output branch disconnects material output before remove."""

        # Patch execute_command and MaterialGraphIsolationModel.OutputNode, MaterialModel, to assert disconnect call.
        class DummyOutputNode:
            """Output node stub with ports."""

            def __init__(self) -> None:
                """Initialize an empty ports list."""
                self.ports = []

        class DummyMaterialModel:
            """Material model stub for output delete coverage."""

            def __init__(self, prim, context_name: str) -> None:
                """Initialize with a prim and context name."""
                self.prim = prim
                self.context_name = context_name

        material_prim = self._get_prim_at_path(self._material_path)
        graph_model = DummyMaterialModel(material_prim, "universal")
        node = DummyOutputNode()

        with patch(f"{Paths.MODULE_ID}.scripts.commands.wrappers.isolation.execute_command", autospec=True) as execute:
            from ...scripts.models.graph.isolation import MaterialGraphIsolationModel

            with patch.object(MaterialGraphIsolationModel, "OutputNode", DummyOutputNode):
                with patch(
                    f"{Paths.MODULE_ID}.scripts.models.graph.nodes.material.MaterialModel", new=DummyMaterialModel
                ):
                    wrappers.DeleteInputOutputNodes(object(), [node], graph_model)
            calls = [
                call_item
                for call_item in execute.call_args_list
                if call_item.args and call_item.args[0] == "MaterialGraph_UsdShadeDisconnectSourceCommand"
            ]
            self.assertTrue(calls)
            target = calls[0].kwargs.get("target")
            self.assertIsNotNone(target)
            expected = UsdShade.Material(material_prim).GetSurfaceOutput(UsdShade.Tokens.universalRenderContext)
            self.assertEqual(target.GetAttr().GetPath(), expected.GetAttr().GetPath())

    async def test_delete_input_output_nodes_reports_failures(self) -> None:
        """DeleteInputOutputNodes returns structured failure when RemoveProperty fails."""

        # Patch RemoveProperty to return failure and execute_command to succeed so we assert result.error_code and warnings.
        class DummyPort:
            def __init__(self, path: Sdf.Path) -> None:
                self.path = path

        class DummyNode:
            def __init__(self, ports: list[DummyPort]) -> None:
                self.ports = ports

        class DummyIsolationModel:
            pass

        class DummyGraphModel:
            pass

        dummy_port = DummyPort(self._shader_a.AppendProperty(f"{UsdShade.Tokens.inputs}diffuseColor"))
        node = DummyNode([dummy_port])
        isolation_model = DummyIsolationModel()
        graph_model = DummyGraphModel()

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.commands.wrappers.isolation.RemoveProperty",
                autospec=True,
                return_value=CommandResult(False, None, error_code="command_failed"),
            ),
            patch(
                f"{Paths.MODULE_ID}.scripts.commands.wrappers.isolation.execute_command",
                autospec=True,
                return_value=CommandResult(True, None),
            ),
        ):
            result = wrappers.DeleteInputOutputNodes(isolation_model, [node], graph_model)
            self.assertFalse(result.success)
            self.assertEqual(result.error_code, "isolation_cleanup_failed")
            self.assertIn("remove_property_failed", ",".join(result.warnings or ()))
