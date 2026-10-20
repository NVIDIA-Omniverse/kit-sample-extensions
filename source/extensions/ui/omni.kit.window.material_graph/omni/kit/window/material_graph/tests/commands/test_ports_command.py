import omni.kit.commands
import omni.kit.undo
from pxr import Sdf, Usd, UsdShade, UsdUI

from ...scripts.commands.wrappers.ports import CreateInputPort
from .base import CommandsTestBase


class TestPortsCommand(CommandsTestBase):
    """CreateInputPortCommand and CreateOutputPortCommand add input/output ports to shaders and
    must apply NodeGraphNodeAPI when missing and integrate with undo. We test create/undo for
    input and output and that API is applied on create and removed on undo."""

    async def setUp(self) -> None:
        """Load the simple scene for port command tests."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")
        self._shader_path = Sdf.Path("/World/Looks/material/shader")

    async def test_create_input_port_undo_redo(self) -> None:
        """CreateInputPort creates and undoes."""
        port_name = f"{UsdShade.Tokens.inputs}newInput"
        omni.kit.commands.execute(
            "MaterialGraph_CreateInputPortCommand",
            prim_path=self._shader_path,
            port_name=port_name,
            port_type=Sdf.ValueTypeNames.Color3f,
        )

        def _after() -> None:
            """Validate input creation after redo."""
            prim = self._get_prim_at_path(self._shader_path)
            self.assertTrue(prim.HasAttribute(f"{UsdShade.Tokens.inputs}newInput"))

        def _before() -> None:
            """Validate input removal after undo."""
            prim = self._get_prim_at_path(self._shader_path)
            self.assertFalse(prim.HasAttribute(f"{UsdShade.Tokens.inputs}newInput"))

        await self._assert_undo_redo(_before, _after)

    async def test_create_output_port_undo_redo(self) -> None:
        """CreateOutputPort creates and undoes."""
        port_name = f"{UsdShade.Tokens.outputs}newOutput"
        omni.kit.commands.execute(
            "MaterialGraph_CreateOutputPortCommand",
            prim_path=self._shader_path,
            port_name=port_name,
            port_type=Sdf.ValueTypeNames.Float,
        )

        def _after() -> None:
            """Validate output creation after redo."""
            prim = self._get_prim_at_path(self._shader_path)
            attr = self._get_attribute_at_path(self._shader_path.AppendProperty(f"{UsdShade.Tokens.outputs}newOutput"))
            self.assertTrue(UsdShade.Output.IsOutput(attr))

        def _before() -> None:
            """Validate output removal after undo."""
            prim = self._get_prim_at_path(self._shader_path)
            self.assertFalse(prim.HasAttribute(f"{UsdShade.Tokens.outputs}newOutput"))

        await self._assert_undo_redo(_before, _after)

    async def test_nodegraph_api_applied_and_removed(self) -> None:
        """Port creation applies NodeGraphNodeAPI when missing and removes on undo."""
        temp_path = self._material_path.AppendChild("tempPortShader")
        prim = UsdShade.Shader.Define(self._stage, temp_path).GetPrim()
        schema_name = "NodeGraphNodeAPI"
        # Force a clean apiSchemas list so apply/remove can be asserted deterministically.
        prim.SetMetadata(Usd.Tokens.apiSchemas, Sdf.TokenListOp.CreateExplicit([]))
        omni.kit.commands.execute(
            "MaterialGraph_CreateInputPortCommand",
            prim_path=temp_path,
            port_name=f"{UsdShade.Tokens.inputs}temp",
            port_type=Sdf.ValueTypeNames.Float,
        )

        def _after() -> None:
            """Validate API application after redo."""
            prim_after = self._get_prim_at_path(temp_path)
            self.assertTrue(prim_after.HasAttribute(f"{UsdShade.Tokens.inputs}temp"))
            api_schemas = prim_after.GetMetadata(Usd.Tokens.apiSchemas) or []
            if hasattr(api_schemas, "GetAddedOrExplicitItems"):
                api_schemas = list(api_schemas.GetAddedOrExplicitItems())
            else:
                api_schemas = list(api_schemas)
            self.assertIn(schema_name, api_schemas)

        def _before() -> None:
            """Validate API removal after undo."""
            prim_before = self._get_prim_at_path(temp_path)
            self.assertFalse(prim_before.HasAttribute(f"{UsdShade.Tokens.inputs}temp"))
            api_schemas = prim_before.GetMetadata(Usd.Tokens.apiSchemas) or []
            if hasattr(api_schemas, "GetAddedOrExplicitItems"):
                api_schemas = list(api_schemas.GetAddedOrExplicitItems())
            else:
                api_schemas = list(api_schemas)
            self.assertNotIn(schema_name, api_schemas)

        await self._assert_undo_redo(_before, _after)

    async def test_invalid_wrapper_port_type_is_rejected_without_partial_mutation(self) -> None:
        """Wrapper validation must reject invalid types before command execution."""
        temp_path = self._material_path.AppendChild("invalidPortShader")
        prim = UsdShade.Shader.Define(self._stage, temp_path).GetPrim()
        prim.SetMetadata(Usd.Tokens.apiSchemas, Sdf.TokenListOp.CreateExplicit([]))
        invalid_type = Sdf.ValueTypeNames.Find("not_a_registered_sdf_type")
        self.assertFalse(invalid_type)

        result = CreateInputPort(temp_path, "invalid", invalid_type)

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "invalid_port_type")
        self.assertFalse(prim.HasAttribute(f"{UsdShade.Tokens.inputs}invalid"))
        self.assertFalse(prim.HasAPI(UsdUI.NodeGraphNodeAPI))

    async def test_direct_command_invalid_port_type_does_not_apply_nodegraph_api(self) -> None:
        """Direct command callers retain the same invalid-type mutation guard."""
        temp_path = self._material_path.AppendChild("invalidDirectPortShader")
        prim = UsdShade.Shader.Define(self._stage, temp_path).GetPrim()
        prim.SetMetadata(Usd.Tokens.apiSchemas, Sdf.TokenListOp.CreateExplicit([]))
        invalid_type = Sdf.ValueTypeNames.Find("not_a_registered_sdf_type")

        _success, result = omni.kit.commands.execute(
            "MaterialGraph_CreateInputPortCommand",
            prim_path=temp_path,
            port_name="invalid",
            port_type=invalid_type,
        )

        self.assertIsNone(result)
        self.assertFalse(prim.HasAttribute(f"{UsdShade.Tokens.inputs}invalid"))
        self.assertFalse(prim.HasAPI(UsdUI.NodeGraphNodeAPI))

    async def test_direct_command_never_claims_or_deletes_an_existing_attribute(self) -> None:
        """A duplicate direct create must leave the existing port and undo stack untouched."""
        prim = self._get_prim_at_path(self._shader_path)
        attr_name = f"{UsdShade.Tokens.inputs}existingAudit"
        existing = prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.Float, custom=True)
        existing.Set(4.25)

        success, result = omni.kit.commands.execute(
            "MaterialGraph_CreateInputPortCommand",
            prim_path=self._shader_path,
            port_name=attr_name,
            port_type=Sdf.ValueTypeNames.Float,
            stage=self._stage,
        )

        self.assertTrue(success)
        self.assertIsNone(result)
        self.assertTrue(prim.GetAttribute(attr_name).IsCustom())
        self.assertEqual(prim.GetAttribute(attr_name).Get(), 4.25)
        omni.kit.undo.undo()
        omni.kit.undo.redo()
        self.assertTrue(prim.HasAttribute(attr_name))
        self.assertEqual(prim.GetAttribute(attr_name).Get(), 4.25)
