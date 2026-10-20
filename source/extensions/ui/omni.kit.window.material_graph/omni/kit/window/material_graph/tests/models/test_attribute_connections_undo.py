import contextlib
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import MagicMock, patch

import omni.kit.undo
from pxr import Sdf, UsdShade

from ...scripts.commands.result import CommandResult
from ...scripts.commands.wrappers.ports import ConnectInputToSource
from ...scripts.models.graph.nodes.material import MaterialModel
from ...scripts.models.graph.nodes.prim.model import PrimModel
from ...scripts.models.graph.ports.internal.connections import AttributeConnections
from ...scripts.validation.validator import MaterialValidator
from ..base import MaterialGraphTestBase
from .helpers import DummyPlugin


class TestAttributeConnectionsUndo(MaterialGraphTestBase):
    """Attribute connection undo grouping coverage."""

    async def setUp(self) -> None:
        """Load the test scene and build a prim model."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._shader_path = Sdf.Path("/World/Looks/material/shader")
        self._plugin = DummyPlugin()
        self._shader_prim = self._get_prim_at_path(self._shader_path)
        self._prim_model = PrimModel(
            self._shader_prim,
            "universal",
            self._usd_context,
            self._plugin,
            None,
            UsdShade.Shader,
        )
        self._prim_model.validator = MaterialValidator()

    async def test_set_inputs_closes_disabled_undo_scope_on_failure(self) -> None:
        """Atomic undo suppression should close even when input creation fails."""
        input_model = self._prim_model._inputs.get_child_by_path(
            self._shader_path.AppendProperty(f"{UsdShade.Tokens.inputs}diffuseColor")
        )
        input_model.sync()
        input_model.validator = type(
            "_AllowAllValidator",
            (),
            {"can_connect": staticmethod(lambda *_args, **_kwargs: True)},
        )()

        flags: dict[str, bool] = {"entered": False, "exited": False}

        @contextlib.contextmanager
        def fake_disabled() -> Iterator[None]:
            """Context manager that records enter/exit."""
            flags["entered"] = True
            try:
                yield
            finally:
                flags["exited"] = True

        with patch("omni.kit.undo.disabled", fake_disabled):
            input_model.create_port = lambda *_args, **_kwargs: False
            input_model.model_root._item_changed = MagicMock()
            input_model._pause = True
            input_model._locked = True
            succeeded = input_model._connections.set_inputs([input_model])

        self.assertFalse(succeeded)
        self.assertTrue(flags["entered"])
        self.assertTrue(flags["exited"])
        input_model.model_root._item_changed.assert_called_once_with(None)
        self.assertFalse(input_model._locked)

    async def test_successful_rewire_is_one_atomic_undo_redo_edit(self) -> None:
        """A successful model rewire must round-trip as one exact layer transaction."""
        input_model = self._prim_model.create_input_port("atomicIn", Sdf.ValueTypeNames.Float)
        old_output = self._prim_model.create_output_port("atomicOld", Sdf.ValueTypeNames.Float)
        new_output = self._prim_model.create_output_port("atomicNew", Sdf.ValueTypeNames.Float)
        self.assertTrue(input_model and old_output and new_output)
        input_model.usdshade_port.ConnectToSource(old_output.usdshade_port)
        input_model._connections.set_connections_for_test({old_output.path: old_output})
        input_model.validator = type(
            "_AllowAllValidator",
            (),
            {"can_connect": staticmethod(lambda *_args, **_kwargs: True)},
        )()

        self.assertTrue(input_model._connections.set_inputs([new_output]))
        self.assertEqual(input_model.usdshade_port.GetAttr().GetConnections(), [new_output.path])

        omni.kit.undo.undo()
        self.assertEqual(input_model.usdshade_port.GetAttr().GetConnections(), [old_output.path])
        omni.kit.undo.redo()
        self.assertEqual(input_model.usdshade_port.GetAttr().GetConnections(), [new_output.path])

    async def test_failed_rewire_preserves_existing_source_and_suppresses_success_notify(self) -> None:
        """A failed replacement must keep the prior USD source and visual cache."""
        input_model = self._prim_model.create_input_port("rewireIn", Sdf.ValueTypeNames.Float)
        old_output = self._prim_model.create_output_port("oldSource", Sdf.ValueTypeNames.Float)
        new_output = self._prim_model.create_output_port("newSource", Sdf.ValueTypeNames.Float)
        self.assertIsNotNone(input_model)
        self.assertIsNotNone(old_output)
        self.assertIsNotNone(new_output)

        input_model.usdshade_port.ConnectToSource(old_output.usdshade_port)
        input_model._connections.set_connections_for_test({old_output.path: old_output})
        input_model.validator = type(
            "_AllowAllValidator",
            (),
            {"can_connect": staticmethod(lambda *_args, **_kwargs: True)},
        )()
        input_model.model_root.notify_connection_changed = MagicMock()
        input_model.model_root._item_changed = MagicMock()

        failed = CommandResult(False, False, message="injected connection failure")
        with patch(
            "omni.kit.window.material_graph.scripts.models.graph.ports.internal.connections.ConnectInputToSource",
            return_value=failed,
        ):
            succeeded = input_model._connections.set_inputs([new_output])

        self.assertFalse(succeeded)
        self.assertEqual(
            AttributeConnections._connected_source_path(input_model.usdshade_port),
            old_output.path,
        )
        self.assertEqual(input_model.connected_ports, [old_output])
        input_model.model_root.notify_connection_changed.assert_not_called()
        input_model.model_root._item_changed.assert_called_once_with(None)

    async def test_late_multi_source_failure_restores_exact_state_through_undo_redo(self) -> None:
        """A later source failure must not leave an earlier connection or redo it later."""
        input_model = self._prim_model.create_input_port("multiRewireIn", Sdf.ValueTypeNames.Float)
        old_output = self._prim_model.create_output_port("multiOld", Sdf.ValueTypeNames.Float)
        first_output = self._prim_model.create_output_port("multiFirst", Sdf.ValueTypeNames.Float)
        second_output = self._prim_model.create_output_port("multiSecond", Sdf.ValueTypeNames.Float)
        self.assertTrue(input_model and old_output and first_output and second_output)
        input_model.usdshade_port.ConnectToSource(old_output.usdshade_port)
        input_model._connections.set_connections_for_test({old_output.path: old_output})
        input_model.validator = type(
            "_AllowAllValidator",
            (),
            {"can_connect": staticmethod(lambda *_args, **_kwargs: True)},
        )()

        calls = 0

        def connect_then_fail(target, source):
            """Run one real command, then inject a failure for the next source."""
            nonlocal calls
            calls += 1
            if calls == 1:
                return ConnectInputToSource(target, source)
            return CommandResult(False, False, message="injected late connection failure")

        with patch(
            "omni.kit.window.material_graph.scripts.models.graph.ports.internal.connections.ConnectInputToSource",
            side_effect=connect_then_fail,
        ):
            succeeded = input_model._connections.set_inputs([first_output, second_output])

        self.assertFalse(succeeded)
        self.assertEqual(input_model.usdshade_port.GetAttr().GetConnections(), [old_output.path])
        self.assertEqual(input_model.connected_ports, [old_output])

        omni.kit.undo.undo()
        self.assertEqual(input_model.usdshade_port.GetAttr().GetConnections(), [old_output.path])
        omni.kit.undo.redo()
        self.assertEqual(input_model.usdshade_port.GetAttr().GetConnections(), [old_output.path])

    async def test_set_inputs_rejects_same_prim_cycle(self) -> None:
        """Same-prim input/output connections should be rejected as cycles."""
        input_model = self._prim_model.create_input_port("testIn", Sdf.ValueTypeNames.Float)
        output_model = self._prim_model.create_output_port("testOut", Sdf.ValueTypeNames.Float)
        self.assertIsNotNone(input_model)
        self.assertIsNotNone(output_model)

        input_model.inputs = [output_model]

        self.assertFalse(input_model.usdshade_port.HasConnectedSource())
        self.assertNotIn(output_model.path, [port.path for port in input_model.connected_ports])

    async def test_set_inputs_empty_unlocks_paused_port_after_disconnect(self) -> None:
        """Clearing inputs on paused ports should not leave the model locked."""
        input_model = self._prim_model._inputs.get_child_by_path(
            self._shader_path.AppendProperty(f"{UsdShade.Tokens.inputs}diffuseColor")
        )
        input_model.sync()
        input_model._pause = True
        input_model._locked = True
        input_model.model_root._item_changed = MagicMock()
        input_model.inputs = []

        self.assertFalse(input_model._locked)

    async def test_connected_source_model_resolves_from_authored_output_connection(self) -> None:
        """Output-node connections should cache the post-command source port model from USD."""
        shader_a = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/ConnectionResolve/ShaderA"))
        shader_b = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/ConnectionResolve/ShaderB"))
        source_output = shader_a.CreateOutput("out", Sdf.ValueTypeNames.Float)
        target_output = shader_b.CreateOutput("out", Sdf.ValueTypeNames.Float)
        target_output.ConnectToSource(source_output)

        source_path = source_output.GetAttr().GetPath()
        refreshed_source_model = SimpleNamespace(path=source_path)
        stale_source_model = SimpleNamespace(path=Sdf.Path("/World/Looks/ConnectionResolve/Old.outputs:out"))
        model_root = SimpleNamespace(
            get_item_model=lambda path: refreshed_source_model if path == source_path else None
        )
        target_model = SimpleNamespace(usdshade_port=target_output, model_root=model_root)
        connections = AttributeConnections(target_model, object)
        connections.set_connections_for_test({stale_source_model.path: stale_source_model})

        connections.sync()

        self.assertEqual(connections.connected_ports(), [refreshed_source_model])

    async def test_material_output_connection_notify_item_requests_full_refresh(self) -> None:
        """Root material outputs need full graph refresh after connection edits."""
        material = UsdShade.Material.Define(self._stage, Sdf.Path("/World/Looks/ConnectionNotify/Mat"))
        material_output = material.CreateSurfaceOutput()
        target_model = SimpleNamespace(
            prim=material.GetPrim(),
            proxy_attribute=SimpleNamespace(name=material_output.GetAttr().GetName()),
        )

        self.assertIsNone(AttributeConnections._connection_notify_item(target_model))

    async def test_sync_resolves_authored_output_connection_source_model(self) -> None:
        """Output-node sync should resolve connected source models from authored USD source info."""
        shader_a = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/ConnectionSync/ShaderA"))
        shader_b = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/ConnectionSync/ShaderB"))
        source_output = shader_a.CreateOutput("out", Sdf.ValueTypeNames.Float)
        target_output = shader_b.CreateOutput("out", Sdf.ValueTypeNames.Float)
        target_output.ConnectToSource(source_output)

        source_path = source_output.GetAttr().GetPath()
        refreshed_source_model = SimpleNamespace(path=source_path)
        model_root = SimpleNamespace(
            get_item_model=lambda path: refreshed_source_model if path == source_path else None
        )
        target_model = SimpleNamespace(usdshade_port=target_output, model_root=model_root)
        connections = AttributeConnections(target_model, object)
        connections.set_connections_for_test({source_path: SimpleNamespace(path=source_path)})

        connections.sync()

        self.assertEqual(connections.connected_ports(), [refreshed_source_model])

    async def test_sync_preserves_cache_when_connected_source_info_is_unavailable(self) -> None:
        """If USD reports a source but omits source details, keep the current visual cache."""
        existing_source_model = SimpleNamespace(path=Sdf.Path("/World/Looks/ConnectionSync/ShaderA.outputs:out"))
        target_port = SimpleNamespace(HasConnectedSource=lambda: True, GetConnectedSources=lambda: [])
        target_model = SimpleNamespace(usdshade_port=target_port, model_root=None)
        connections = AttributeConnections(target_model, object)
        connections.set_connections_for_test({existing_source_model.path: existing_source_model})

        connections.sync()

        self.assertEqual(connections.connected_ports(), [existing_source_model])

    async def test_create_input_port_uses_unique_suffix(self) -> None:
        """Creating duplicate input ports should append a numeric suffix."""
        first = self._prim_model.create_input_port("frame", Sdf.ValueTypeNames.Float)
        second = self._prim_model.create_input_port("frame", Sdf.ValueTypeNames.Float)
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)

        prim = self._get_prim_at_path(self._shader_path)
        self.assertTrue(prim.HasAttribute(f"{UsdShade.Tokens.inputs}frame"))
        self.assertTrue(prim.HasAttribute(f"{UsdShade.Tokens.inputs}frame01"))

        self.assertTrue(first.path.name.endswith("frame"))
        self.assertTrue(second.path.name.endswith("frame01"))

    async def test_interface_port_variability_updates(self) -> None:
        """Interface ports should inherit source variability."""
        material_path = Sdf.Path("/World/Looks/material")
        material_prim = self._get_prim_at_path(material_path)
        self.assertTrue(material_prim)
        material_model = MaterialModel(
            material_prim,
            "universal",
            self._usd_context,
            self._plugin,
            validator=MaterialValidator(),
        )

        input_model = material_model.create_input_port("frame", Sdf.ValueTypeNames.Float)
        self.assertIsNotNone(input_model)

        output_model = self._prim_model.create_output_port("frameOut", Sdf.ValueTypeNames.Float)
        self.assertIsNotNone(output_model)
        output_model.proxy_attribute._metadata["variability"] = Sdf.VariabilityUniform

        input_model.inputs = [output_model]
        self.assertEqual(input_model.usdshade_port.GetAttr().GetVariability(), Sdf.VariabilityUniform)

    async def test_create_port_uses_variability(self) -> None:
        """Create input ports should honor the requested variability."""
        input_model = self._prim_model.create_input_port(
            "uniformIn",
            Sdf.ValueTypeNames.Float,
            variability=Sdf.VariabilityUniform,
        )
        self.assertIsNotNone(input_model)
        attr = input_model.usdshade_port.GetAttr()
        self.assertEqual(attr.GetVariability(), Sdf.VariabilityUniform)

    async def test_interface_output_variability_updates(self) -> None:
        """Interface output ports should inherit source variability."""
        material_path = Sdf.Path("/World/Looks/material")
        material_prim = self._get_prim_at_path(material_path)
        self.assertTrue(material_prim)
        material_model = MaterialModel(
            material_prim,
            "universal",
            self._usd_context,
            self._plugin,
            validator=MaterialValidator(),
        )

        output_interface = material_model.create_output_port("frameOut", Sdf.ValueTypeNames.Float)
        self.assertIsNotNone(output_interface)

        source_output = self._prim_model.create_output_port("frameSource", Sdf.ValueTypeNames.Float)
        self.assertIsNotNone(source_output)
        source_output.proxy_attribute._metadata["variability"] = Sdf.VariabilityUniform

        output_interface.inputs = [source_output]
        self.assertEqual(output_interface.usdshade_port.GetAttr().GetVariability(), Sdf.VariabilityUniform)

    async def test_create_output_port_uses_variability(self) -> None:
        """Create output ports should honor the requested variability."""
        output_model = self._prim_model.create_output_port(
            "uniformOut",
            Sdf.ValueTypeNames.Float,
            variability=Sdf.VariabilityUniform,
        )
        self.assertIsNotNone(output_model)
        attr = output_model.usdshade_port.GetAttr()
        self.assertEqual(attr.GetVariability(), Sdf.VariabilityUniform)
