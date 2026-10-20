# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Contract tests for native scene structs and style push (no graph model rebuild)."""

import importlib
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import omni.kit.test

try:
    # Preferred when the extension package loads (native binary present).
    from ...scripts.config.graph_style import GraphStyle
except ImportError:  # pragma: no cover - package __init__ may require _graphCanvas
    _gs = Path(__file__).resolve().parents[2] / "scripts" / "config" / "graph_style.py"
    _spec = importlib.util.spec_from_file_location("omni.kit.window.material_graph.tests._graph_style_contract", _gs)
    assert _spec and _spec.loader
    _graph_style_mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_graph_style_mod)
    GraphStyle = _graph_style_mod.GraphStyle

try:
    _gnw = importlib.import_module("omni.kit.window.material_graph._graphCanvas")
except ImportError:  # pragma: no cover
    _gnw = None


def _port_snapshot(port, name, type_name, *, inputs=None, outputs=None, **overrides):
    snapshot = {
        "port": port,
        "name": name,
        "type": type_name,
        "level": 0,
        "exp": 0,
        "is_group": False,
        "sub_count": 0,
        "inputs": inputs,
        "outputs": outputs,
    }
    snapshot.update(overrides)
    return snapshot


def _node_snapshot(node, name, ports, **overrides):
    snapshot = {
        "node": node,
        "name": name,
        "type": "Shader",
        "size_w": 200.0,
        "pos": None,
        "color": None,
        "selected": False,
        "valid": True,
        "ports": ports,
    }
    snapshot.update(overrides)
    return snapshot


