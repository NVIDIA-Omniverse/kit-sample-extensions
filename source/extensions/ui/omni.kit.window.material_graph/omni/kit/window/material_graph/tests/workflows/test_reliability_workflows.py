# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Stateful workflows spanning USD, graph models, snapshots, and the native canvas."""

import importlib
import logging
import unittest

import omni.kit.undo
import omni.ui
from omni.kit.widget.graph import GraphModel
from pxr import Gf, Sdf, Usd, UsdShade

from ...scripts.commands.wrappers.ports import ConnectInputToSource, DisconnectSourcePort
from ...scripts.commands.wrappers.prims import DeletePrims
from ...scripts.commands.wrappers.ui_nodes import CreateNodeGraph
from ...scripts.config.logging import logger
from ...scripts.context_manager.context_manager import ContextManager
from ...scripts.models.graph.isolation import MaterialGraphIsolationModel
from ...scripts.ui.graph_canvas_view import GraphCanvasView
from ...scripts.validation.registry import get_active_validator, set_active_validator
from ..context.base import ContextManagerTestBase
from ..ui_base import MaterialGraphUiTestBase

try:
    _graph_canvas_native = importlib.import_module("omni.kit.window.material_graph._graphCanvas")
except ImportError:  # pragma: no cover - the extension test runner normally supplies the binding
    _graph_canvas_native = None


class _OpenPbrWorkflowMixin:
    """Build and inspect a deterministic workflow on the representative MaterialX asset."""

    _MATERIAL_PATH = Sdf.Path("/World/Looks/Material")
    _OPEN_PBR_PATH = _MATERIAL_PATH.AppendChild("ND_open_pbr_surface_surfaceshader")
    _GROUP_NAME = "Workflow"

    def _author_workflow_ports(self) -> None:
        material = UsdShade.Material(self._stage.GetPrimAtPath(self._MATERIAL_PATH))
        shader = UsdShade.Shader(self._stage.GetPrimAtPath(self._OPEN_PBR_PATH))
        self.assertTrue(material)
        self.assertTrue(shader)

        self._source_a = material.CreateInput("workflowSourceA", Sdf.ValueTypeNames.Color3f)
        self._source_b = material.CreateInput("workflowSourceB", Sdf.ValueTypeNames.Color3f)
        self._target = shader.CreateInput("workflowEmission", Sdf.ValueTypeNames.Color3f)
        self.assertTrue(self._target.GetAttr().SetMetadata(Sdf.AttributeSpec.DisplayGroupKey, self._GROUP_NAME))

    def _load_mtlx_model(self, manager: ContextManager):
        self.assertTrue(manager.load(self._MATERIAL_PATH))
        self.assertTrue(manager.add_context("mtlx"))
        handle = manager.get_context("mtlx")
        self.assertTrue(handle.is_valid, handle.error)
        model = handle.context.model
        model.active = True
        model.sync()
        target_model = model.get_item_model(self._OPEN_PBR_PATH)
        self.assertIsNotNone(target_model)
        group = target_model._inputs._children.get(self._GROUP_NAME)
        self.assertIsNotNone(group, f"missing '{self._GROUP_NAME}' input group")
        return model, target_model, group

    @staticmethod
    def _find_snapshot_node(snapshot: list, prim_path: Sdf.Path) -> tuple[int, dict]:
        for index, node in enumerate(snapshot):
            prim = getattr(node.get("node"), "prim", None)
            if prim and prim.GetPath() == prim_path:
                return index, node
        raise AssertionError(f"snapshot node missing: {prim_path}")

    def _build_state(self, model, group) -> dict:
        isolation = MaterialGraphIsolationModel(model, model)
        try:
            snapshot = isolation.export_snapshot(True)
            node_index, node = self._find_snapshot_node(snapshot, self._OPEN_PBR_PATH)
            group_port = next((port for port in node["ports"] if port.get("port") is group), None)
            self.assertIsNotNone(group_port, "workflow group was not exported")
            native = _graph_canvas_native.native_build_from_snapshot(snapshot)
            self.assertEqual(len(native.scene.nodes), len(snapshot))
            self.assertEqual(len(native.model_nodes), len(snapshot))
            self.assertEqual(len(native.node_heights), len(snapshot))
            self.assertEqual(len(native.visible_port_counts), len(snapshot))

            node_ids = {id(entry["node"]) for entry in snapshot}
            self.assertEqual(len(node_ids), len(snapshot), "snapshot contains duplicate model nodes")
            exported_ports = {port["port"] for entry in snapshot for port in entry["ports"] if port.get("port")}
            for entry in snapshot:
                for port in entry["ports"]:
                    for source in port.get("inputs") or []:
                        self.assertIn(source, exported_ports, "snapshot contains a stale connection source")

            return {
                "collapsed": group_port.get("exp", 0) != 0,
                "connections": tuple(self._target.GetAttr().GetConnections()),
                "height": native.node_heights[node_index],
                "native_connections": len(native.scene.connections),
                "visible_ports": native.visible_port_counts[node_index],
            }
        finally:
            isolation.destroy()

    async def _settle_model(self, model, target_model) -> None:
        """Let USD notices/deferred callbacks run, then synchronize runtime connection state."""

        await self._app.next_update_async()
        await self._app.next_update_async()
        target_model.sync_ports()
        model.sync_ports()


