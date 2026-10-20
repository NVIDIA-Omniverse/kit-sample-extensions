import omni.kit.commands
from pxr import Sdf, UsdShade

from .base import CommandsTestBase


class TestConnectionsCommand(CommandsTestBase):
    """Connect and disconnect commands drive USD shader connections and must integrate with the undo
    stack so users can revert. RemoveConnections batches disconnects and must also undo correctly.
    We test connect/disconnect roundtrips, RemoveConnections on input and output, invalid ports
    returning failure, and that undo does not reconnect when the source prim was deleted."""

    async def setUp(self) -> None:
        """Load the simple scene for connection command tests."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")
        self._shader_path = Sdf.Path("/World/Looks/material/shader")

    async def test_connect_and_disconnect(self) -> None:
        """Connect and disconnect are undoable."""
        shader = UsdShade.Shader(self._get_prim_at_path(self._shader_path))
        material = UsdShade.Material(self._get_prim_at_path(self._material_path))
        output = shader.CreateOutput("outColor", Sdf.ValueTypeNames.Color3f)
        input_port = material.GetInput("diffuseColor")
        self.assertTrue(input_port)
        if input_port.HasConnectedSource():
            input_port.DisconnectSource()

        omni.kit.commands.execute(
            "MaterialGraph_ConnectUsdShadeToSourceCommand",
            target=input_port,
            source=output,
        )

        def _after() -> None:
            """Validate connection after redo."""
            self.assertTrue(input_port.HasConnectedSource())

        def _before() -> None:
            """Validate disconnect after undo."""
            self.assertFalse(input_port.HasConnectedSource())

        await self._assert_undo_redo(_before, _after)

        omni.kit.commands.execute(
            "MaterialGraph_UsdShadeDisconnectSourceCommand",
            target=input_port,
        )

        def _after_disconnect() -> None:
            """Validate disconnect after redo."""
            self.assertFalse(input_port.HasConnectedSource())

        def _before_disconnect() -> None:
            """Validate connection after undo."""
            self.assertTrue(input_port.HasConnectedSource())

        await self._assert_undo_redo(_before_disconnect, _after_disconnect)

    async def test_remove_connections_command(self) -> None:
        """RemoveConnections disconnects and undoes correctly."""
        shader = UsdShade.Shader(self._get_prim_at_path(self._shader_path))
        material = UsdShade.Material(self._get_prim_at_path(self._material_path))
        output = shader.CreateOutput("outColor", Sdf.ValueTypeNames.Color3f)
        input_port = material.GetInput("diffuseColor")
        self.assertTrue(input_port)
        if input_port.HasConnectedSource():
            input_port.DisconnectSource()
        input_port.ConnectToSource(output)

        dest_attr_path = input_port.GetAttr().GetPath()
        disconnected = [output.GetAttr().GetPath()]

        omni.kit.commands.execute(
            "MaterialGraph_RemoveConnectionsCommand",
            dest_attr_path=dest_attr_path,
            disconnected_values=disconnected,
        )

        def _after() -> None:
            """Validate disconnect after redo."""
            self.assertFalse(input_port.HasConnectedSource())

        def _before() -> None:
            """Validate connection after undo."""
            self.assertTrue(input_port.HasConnectedSource())

        await self._assert_undo_redo(_before, _after)

    async def test_remove_connections_output_branch(self) -> None:
        """RemoveConnections handles output destinations."""
        shader = UsdShade.Shader(self._get_prim_at_path(self._shader_path))
        material = UsdShade.Material(self._get_prim_at_path(self._material_path))
        source_output = shader.GetOutput("surface")
        self.assertTrue(source_output)
        dest_output = material.GetOutput("surface")
        self.assertTrue(dest_output)
        if dest_output.HasConnectedSource():
            dest_output.DisconnectSource()
        dest_output.ConnectToSource(source_output)

        dest_attr_path = dest_output.GetAttr().GetPath()
        disconnected = [source_output.GetAttr().GetPath()]

        omni.kit.commands.execute(
            "MaterialGraph_RemoveConnectionsCommand",
            dest_attr_path=dest_attr_path,
            disconnected_values=disconnected,
        )

        def _after() -> None:
            """Validate disconnect after redo."""
            self.assertFalse(dest_output.HasConnectedSource())

        def _before() -> None:
            """Validate connection after undo."""
            self.assertTrue(dest_output.HasConnectedSource())

        await self._assert_undo_redo(_before, _after)

    async def test_remove_connections_preserves_unselected_sources_exactly(self) -> None:
        """Removing one source must retain and round-trip the ordered remainder."""
        shader = UsdShade.Shader(self._get_prim_at_path(self._shader_path))
        material = UsdShade.Material(self._get_prim_at_path(self._material_path))
        source_a = shader.CreateOutput("removeA", Sdf.ValueTypeNames.Color3f)
        source_b = shader.CreateOutput("keepB", Sdf.ValueTypeNames.Color3f)
        input_port = material.GetInput("diffuseColor")
        previous = [source_a.GetAttr().GetPath(), source_b.GetAttr().GetPath()]
        self.assertTrue(input_port.GetAttr().SetConnections(previous))

        omni.kit.commands.execute(
            "MaterialGraph_RemoveConnectionsCommand",
            dest_attr_path=input_port.GetAttr().GetPath(),
            disconnected_values=[previous[0]],
        )
        self.assertEqual(input_port.GetAttr().GetConnections(), [previous[1]])
        self.assertTrue(omni.kit.undo.undo())
        self.assertEqual(input_port.GetAttr().GetConnections(), previous)
        self.assertTrue(omni.kit.undo.redo())
        self.assertEqual(input_port.GetAttr().GetConnections(), [previous[1]])

    async def test_connect_invalid_ports(self) -> None:
        """Invalid ports return failure and no connection payload."""
        result = omni.kit.commands.execute(
            "MaterialGraph_ConnectUsdShadeToSourceCommand",
            target=None,
            source=None,
        )
        if isinstance(result, tuple) and result and isinstance(result[0], bool):
            success, payload = result
            self.assertFalse(
                success and bool(payload),
                "Connect with invalid inputs should not produce a successful connection payload",
            )
        else:
            self.assertFalse(result)

    async def test_disconnect_undo_after_delete(self) -> None:
        """Undo does not reconnect if source prim was deleted."""
        shader = UsdShade.Shader(self._get_prim_at_path(self._shader_path))
        material = UsdShade.Material(self._get_prim_at_path(self._material_path))
        output = shader.CreateOutput("outColor", Sdf.ValueTypeNames.Color3f)
        input_port = material.GetInput("diffuseColor")
        if input_port.HasConnectedSource():
            input_port.DisconnectSource()
        input_port.ConnectToSource(output)

        omni.kit.commands.execute(
            "MaterialGraph_UsdShadeDisconnectSourceCommand",
            target=input_port,
        )
        self._stage.RemovePrim(self._shader_path)
        self.assertTrue(omni.kit.undo.undo())
        self.assertFalse(input_port.HasConnectedSource())

    async def test_connect_undo_restores_exact_previous_source_list(self) -> None:
        """Replacing a connection must round-trip every prior authored source path."""
        shader = UsdShade.Shader(self._get_prim_at_path(self._shader_path))
        material = UsdShade.Material(self._get_prim_at_path(self._material_path))
        previous_a = shader.CreateOutput("previousA", Sdf.ValueTypeNames.Color3f)
        previous_b = shader.CreateOutput("previousB", Sdf.ValueTypeNames.Color3f)
        replacement = shader.CreateOutput("replacement", Sdf.ValueTypeNames.Color3f)
        input_port = material.GetInput("diffuseColor")
        previous_paths = [previous_a.GetAttr().GetPath(), previous_b.GetAttr().GetPath()]
        self.assertTrue(input_port.GetAttr().SetConnections(previous_paths))

        omni.kit.commands.execute(
            "MaterialGraph_ConnectUsdShadeToSourceCommand",
            target=input_port,
            source=replacement,
        )
        self.assertNotEqual(input_port.GetAttr().GetConnections(), previous_paths)
        self.assertTrue(omni.kit.undo.undo())
        self.assertEqual(input_port.GetAttr().GetConnections(), previous_paths)

    async def test_disconnect_undo_restores_exact_previous_source_list(self) -> None:
        """Disconnect undo must restore ordered multi-source connection opinions."""
        shader = UsdShade.Shader(self._get_prim_at_path(self._shader_path))
        material = UsdShade.Material(self._get_prim_at_path(self._material_path))
        source_a = shader.CreateOutput("sourceA", Sdf.ValueTypeNames.Color3f)
        source_b = shader.CreateOutput("sourceB", Sdf.ValueTypeNames.Color3f)
        input_port = material.GetInput("diffuseColor")
        previous_paths = [source_a.GetAttr().GetPath(), source_b.GetAttr().GetPath()]
        self.assertTrue(input_port.GetAttr().SetConnections(previous_paths))

        omni.kit.commands.execute("MaterialGraph_UsdShadeDisconnectSourceCommand", target=input_port)
        self.assertEqual(input_port.GetAttr().GetConnections(), [])
        self.assertTrue(omni.kit.undo.undo())
        self.assertEqual(input_port.GetAttr().GetConnections(), previous_paths)