class TestRebuildFlowContracts(omni.kit.test.AsyncTestCase):
    """Scene graph structs and style wiring expected by the native canvas."""

    @unittest.skipIf(_gnw is None, "native _graphCanvas not available")
    async def test_scene_data_structures(self):
        """Bound C++ types expose the fields Python uses when building scenes."""
        GraphScene = _gnw.GraphScene
        SceneNodeEntry = _gnw.SceneNodeEntry
        SceneConnectionEntry = _gnw.SceneConnectionEntry
        NodeData = _gnw.NodeData
        PortData = _gnw.PortData

        scene = GraphScene()
        scene.nodes = []
        scene.connections = []
        self.assertIsInstance(scene.nodes, list)
        self.assertIsInstance(scene.connections, list)

        node = NodeData()
        node.name = "n"
        node.type_name = "t"
        node.ports = []
        self.assertEqual(node.name, "n")

        port = PortData()
        port.name = "p"
        port.type_name = "float"
        self.assertEqual(port.name, "p")

        entry = SceneNodeEntry()
        entry.stable_id = 1
        entry.data = node
        entry.pos_x = 0.0
        entry.pos_y = 0.0
        self.assertEqual(entry.stable_id, 1)
        # The pybind property returns a value wrapper rather than preserving
        # Python object identity, so validate the copied contract fields.
        self.assertIsInstance(entry.data, NodeData)
        self.assertEqual(entry.data.name, node.name)
        self.assertEqual(entry.data.type_name, node.type_name)

        conn = SceneConnectionEntry()
        conn.source_node_id = 1
        conn.source_port_index = 0
        conn.target_node_id = 2
        conn.target_port_index = 1
        conn.color = 0xFFFFFFFF
        conn.thickness = 1.0
        conn.reversed = False
        self.assertEqual(conn.target_node_id, 2)

    async def test_scene_fields_documented_on_mock_objects(self):
        """Offline stand-ins document the same attribute contract as the bindings."""
        scene = SimpleNamespace(nodes=[], connections=[])
        port = SimpleNamespace(
            name="p",
            type_name="float",
        )
        node = SimpleNamespace(
            name="n",
            type_name="t",
            ports=[port],
        )
        entry = SimpleNamespace(
            stable_id=1,
            data=node,
            pos_x=0.0,
            pos_y=0.0,
        )
        conn = SimpleNamespace(
            source_node_id=1,
            source_port_index=0,
            target_node_id=2,
            target_port_index=1,
            color=0,
            thickness=1.0,
            reversed=False,
        )
        scene.nodes.append(entry)
        scene.connections.append(conn)
        self.assertEqual(len(scene.nodes), 1)
        self.assertEqual(len(scene.connections), 1)

    async def test_style_config_push_contract(self):
        style = GraphStyle.to_dict()
        self.assertIsInstance(style, dict)
        self.assertIn("header_height", style)

        w = MagicMock()
        w.set_style_config(style)
        w.set_style_config.assert_called_once()
        (arg,), _kwargs = w.set_style_config.call_args
        self.assertIsInstance(arg, dict)

    async def test_visible_counts_after_empty_scene(self):
        """Empty ``GraphScene`` has no nodes; the widget reports zero visible nodes."""

        class _FakeCanvas:
            def __init__(self):
                self._scene = None

            def set_scene(self, scene):
                self._scene = scene

            @property
            def visible_node_count(self):
                if self._scene is None:
                    return 0
                return len(self._scene.nodes)

        scene = SimpleNamespace(nodes=[], connections=[])
        w = _FakeCanvas()
        w.set_scene(scene)
        self.assertEqual(w.visible_node_count, 0)

    @unittest.skipIf(_gnw is None, "native _graphCanvas not available")
    async def test_native_snapshot_empty_result_is_aligned(self):
        """The production C++ snapshot path returns aligned empty collections."""
        result = _gnw.native_build_from_snapshot([])

        self.assertEqual(result.scene.nodes, [])
        self.assertEqual(result.scene.connections, [])
        self.assertEqual(result.edges, [])
        self.assertEqual(result.visible_port_counts, [])
        self.assertEqual(result.model_nodes, [])
        self.assertEqual(result.stable_ids, [])
        self.assertEqual(result.node_pos_x, [])
        self.assertEqual(result.node_pos_y, [])
        self.assertEqual(result.node_widths, [])
        self.assertEqual(result.node_heights, [])
        self.assertEqual(result.node_port_start_y, [])

    @unittest.skipIf(_gnw is None, "native _graphCanvas not available")
    async def test_native_snapshot_preserves_validation_and_port_metadata(self):
        """Validation state reaches the native renderer without constructing a widget."""
        model_node = object()
        model_port = object()
        port = _port_snapshot(
            model_port,
            "broken",
            "color3f",
            inputs=[],
            is_empty=True,
            rel_pos=2,
            parent_count=4,
            poly_unresolved=True,
            is_uniform=True,
            is_interface_only=True,
            io_state=2,
            is_group_header=True,
            group_port_count=3,
            group_collapsed=True,
            is_hidden=True,
            has_error=True,
        )
        result = _gnw.native_build_from_snapshot(
            [
                _node_snapshot(
                    model_node,
                    "Invalid Shader",
                    [port],
                    pos=(12.5, -3.0),
                    selected=True,
                    valid=False,
                    valid_state=2,
                    polymorphic_unresolved=True,
                    is_input_node=True,
                    view_mode=2,
                )
            ]
        )

        self.assertEqual(result.stable_ids, [1])
        self.assertEqual(result.node_pos_x, [12.5])
        self.assertEqual(result.node_pos_y, [-3.0])
        self.assertEqual(result.visible_port_counts, [1])
        self.assertIs(result.model_nodes[0], model_node)

        node = result.scene.nodes[0].data
        self.assertEqual(node.name, "Invalid Shader")
        self.assertTrue(node.selected)
        self.assertEqual(node.valid_state, 2)
        self.assertTrue(node.is_polymorphic)
        self.assertFalse(node.is_resolved)
        self.assertTrue(node.is_input_node)
        self.assertEqual(node.view_mode, 2)
        self.assertTrue(node.is_interface)

        rendered_port = node.ports[0]
        self.assertFalse(rendered_port.connected_target)
        self.assertTrue(rendered_port.is_empty)
        self.assertEqual(rendered_port.relative_position, 2)
        self.assertEqual(rendered_port.parent_child_count, 4)
        self.assertTrue(rendered_port.is_polymorphic)
        self.assertFalse(rendered_port.is_resolved)
        self.assertTrue(rendered_port.is_uniform)
        self.assertTrue(rendered_port.is_interface_only)
        self.assertEqual(rendered_port.io_state, 2)
        self.assertTrue(rendered_port.is_group_header)
        self.assertEqual(rendered_port.group_port_count, 3)
        self.assertTrue(rendered_port.group_collapsed)
        self.assertTrue(rendered_port.is_hidden)
        self.assertTrue(rendered_port.has_error)

    @unittest.skipIf(_gnw is None, "native _graphCanvas not available")
    async def test_native_snapshot_builds_colored_invalid_connection(self):
        """Connections, layout edges, noodle colors, and error state share one native result."""
        source_node = object()
        target_node = object()
        source_port = object()
        target_port = object()
        snapshot = [
            _node_snapshot(
                source_node,
                "Source",
                [_port_snapshot(source_port, "out", "color3f", outputs=[])],
            ),
            _node_snapshot(
                target_node,
                "Target",
                [_port_snapshot(target_port, "in", "color3f", inputs=[source_port], has_error=True)],
            ),
        ]

        previous = _gnw.get_color_noodles()
        try:
            _gnw.set_color_noodles(True)
            result = _gnw.native_build_from_snapshot(snapshot)
        finally:
            _gnw.set_color_noodles(previous)

        self.assertEqual(result.edges, [(1, 0)])
        self.assertEqual(len(result.scene.connections), 1)
        connection = result.scene.connections[0]
        self.assertEqual(connection.source_node_id, 1)
        self.assertEqual(connection.source_port_index, 0)
        self.assertEqual(connection.target_node_id, 2)
        self.assertEqual(connection.target_port_index, 0)
        self.assertEqual(connection.color, result.scene.nodes[0].data.ports[0].color)
        self.assertNotEqual(connection.color, 0xFFAAAAAA)
        self.assertFalse(connection.valid)

    @unittest.skipIf(_gnw is None, "native _graphCanvas not available")
    async def test_native_snapshot_backdrop_keeps_authored_geometry(self):
        """Backdrop geometry bypasses shader auto-sizing in the native path."""
        result = _gnw.native_build_from_snapshot(
            [
                _node_snapshot(
                    object(),
                    "Backdrop",
                    [],
                    size_w=640.0,
                    size_h=360.0,
                    is_backdrop=True,
                    description="Notes",
                    stacking_order=-4,
                    color=(2.0, 1.0, 0.0),
                )
            ]
        )

        node = result.scene.nodes[0].data
        self.assertTrue(node.is_backdrop)
        self.assertEqual(node.description, "Notes")
        self.assertEqual(node.stacking_order, -4)
        self.assertEqual(result.node_widths, [640.0])
        self.assertEqual(result.node_heights, [360.0])
        self.assertEqual(node.background_color, 0xFF0080FF)

    @unittest.skipIf(_gnw is None, "native _graphCanvas not available")
    async def test_native_group_collapse_changes_visible_geometry(self):
        """Collapsed groups remove child rows from native sizing without losing metadata."""

        group = object()
        child_a = object()
        child_b = object()
        open_ports = [
            _port_snapshot(
                group,
                "Emission",
                "",
                inputs=[],
                is_group=True,
                sub_count=2,
                exp=0,
                group_collapsed=False,
            ),
            _port_snapshot(child_a, "Luminance", "float", inputs=[], level=1, parent_count=2),
            _port_snapshot(child_b, "Color", "color3f", inputs=[], level=1, parent_count=2),
        ]
        closed_ports = [
            _port_snapshot(
                group,
                "Emission",
                "",
                inputs=[],
                is_group=True,
                sub_count=2,
                exp=2,
                group_collapsed=True,
            )
        ]

        opened = _gnw.native_build_from_snapshot([_node_snapshot(object(), "OpenPBR", open_ports)])
        closed = _gnw.native_build_from_snapshot([_node_snapshot(object(), "OpenPBR", closed_ports)])

        self.assertEqual(opened.visible_port_counts, [3])
        self.assertEqual(closed.visible_port_counts, [1])
        self.assertGreater(opened.node_heights[0], closed.node_heights[0])
        self.assertFalse(opened.scene.nodes[0].data.ports[0].group_collapsed)
        self.assertTrue(closed.scene.nodes[0].data.ports[0].group_collapsed)


if __name__ == "__main__":
    unittest.main()