class _ExtensionDiagnosticHandler(logging.Handler):
    """Collect extension warnings/errors emitted after the smoke workflow begins."""

    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class TestRealUsdReliabilityWorkflows(_OpenPbrWorkflowMixin, ContextManagerTestBase):
    """Exercise connected user actions through every non-rendering production layer."""

    async def setUp(self) -> None:
        await super().setUp()
        omni.kit.undo.clear_stack()

    async def tearDown(self) -> None:
        omni.kit.undo.clear_stack()
        await super().tearDown()

    @unittest.skipIf(_graph_canvas_native is None, "native _graphCanvas not available")
    async def test_openpbr_connect_rewire_disconnect_undo_redo_invariants(self) -> None:
        """A representative graph stays coherent through a stateful connection workflow."""

        await self._load_scene("material.usda")
        self._author_workflow_ports()
        model, target_model, group = self._load_mtlx_model(self._manager)
        group.expansion_state = GraphModel.ExpansionState.CLOSED

        disconnected = self._build_state(model, group)
        self.assertTrue(disconnected["collapsed"])
        self.assertEqual(disconnected["connections"], ())

        self.assertTrue(ConnectInputToSource(self._target, self._source_a).success)
        await self._settle_model(model, target_model)
        connected_a = self._build_state(model, group)
        self.assertFalse(connected_a["collapsed"])
        self.assertEqual(connected_a["connections"], (self._source_a.GetAttr().GetPath(),))
        self.assertGreater(connected_a["height"], disconnected["height"])
        self.assertGreater(connected_a["visible_ports"], disconnected["visible_ports"])
        self.assertEqual(connected_a["native_connections"], disconnected["native_connections"] + 1)

        # Rewiring must replace, not append to, the source and must leave no stale native edge.
        self.assertTrue(ConnectInputToSource(self._target, self._source_b).success)
        await self._settle_model(model, target_model)
        connected_b = self._build_state(model, group)
        self.assertEqual(connected_b["connections"], (self._source_b.GetAttr().GetPath(),))
        self.assertEqual(connected_b["native_connections"], connected_a["native_connections"])
        self.assertFalse(connected_b["collapsed"])

        # A close request while connected is remembered, but the effective UI state stays open.
        group.expansion_state = GraphModel.ExpansionState.CLOSED
        self.assertEqual(group.expansion_state, GraphModel.ExpansionState.OPEN)
        self.assertTrue(DisconnectSourcePort(self._target).success)
        await self._settle_model(model, target_model)
        disconnected_again = self._build_state(model, group)
        self.assertTrue(self._target.GetAttr().HasAuthoredConnections())
        self.assertEqual(disconnected_again["connections"], ())
        self.assertTrue(disconnected_again["collapsed"])
        self.assertEqual(disconnected_again["height"], disconnected["height"])
        self.assertEqual(disconnected_again["native_connections"], disconnected["native_connections"])

        self.assertTrue(omni.kit.undo.undo())
        await self._settle_model(model, target_model)
        undo_disconnect = self._build_state(model, group)
        self.assertEqual(undo_disconnect["connections"], (self._source_b.GetAttr().GetPath(),))
        self.assertFalse(undo_disconnect["collapsed"])

        self.assertTrue(omni.kit.undo.undo())
        await self._settle_model(model, target_model)
        undo_rewire = self._build_state(model, group)
        self.assertEqual(undo_rewire["connections"], (self._source_a.GetAttr().GetPath(),))
        self.assertEqual(undo_rewire["native_connections"], connected_a["native_connections"])

        self.assertTrue(omni.kit.undo.redo())
        await self._settle_model(model, target_model)
        self.assertEqual(self._build_state(model, group)["connections"], (self._source_b.GetAttr().GetPath(),))
        self.assertTrue(omni.kit.undo.redo())
        await self._settle_model(model, target_model)
        redo_disconnect = self._build_state(model, group)
        self.assertEqual(redo_disconnect["connections"], ())
        self.assertTrue(redo_disconnect["collapsed"])

    @unittest.skipIf(_graph_canvas_native is None, "native _graphCanvas not available")
    async def test_create_delete_undo_redo_rebuild_has_no_stale_nodes(self) -> None:
        """Create/delete commands and their history agree with the model and native snapshot."""

        await self._load_scene("material.usda")
        self.assertTrue(self._manager.load(self._MATERIAL_PATH))
        self.assertTrue(self._manager.add_context("mtlx"))
        model = self._manager.get_context("mtlx").context.model
        model.active = True

        created = CreateNodeGraph(self._MATERIAL_PATH, (37.0, 91.0), context_visibility="mtlx")
        self.assertTrue(created.success)
        created_path = created.payload.GetPath()

        async def _assert_presence(expected: bool) -> None:
            await self._app.next_update_async()
            model.sync()
            isolation = MaterialGraphIsolationModel(model, model)
            try:
                snapshot = isolation.export_snapshot(True)
                native = _graph_canvas_native.native_build_from_snapshot(snapshot)
                usd_present = bool(self._stage.GetPrimAtPath(created_path))
                model_present = model.get_item_model(created_path) is not None
                snapshot_paths = {
                    entry["node"].prim.GetPath() for entry in snapshot if getattr(entry["node"], "prim", None)
                }
                self.assertEqual(usd_present, expected)
                self.assertEqual(model_present, expected)
                self.assertEqual(created_path in snapshot_paths, expected)
                self.assertEqual(len(native.scene.nodes), len(snapshot))
            finally:
                isolation.destroy()

        await _assert_presence(True)
        self.assertTrue(DeletePrims([created_path], stage=self._stage).success)
        await _assert_presence(False)
        self.assertTrue(omni.kit.undo.undo())
        await _assert_presence(True)
        self.assertTrue(omni.kit.undo.redo())
        await _assert_presence(False)

    async def test_composed_connection_lists_value_blocks_and_mixed_types(self) -> None:
        """Real USD composition distinguishes blocks, list edits, and unresolved paths."""

        root = self._stage.GetRootLayer()
        weak = Sdf.Layer.CreateAnonymous("material_graph_workflow_weak.usda")
        root.subLayerPaths.append(weak.identifier)
        target_path = Sdf.Path("/World/Looks/Composed/Target")
        source_a_path = Sdf.Path("/World/Looks/Composed/SourceA")
        source_b_path = Sdf.Path("/World/Looks/Composed/SourceB")

        with Usd.EditContext(self._stage, weak):
            source_a = UsdShade.Shader.Define(self._stage, source_a_path)
            source_b = UsdShade.Shader.Define(self._stage, source_b_path)
            target = UsdShade.Shader.Define(self._stage, target_path)
            source_a_output = source_a.CreateOutput("out", Sdf.ValueTypeNames.Float)
            source_b_output = source_b.CreateOutput("out", Sdf.ValueTypeNames.Float)
            target_input = target.CreateInput("value", Sdf.ValueTypeNames.Float)
            self.assertTrue(target_input.ConnectToSource(source_a_output))

            mixed = (
                ("scalar", Sdf.ValueTypeNames.Float, 1.25),
                ("float2", Sdf.ValueTypeNames.Float2, Gf.Vec2f(1.0, 2.0)),
                ("double2", Sdf.ValueTypeNames.Double2, Gf.Vec2d(3.0, 4.0)),
                ("token", Sdf.ValueTypeNames.Token, "weakToken"),
                ("asset", Sdf.ValueTypeNames.Asset, Sdf.AssetPath("textures/weak.png")),
            )
            mixed_attrs = []
            for name, value_type, value in mixed:
                attr = target.GetPrim().CreateAttribute(f"inputs:{name}", value_type)
                self.assertTrue(attr.Set(value))
                mixed_attrs.append((attr, value))

        target_input = UsdShade.Input(self._stage.GetAttributeAtPath(target_input.GetAttr().GetPath()))
        source_a_output = UsdShade.Output(self._stage.GetAttributeAtPath(source_a_output.GetAttr().GetPath()))
        source_b_output = UsdShade.Output(self._stage.GetAttributeAtPath(source_b_output.GetAttr().GetPath()))
        self.assertEqual(target_input.GetAttr().GetConnections(), [source_a_output.GetAttr().GetPath()])

        with Usd.EditContext(self._stage, root):
            self.assertTrue(target_input.DisconnectSource())
            self.assertTrue(target_input.GetAttr().HasAuthoredConnections())
            self.assertEqual(target_input.GetAttr().GetConnections(), [])
            target_input.GetAttr().ClearConnections()
            self.assertEqual(target_input.GetAttr().GetConnections(), [source_a_output.GetAttr().GetPath()])

            self.assertTrue(target_input.GetAttr().AddConnection(source_b_output.GetAttr().GetPath()))
            self.assertEqual(
                set(target_input.GetAttr().GetConnections()),
                {source_a_output.GetAttr().GetPath(), source_b_output.GetAttr().GetPath()},
            )
            self.assertTrue(target_input.GetAttr().RemoveConnection(source_a_output.GetAttr().GetPath()))
            self.assertEqual(target_input.GetAttr().GetConnections(), [source_b_output.GetAttr().GetPath()])

            missing_path = Sdf.Path("/World/Looks/Composed/Missing.outputs:out")
            self.assertTrue(target_input.GetAttr().AddConnection(missing_path))
            self.assertIn(missing_path, target_input.GetAttr().GetConnections())

            for attr, weak_value in mixed_attrs:
                composed = self._stage.GetAttributeAtPath(attr.GetPath())
                self.assertEqual(composed.Get(), weak_value)
                composed.Block()
                self.assertIsNone(composed.Get())
                composed.Clear()
                self.assertEqual(composed.Get(), weak_value)


