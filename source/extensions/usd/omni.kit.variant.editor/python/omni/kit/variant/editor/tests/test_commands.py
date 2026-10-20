from pathlib import Path

import carb
import omni.kit.app
import omni.kit.stage_templates
import omni.kit.test
from pxr import Sdf


def _get_kit_major_version() -> int:
    """Return Kit major version (e.g. 107 from '107.5')."""
    try:
        short = omni.kit.app.get_app().get_kit_version_short()
        return int(str(short).split(".", 1)[0])
    except Exception:
        return 0


class TestCommands(omni.kit.test.AsyncTestCase):
    _USDLUX_VERSION_SETTING = "/rtx/lighting/defaultUsdLuxVersion"

    async def test_commands(self):
        """Test commands with legacy, non-UsdLux-compliant lights."""
        await self._run_with_usdlux_version(version=2411, suffix="")

    async def test_commands_usdlux_2505(self):
        """Test commands with UsdLux-compliant lights."""
        if _get_kit_major_version() < 109:
            # Support for UsdLux 25.05 was added in Kit SDK 109. Should not be tested on older versions.
            self.skipTest(f"Requires Kit SDK >= 109 (current: {omni.kit.app.get_app().get_kit_version()})")
        await self._run_with_usdlux_version(version=2505, suffix="UsdLux2505")

    async def _run_with_usdlux_version(self, version: int, suffix: str):
        settings = carb.settings.get_settings()
        prev = settings.get_as_int(self._USDLUX_VERSION_SETTING) if hasattr(settings, "get_as_int") else None
        try:
            settings.set(self._USDLUX_VERSION_SETTING, version)
            await self._test_commands_impl(file_name_suffix=suffix)
        finally:
            if prev is not None:
                settings.set(self._USDLUX_VERSION_SETTING, prev)

    async def _test_commands_impl(self, file_name_suffix: str = ""):
        await omni.kit.stage_templates.new_stage_async(template=None)

        stage = omni.usd.get_context().get_stage()

        def compare_layer(file_name: str):
            # Save current layer
            out_file_stem = file_name + file_name_suffix

            out_put_path = Path(omni.kit.test.get_test_output_path()) / (out_file_stem + ".usda")
            out_put_layer = Sdf.Layer.CreateNew(str(out_put_path))

            out_put_layer.TransferContent(stage.GetRootLayer())
            out_put_layer.Save()

            # Load right result layer
            result_dir = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "tests" / "cmd_stages"
            layer_path = (result_dir / out_file_stem).with_suffix(".usda")
            result_layer = Sdf.Layer.FindOrOpen(str(layer_path))

            # Compare
            self.assertTrue(result_layer is not None)
            if result_layer is not None:
                self.assertTrue(out_put_layer.ExportToString() == result_layer.ExportToString())

        prim = stage.GetPrimAtPath("/World")

        # Test AddVariantSet
        self.assertTrue(not prim.GetVariantSets().GetNames())

        org_layer_str = stage.GetRootLayer().ExportToString()

        result, ret = omni.kit.commands.execute(
            "AddVariantSet",
            prim_path="/World",
            variant_set_name="variantSet",
            auto_postfix=True,
        )

        compare_layer("addVariantSet")

        omni.kit.undo.undo()

        self.assertTrue(stage.GetRootLayer().ExportToString() == org_layer_str)

        omni.kit.undo.redo()

        compare_layer("addVariantSet")

        # Test RemoveVariantSet
        org_layer_str = stage.GetRootLayer().ExportToString()

        result, ret = omni.kit.commands.execute("RemoveVariantSet", prim_path="/World", variant_set_name="variantSet")

        compare_layer("removeVariantSet")

        omni.kit.undo.undo()

        self.assertTrue(stage.GetRootLayer().ExportToString() == org_layer_str)

        # Test RenameVariantSet
        result, ret = omni.kit.commands.execute(
            "RenameVariantSet",
            prim_path="/World",
            variant_set_name="variantSet",
            new_name="variantSetNew",
        )
        compare_layer("renameVariantSet")

        omni.kit.undo.undo()

        self.assertTrue(stage.GetRootLayer().ExportToString() == org_layer_str)

        # Test AddVariant
        result, ret = omni.kit.commands.execute(
            "AddVariant",
            prim_path="/World",
            variant_set_name="variantSet",
            variant_name="variant",
            auto_postfix=True,
        )

        compare_layer("addVariant")

        omni.kit.undo.undo()

        self.assertTrue(stage.GetRootLayer().ExportToString() == org_layer_str)

        omni.kit.undo.redo()

        compare_layer("addVariant")

        # Test RemoveVariant
        org_layer_str = stage.GetRootLayer().ExportToString()

        result, ret = omni.kit.commands.execute(
            "RemoveVariant",
            prim_path="/World",
            variant_set_name="variantSet",
            variant_name="variant",
        )

        compare_layer("removeVariant")

        omni.kit.undo.undo()

        self.assertTrue(stage.GetRootLayer().ExportToString() == org_layer_str)

        # Test RenameVariant

        result, ret = omni.kit.commands.execute(
            "RenameVariant",
            prim_path="/World",
            variant_set_name="variantSet",
            variant_name="variant",
            new_name="variantNew",
        )

        compare_layer("renameVariant")

        omni.kit.undo.undo()

        self.assertTrue(stage.GetRootLayer().ExportToString() == org_layer_str)

        # Test EditVariant
        omni.kit.commands.execute(
            "SelectVariantPrim",
            prim_path="/World",
            vset_name="variantSet",
            var_name="variant",
        )

        omni.kit.commands.execute(
            "EditVariant",
            prim_path="/World",
            variant_set_name="variantSet",
            cmd_name="ChangeProperty",
            cmd_args={
                "prop_path": "/World.visibility",
                "value": "invisible",
                "prev": None,
            },
        )

        omni.kit.commands.execute(
            "EditVariant",
            prim_path="/World",
            variant_set_name="variantSet",
            cmd_name="AddRelationshipTarget",
            cmd_args={
                "relationship": prim.GetRelationship("proxyPrim"),
                "target": "/World",
            },
        )

        compare_layer("editVariant")

        # Test PasteVariant
        omni.kit.commands.execute(
            "PasteVariant",
            prim_path="/World",
            variant_set_name="variantSet",
            clipboard={"/World.visibility": "inherited"},
        )

        compare_layer("pasteVariant")

        # Test DuplicateVariant
        org_layer_str = stage.GetRootLayer().ExportToString()

        result, ret = omni.kit.commands.execute(
            "DuplicateVariant",
            prim_path="/World",
            variant_set_name="variantSet",
            variant_name="variant",
            new_name="variantDup",
            auto_postfix=True,
        )

        compare_layer("dupVariant")

        omni.kit.undo.undo()

        self.assertTrue(stage.GetRootLayer().ExportToString() == org_layer_str)
