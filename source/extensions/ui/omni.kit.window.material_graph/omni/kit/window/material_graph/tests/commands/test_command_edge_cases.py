# pylint: disable=relative-beyond-top-level,no-member
from unittest.mock import MagicMock, patch

from pxr import Sdf, UsdShade

from ...scripts.commands.impl.connections import MaterialGraph_RemoveConnectionsCommand
from ...scripts.commands.impl.metadata import (
    MaterialGraph_SetPrimCustomDataCommand,
    MaterialGraph_SetPrimCustomDataKeyCommand,
)
from ...scripts.commands.impl.ports import MaterialGraph_RenamePropertyCommand
from ...scripts.commands.impl.prim import MaterialGraph_DeletePrimsCommand
from ...scripts.commands.impl.prim.delete import _AttributeSpecSnapshot
from ...scripts.config.paths import Paths
from .base import CommandsTestBase


class TestCommandEdgeCases(CommandsTestBase):
    """Remove-connections and rename-property commands must behave safely when the stage is in
    inconsistent or edge states (e.g. undo after dest attribute removed, missing source, same-name
    rename). We test that undo doesn't crash and that no-op cases don't create attributes."""

    async def setUp(self) -> None:
        """Load the simple scene for edge-case command coverage."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._shader_path = Sdf.Path("/World/Looks/material/shader")

    async def test_remove_connections_undo_with_missing_dest(self) -> None:
        """Undo is safe when destination attribute was removed."""
        prim = self._get_prim_at_path(self._shader_path)
        input_attr = prim.CreateAttribute(f"{UsdShade.Tokens.inputs}testIn", Sdf.ValueTypeNames.Float)
        output_attr = prim.CreateAttribute(f"{UsdShade.Tokens.outputs}testOut", Sdf.ValueTypeNames.Float)
        input_port = UsdShade.Input(input_attr)
        output_port = UsdShade.Output(output_attr)
        input_port.ConnectToSource(output_port)

        cmd = MaterialGraph_RemoveConnectionsCommand(input_attr.GetPath(), [output_attr.GetPath()], stage=self._stage)
        self.assertTrue(cmd.do())

        prim.RemoveProperty(f"{UsdShade.Tokens.inputs}testIn")
        cmd.undo()
        self.assertFalse(prim.HasAttribute(f"{UsdShade.Tokens.inputs}testIn"))

    async def test_remove_connections_write_failure_rolls_back_and_latches(self) -> None:
        """A failed batched connection write restores sources and cannot mutate on redo."""
        source_a = Sdf.Path("/World/A.outputs:out")
        source_b = Sdf.Path("/World/B.outputs:out")
        edit_layer = Sdf.Layer.CreateAnonymous("remove_connections_failure.usda")
        Sdf.CreatePrimInLayer(edit_layer, "/Keep")
        before = edit_layer.ExportToString()
        dest_path = Sdf.Path("/World/Target.inputs:in")
        dest_attr = MagicMock()
        dest_attr.GetConnections.return_value = [source_a, source_b]

        def fail_remove(_path: Sdf.Path) -> bool:
            """Simulate a partially authored USD failure."""
            Sdf.JustCreatePrimAttributeInLayer(
                edit_layer,
                dest_path,
                Sdf.ValueTypeNames.Float,
                Sdf.VariabilityVarying,
                False,
            )
            return False

        dest_attr.RemoveConnection.side_effect = fail_remove
        stage = MagicMock()
        stage.GetAttributeAtPath.return_value = dest_attr
        stage.GetEditTarget.return_value.GetLayer.return_value = edit_layer
        stage.GetEditTarget.return_value.MapToSpecPath.return_value = dest_path
        cmd = MaterialGraph_RemoveConnectionsCommand(
            dest_path,
            [source_a],
            stage=self._stage,
        )
        cmd._get_stage = lambda: stage

        self.assertFalse(cmd.do())
        self.assertEqual(edit_layer.ExportToString(), before)
        dest_attr.RemoveConnection.assert_called_once_with(source_a)
        self.assertFalse(cmd.do())
        cmd.undo()
        dest_attr.RemoveConnection.assert_called_once_with(source_a)

    async def test_delete_prims_partial_failure_rolls_back_and_latches(self) -> None:
        """A partial native delete must roll back once and never retry from a failed command."""
        prim_path = self._shader_path.AppendChild("delete_failure")
        self._stage.DefinePrim(prim_path, "Shader")
        native_command = MagicMock()

        with patch(
            f"{Paths.MODULE_ID}.scripts.commands.impl.prim.delete.DeletePrimsCommand",
            return_value=native_command,
        ) as command_type:
            command = MaterialGraph_DeletePrimsCommand([prim_path], stage=self._stage)
            self.assertFalse(command.do())
            self.assertTrue(self._stage.GetPrimAtPath(prim_path))
            self.assertFalse(command.do())
            command.undo()

        command_type.assert_called_once_with([prim_path], stage=self._stage)
        native_command.do.assert_called_once_with()
        native_command.undo.assert_called_once_with()

    async def test_delete_prims_exception_attempts_rollback_and_logs(self) -> None:
        """An exception from Kit delete is contained, rolled back, and reported through the extension logger."""
        prim_path = self._shader_path.AppendChild("delete_exception")
        self._stage.DefinePrim(prim_path, "Shader")
        native_command = MagicMock()
        native_command.do.side_effect = RuntimeError("injected delete failure")

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.commands.impl.prim.delete.DeletePrimsCommand",
                return_value=native_command,
            ),
            patch(f"{Paths.MODULE_ID}.scripts.commands.impl.prim.delete.log_exception") as log_error,
        ):
            command = MaterialGraph_DeletePrimsCommand([prim_path], stage=self._stage)
            self.assertFalse(command.do())

        native_command.undo.assert_called_once_with()
        log_error.assert_called_once()

    async def test_delete_prims_restore_exception_is_contained_and_reported(self) -> None:
        """A bad layer during undo must report failure without escaping the command boundary."""
        attribute_path = self._shader_path.AppendProperty("inputs:broken")
        target_layer = MagicMock()
        target_layer.GetAttributeAtPath.side_effect = RuntimeError("closed layer")
        command = MaterialGraph_DeletePrimsCommand([self._shader_path], stage=self._stage)
        command._snapshots = [
            _AttributeSpecSnapshot(
                attribute_path=attribute_path,
                spec_path=attribute_path,
                target_layer=target_layer,
                snapshot=Sdf.Layer.CreateAnonymous("delete_restore_exception.usda"),
                authored=True,
                before_prim_paths=frozenset(),
            )
        ]

        with patch(f"{Paths.MODULE_ID}.scripts.commands.impl.prim.delete.log_exception") as log_error:
            self.assertFalse(command._restore_affected_specs())

        log_error.assert_called_once()

    async def test_metadata_commands_roll_back_failed_writes_and_latch(self) -> None:
        """Failed customData setters restore the original dictionary and stay failed."""
        previous = {"keep": 1, "position:mdl": (1.0, 2.0)}
        prim = MagicMock()
        prim.IsValid.return_value = True
        prim.GetCustomData.return_value = previous
        stage = MagicMock()
        stage.GetPrimAtPath.return_value = prim

        whole = MaterialGraph_SetPrimCustomDataCommand(
            self._shader_path,
            {"replacement": True},
            stage=self._stage,
        )
        whole._get_stage = lambda: stage
        prim.SetCustomData.side_effect = [False, True]
        self.assertIsNone(whole.do())
        self.assertEqual(prim.SetCustomData.call_args_list[-1].args[0], previous)
        self.assertIsNone(whole.do())
        whole.undo()
        self.assertEqual(prim.SetCustomData.call_count, 2)

        prim.reset_mock()
        prim.IsValid.return_value = True
        prim.GetCustomData.return_value = previous
        prim.SetCustomData.side_effect = [True, True]
        prim.SetCustomDataByKey.return_value = False
        keyed = MaterialGraph_SetPrimCustomDataKeyCommand(
            self._shader_path,
            "position:mdl",
            (3.0, 4.0),
            stage=self._stage,
        )
        keyed._get_stage = lambda: stage
        self.assertIsNone(keyed.do())
        self.assertEqual(prim.SetCustomData.call_args_list[-1].args[0], previous)
        self.assertIsNone(keyed.do())
        keyed.undo()
        prim.SetCustomDataByKey.assert_called_once_with("position:mdl", (3.0, 4.0))

    async def test_rename_property_missing_source_is_noop(self) -> None:
        """Missing source rename does not create new attributes."""
        prim = self._get_prim_at_path(self._shader_path)
        cmd = MaterialGraph_RenamePropertyCommand(
            self._shader_path, f"{UsdShade.Tokens.inputs}missing", f"{UsdShade.Tokens.inputs}new", stage=self._stage
        )
        cmd.do()
        self.assertFalse(prim.HasAttribute(f"{UsdShade.Tokens.inputs}new"))

    async def test_rename_property_same_name_is_noop(self) -> None:
        """Same-name rename does not mutate attributes."""
        prim = self._get_prim_at_path(self._shader_path)
        prim.CreateAttribute(f"{UsdShade.Tokens.inputs}temp", Sdf.ValueTypeNames.Float)
        cmd = MaterialGraph_RenamePropertyCommand(
            self._shader_path, f"{UsdShade.Tokens.inputs}temp", f"{UsdShade.Tokens.inputs}temp", stage=self._stage
        )
        cmd.do()
        self.assertTrue(prim.HasAttribute(f"{UsdShade.Tokens.inputs}temp"))