class TestRenderedReliabilityWorkflow(_OpenPbrWorkflowMixin, MaterialGraphUiTestBase):
    """Exercise the real C++ canvas boundary after Kit processes deferred work."""

    async def setUp(self) -> None:
        await super().setUp()
        omni.kit.undo.clear_stack()
        self._diagnostics = _ExtensionDiagnosticHandler()
        logger.addHandler(self._diagnostics)

    async def tearDown(self) -> None:
        logger.removeHandler(self._diagnostics)
        self._diagnostics = None
        omni.kit.undo.clear_stack()
        await super().tearDown()

    @unittest.skipIf(_graph_canvas_native is None, "native _graphCanvas not available")
    async def test_native_canvas_rebuilds_group_geometry_after_disconnect(self) -> None:
        """Rendered geometry and hit regions follow effective group state after frames."""

        await self._load_scene("material.usda")
        self._author_workflow_ports()
        previous_validator = get_active_validator(self._usd_context)
        manager = ContextManager(self._usd_context)
        view = None
        isolation = None
        window = None
        try:
            model, target_model, group = self._load_mtlx_model(manager)
            group.expansion_state = GraphModel.ExpansionState.CLOSED
            isolation = MaterialGraphIsolationModel(model, model)
            window = await self.create_test_window(width=900, height=520, block_devices=False)
            with window.frame:
                view = GraphCanvasView(
                    model=isolation,
                    port_grouping=True,
                    width=omni.ui.Percent(100),
                    height=omni.ui.Percent(100),
                )
            await self.wait_n_updates(4)
            view._rebuild_core()
            await self.wait_n_updates(2)
            self.assertIsNotNone(view._canvas_widget)
            self.assertIsNotNone(view._last_scene)
            self.assertEqual(view._canvas_widget.visible_node_count, len(view._scene_model_nodes))

            self.assertTrue(ConnectInputToSource(self._target, self._source_a).success)
            await self.wait_n_updates(2)
            target_model.sync_ports()
            isolation.clear_caches()
            isolation._item_changed(None)
            await self.wait_n_updates(3)
            connected_index = view._scene_model_nodes.index(target_model)
            connected_height = view._scene_heights[connected_index]
            connected_count = len(view._last_scene.connections)

            group_port_index = next(
                index
                for index in range(len(view._scene_port_sides[connected_index]))
                if view._get_model_port(connected_index, index) is group
            )
            hit_x = view._scene_pos_x[connected_index]
            hit_y = (
                view._scene_pos_y[connected_index]
                + view._scene_port_start_y[connected_index]
                + group_port_index * view._PORT_H
                + view._PORT_H * 0.5
            )
            self.assertEqual(view._find_group_icon_at(hit_x, hit_y), (connected_index, group_port_index))
            view._toggle_group_expansion(connected_index, group_port_index)
            self.assertEqual(group.expansion_state, GraphModel.ExpansionState.OPEN)

            self.assertTrue(DisconnectSourcePort(self._target).success)
            await self.wait_n_updates(2)
            target_model.sync_ports()
            isolation.clear_caches()
            isolation._item_changed(None)
            await self.wait_n_updates(3)
            disconnected_index = view._scene_model_nodes.index(target_model)
            self.assertEqual(group.expansion_state, GraphModel.ExpansionState.CLOSED)
            self.assertLess(view._scene_heights[disconnected_index], connected_height)
            self.assertEqual(len(view._last_scene.connections), connected_count - 1)
            self.assertEqual(view._canvas_widget.visible_node_count, len(view._scene_model_nodes))
            rendered_diagnostics = [
                f"{record.levelname}: {record.getMessage()}" for record in self._diagnostics.records
            ]
            self.assertEqual(rendered_diagnostics, [])
        finally:
            if view:
                view.destroy()
            if isolation:
                isolation.destroy()
            manager.destroy()
            if previous_validator:
                set_active_validator(self._usd_context, previous_validator)
            if window:
                window.visible = False
                await self.finalize_test_no_image()
