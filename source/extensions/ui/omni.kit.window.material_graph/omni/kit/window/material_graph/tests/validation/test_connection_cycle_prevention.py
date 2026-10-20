# pylint: disable=relative-beyond-top-level,no-member,protected-access
from unittest.mock import patch

from pxr import Sdf, UsdShade

from ...scripts.config.paths import Paths
from ...scripts.models.graph.ports.internal.connections import AttributeConnections
from ...scripts.validation.validator import MaterialValidator
from ..base import MaterialGraphTestBase


class _DummyAttrModel:
    """Minimal source-model shim with a USD port."""

    def __init__(self, path: str, usdshade_port: object) -> None:
        self.path = path
        self.usdshade_port = usdshade_port


class _DummyTargetModel:
    """Minimal target model shim used by AttributeConnections.set_inputs."""

    def __init__(self, prim: object, usdshade_port: object) -> None:
        self.context_name = "universal"
        self._plugin = type("_DummyPlugin", (), {"can_connect": staticmethod(lambda *_args, **_kwargs: True)})()
        self.prim = prim
        self.usdshade_port = usdshade_port
        self.usd_context = None
        self.validator = MaterialValidator()
        self.path = str(usdshade_port.GetAttr().GetPath())
        self._pause = False
        self._locked = False
        self.model_root = None

    def create_port(self) -> bool:
        """Port creation is unnecessary for this guard-path test."""
        return True


class TestConnectionCyclePrevention(MaterialGraphTestBase):
    """Connection-path validation tests that prevent cyclical graph edits."""

    async def test_set_inputs_rejects_self_cycle_connection(self) -> None:
        """Connecting a shader output back into the same shader input is rejected."""
        UsdShade.Material.Define(self._stage, Sdf.Path("/World/Looks/CycleGuard"))
        shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/CycleGuard/Shader"))
        shader_output = shader.CreateOutput("out", Sdf.ValueTypeNames.Float)
        shader_input = shader.CreateInput("in", Sdf.ValueTypeNames.Float)

        target_model = _DummyTargetModel(shader.GetPrim(), shader_input)
        source_model = _DummyAttrModel(str(shader_output.GetAttr().GetPath()), shader_output)
        connections = AttributeConnections(target_model, _DummyAttrModel)

        connections.set_inputs([source_model])

        self.assertEqual(connections.connected_ports(), [])
        self.assertFalse(connections.HasConnectedSource(target_model))

    async def test_set_inputs_rejects_two_node_cycle_connection(self) -> None:
        """Connecting B back to A should be rejected when A already feeds B."""
        UsdShade.Material.Define(self._stage, Sdf.Path("/World/Looks/CycleGuardTwo"))
        shader_a = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/CycleGuardTwo/ShaderA"))
        shader_b = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/CycleGuardTwo/ShaderB"))
        a_output = shader_a.CreateOutput("out", Sdf.ValueTypeNames.Float)
        a_input = shader_a.CreateInput("in", Sdf.ValueTypeNames.Float)
        b_output = shader_b.CreateOutput("out", Sdf.ValueTypeNames.Float)
        b_input = shader_b.CreateInput("in", Sdf.ValueTypeNames.Float)
        b_input.ConnectToSource(a_output)

        target_model = _DummyTargetModel(shader_a.GetPrim(), a_input)
        source_model = _DummyAttrModel(str(b_output.GetAttr().GetPath()), b_output)
        connections = AttributeConnections(target_model, _DummyAttrModel)

        connections.set_inputs([source_model])

        self.assertEqual(connections.connected_ports(), [])
        self.assertFalse(a_input.HasConnectedSource())

    async def test_force_connection_still_rejects_two_node_cycle_connection(self) -> None:
        """Force-connect bypasses type checks, not cycle prevention."""
        UsdShade.Material.Define(self._stage, Sdf.Path("/World/Looks/CycleGuardForce"))
        shader_a = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/CycleGuardForce/ShaderA"))
        shader_b = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/CycleGuardForce/ShaderB"))
        a_output = shader_a.CreateOutput("out", Sdf.ValueTypeNames.Float)
        a_input = shader_a.CreateInput("in", Sdf.ValueTypeNames.Float)
        b_output = shader_b.CreateOutput("out", Sdf.ValueTypeNames.Float)
        b_input = shader_b.CreateInput("in", Sdf.ValueTypeNames.Float)
        b_input.ConnectToSource(a_output)

        target_model = _DummyTargetModel(shader_a.GetPrim(), a_input)
        source_model = _DummyAttrModel(str(b_output.GetAttr().GetPath()), b_output)
        connections = AttributeConnections(target_model, _DummyAttrModel)

        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.ports.internal.connections.is_force_connection_modifier_pressed",
            autospec=True,
            return_value=True,
        ):
            connections.set_inputs([source_model])

        self.assertEqual(connections.connected_ports(), [])
        self.assertFalse(a_input.HasConnectedSource())

    async def test_would_create_cycle_detects_three_node_dependency_path(self) -> None:
        """Connecting C back to A should be rejected when A feeds B and B feeds C."""
        UsdShade.Material.Define(self._stage, Sdf.Path("/World/Looks/CycleGuardThree"))
        shader_a = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/CycleGuardThree/ShaderA"))
        shader_b = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/CycleGuardThree/ShaderB"))
        shader_c = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/CycleGuardThree/ShaderC"))
        a_output = shader_a.CreateOutput("out", Sdf.ValueTypeNames.Float)
        a_input = shader_a.CreateInput("in", Sdf.ValueTypeNames.Float)
        b_output = shader_b.CreateOutput("out", Sdf.ValueTypeNames.Float)
        b_input = shader_b.CreateInput("in", Sdf.ValueTypeNames.Float)
        c_output = shader_c.CreateOutput("out", Sdf.ValueTypeNames.Float)
        c_input = shader_c.CreateInput("in", Sdf.ValueTypeNames.Float)
        b_input.ConnectToSource(a_output)
        c_input.ConnectToSource(b_output)

        target_model = _DummyTargetModel(shader_a.GetPrim(), a_input)
        source_model = _DummyAttrModel(str(c_output.GetAttr().GetPath()), c_output)

        self.assertTrue(MaterialValidator.would_create_cycle(source_model, target_model))

    async def test_would_create_cycle_detects_path_outside_endpoint_parent(self) -> None:
        """Cycle checks should follow dependencies that leave and re-enter the endpoint parent."""
        UsdShade.Material.Define(self._stage, Sdf.Path("/World/Looks/CrossScope"))
        shader_a = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/CrossScope/GroupA/ShaderA"))
        shader_b = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/CrossScope/GroupA/ShaderB"))
        shader_x = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/CrossScope/GroupX/ShaderX"))
        a_output = shader_a.CreateOutput("out", Sdf.ValueTypeNames.Float)
        a_input = shader_a.CreateInput("in", Sdf.ValueTypeNames.Float)
        b_output = shader_b.CreateOutput("out", Sdf.ValueTypeNames.Float)
        b_input = shader_b.CreateInput("in", Sdf.ValueTypeNames.Float)
        x_output = shader_x.CreateOutput("out", Sdf.ValueTypeNames.Float)
        x_input = shader_x.CreateInput("in", Sdf.ValueTypeNames.Float)
        x_input.ConnectToSource(b_output)
        a_input.ConnectToSource(x_output)

        target_model = _DummyTargetModel(shader_b.GetPrim(), b_input)
        source_model = _DummyAttrModel(str(a_output.GetAttr().GetPath()), a_output)

        self.assertTrue(MaterialValidator.would_create_cycle(source_model, target_model))
