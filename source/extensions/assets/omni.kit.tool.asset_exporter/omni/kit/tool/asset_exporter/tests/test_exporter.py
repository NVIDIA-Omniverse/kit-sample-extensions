import asyncio
import json
import os
import platform
import tempfile
import unittest
from pathlib import Path

import carb.tokens
import omni.client
import omni.kit.app
import omni.kit.asset_converter
import omni.kit.commands
import omni.kit.test
import omni.kit.tool.asset_exporter
from omni.kit.tool.asset_exporter.common import BAKE_MDL_SUPPORTED
from omni.kit.window.file_exporter import get_file_exporter
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

g_token = carb.tokens.get_tokens_interface()
EXT_ROOT_PATH = Path(g_token.resolve("${omni.kit.tool.asset_exporter}"))
TEST_DATA = EXT_ROOT_PATH / "data"

KIT_VERSION = omni.kit.app.get_app().get_kit_version()

DISTILL_AND_BAKE_UNSUPPORTED = "Kit 111 EA1: omni.mdl.distill_and_bake is not supported"


class TestExporter(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        pass

    # After running each test
    async def tearDown(self):
        pass

    async def _wait(self, frames=10):
        for i in range(frames):
            await omni.kit.app.get_app().next_update_async()

    async def _prepare_simple_cube(self):
        await omni.usd.get_context().new_stage_async()
        stage = omni.usd.get_context().get_stage()
        result, path = omni.kit.commands.execute("CreateMeshPrim", prim_type="Cube")
        self.assertTrue(result)
        prim = stage.GetPrimAtPath(path)
        self.assertTrue(prim)

        return stage, prim

    async def test_export_from_menu(self):
        import omni.kit.ui_test as ui_test

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "cube.usd")
            stage = Usd.Stage.CreateNew(input_path)
            stage.Save()
            stage = None
            result, _ = await omni.usd.get_context().open_stage_async(input_path)
            self.assertTrue(result)
            omni.kit.commands.execute("CreateMeshPrim", prim_type="Cube")

            output_path = os.path.join(tmpdir, "cube.gltf")
            await ui_test.menu_click("File/Export")
            await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()
            self.assertTrue(ui_test.find("Select Export Path"))

            file_exporter = get_file_exporter()
            file_exporter.click_apply(output_path)
            await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()

            option_window = ui_test.find("Export Options")
            self.assertTrue(option_window)
            click_button = option_window.find("**/Button[*].name=='export'")
            self.assertTrue(click_button)
            await click_button.click()

            # 3s is enough to export a single box
            await asyncio.sleep(3.0)

            result, _ = await omni.client.stat_async(output_path)
            self.assertEqual(result, omni.client.Result.OK)

            await omni.usd.get_context().close_stage_async()
            stage = None

    @unittest.skipIf(
        "aarch64" in platform.machine(),
        "export to usd fails on linux-aarch64. Skip for now",
    )
    async def test_simple_usd_to_supported_formats(self):
        stage, prim = await self._prepare_simple_cube()
        with tempfile.TemporaryDirectory() as tmpdir:
            for ext in [".obj", ".glb", ".gltf", ".fbx", ".usdz"]:
                output_path = os.path.join(tmpdir, "cube" + ext)
                output_path = output_path.replace("\\", "/")
                exporter = omni.kit.tool.asset_exporter.get_instance()
                exporter._export_file(stage, output_path)
                await self._wait()
                exporter._export_option_window._on_export_fn()
                # 3s is enough to export a single box
                await asyncio.sleep(3.0)
                self.assertTrue(os.path.exists(output_path))

                # Converts assets back into USD to check if the cube is exported successfully
                layer = Sdf.Layer.CreateAnonymous()
                converter_manager = omni.kit.asset_converter.get_instance()
                context = omni.kit.asset_converter.AssetConverterContext()
                task = converter_manager.create_converter_task(output_path, layer.identifier, None, context)
                success = await task.wait_until_finished()
                self.assertTrue(success, f"Failed to convert asset {output_path}.")

                converted_stage = Usd.Stage.Open(layer)
                mesh_prim = None
                for prim in converted_stage.Traverse():
                    if prim.IsA(UsdGeom.Mesh):
                        mesh_prim = UsdGeom.Mesh(prim)
                        break

                self.assertTrue(mesh_prim)
                points = mesh_prim.GetPointsAttr().Get()
                face_indices = mesh_prim.GetFaceVertexIndicesAttr().Get()
                normals = mesh_prim.GetNormalsAttr().Get()
                face_counts = mesh_prim.GetFaceVertexCountsAttr().Get()
                self.assertTrue(len(points) > 0)
                self.assertTrue(len(face_indices) > 0)
                self.assertTrue(len(normals) > 0)
                self.assertTrue(len(face_counts) > 0)

    @unittest.skipIf(BAKE_MDL_SUPPORTED, "MDL baking is supported: the option is shown")
    async def test_bake_mdl_option_hidden_when_unsupported(self):
        stage, _ = await self._prepare_simple_cube()
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = omni.kit.tool.asset_exporter.get_instance()
            exporter._export_file(stage, os.path.join(tmpdir, "test.gltf"))
            await self._wait()
            # Kit 111 EA1: no "Export Baked MDL" checkbox, so the export never asks for omni.mdl.distill_and_bake.
            self.assertIsNone(exporter._export_option_window._export_baked_mdl_checkbox)
            self.assertIsNotNone(exporter._export_option_window._export_mdl_gltf_extension_checkbox)
            exporter._export_option_window._window.visible = False
            stage = None
            await omni.usd.get_context().close_stage_async()

    @unittest.skipIf(not BAKE_MDL_SUPPORTED, DISTILL_AND_BAKE_UNSUPPORTED)
    @unittest.skipIf(os.getenv("ETM_ACTIVE"), "skipped in ETM")
    async def test_export_mdl_gltf_extension_with_baking(self):
        await omni.usd.get_context().new_stage_async()
        stage = omni.usd.get_context().get_stage()
        result, path = omni.kit.commands.execute("CreateMeshPrim", prim_type="Cube")
        self.assertTrue(result)
        prim = stage.GetPrimAtPath(path)
        self.assertTrue(prim)

        looks_scope = UsdGeom.Scope.Define(stage, "/World/Looks")
        self.assertTrue(looks_scope)
        material = UsdShade.Material.Define(stage, "/World/Looks/OmniSurfaceLite")
        self.assertTrue(material)
        shader = UsdShade.Shader.Define(stage, "/World/Looks/OmniSurfaceLite/Shader")
        self.assertTrue(shader)
        shader.CreateInput("diffuse_reflection_color", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0, 1, 0))
        shader.CreateImplementationSourceAttr(UsdShade.Tokens.sourceAsset)
        shader.SetSourceAsset("OmniSurfaceLite.mdl", "mdl")
        shader.SetSourceAssetSubIdentifier("OmniSurfaceLite", "mdl")
        material.CreateSurfaceOutput("mdl").ConnectToSource(shader.ConnectableAPI(), "out")
        UsdShade.MaterialBindingAPI(prim.GetPrim()).Bind(material)

        with tempfile.TemporaryDirectory() as tmpdir:
            usd_path = os.path.join(tmpdir, "test.usd")
            output_path = os.path.join(tmpdir, "test.gltf")
            result, error_msg, _ = await omni.usd.get_context().save_as_stage_async(usd_path)
            self.assertTrue(result, error_msg)

            stage = omni.usd.get_context().get_stage()

            exporter = omni.kit.tool.asset_exporter.get_instance()
            exporter._export_file(stage, output_path)
            await self._wait()
            exporter._export_option_window._export_mdl_gltf_extension_checkbox.model.set_value(True)
            exporter._export_option_window._export_baked_mdl_checkbox.model.set_value(True)
            exporter._export_option_window._on_export_fn()
            # 3s is enough to export a single box
            await asyncio.sleep(3.0)
            self.assertTrue(os.path.exists(output_path))

            stage = None
            result, error_msg = await omni.usd.get_context().close_stage_async()
            self.assertTrue(result, error_msg)

            with open(output_path) as gltf_file:
                gltf = json.load(gltf_file)

                self.assertEqual(len(gltf["materials"]), 1)
                material = gltf["materials"][0]
                self.assertEqual(material["extensions"]["NV_materials_mdl"]["functionCall"], 0)

                # this only exists if baking was successful
                self.assertIn("pbrMetallicRoughness", material)
                self.assertIn("baseColorFactor", material["pbrMetallicRoughness"])

                nv_materials_mdl = gltf["extensions"]["NV_materials_mdl"]

                self.assertEqual(len(nv_materials_mdl["functionCalls"]), 1)
                call = nv_materials_mdl["functionCalls"][0]
                self.assertEqual(call["functionName"], "OmniSurfaceLite")
                self.assertEqual(call["module"], 0)
                self.assertEqual(call["type"]["typeName"], "material")
                self.assertEqual(len(call["arguments"]), 1)

                argument = call["arguments"][0]
                self.assertEqual(argument["name"], "diffuse_reflection_color")
                self.assertEqual(argument["type"]["typeName"], "color")
                self.assertEqual(len(argument["value"]), 3)
                for x, y in zip(argument["value"], [0.0, 1.0, 0.0]):
                    self.assertTrue(abs(x - y) < 1e-5)

                self.assertEqual(len(nv_materials_mdl["modules"]), 1)
                mdl_module = nv_materials_mdl["modules"][0]
                self.assertTrue(
                    mdl_module["uri"] == "mdl:/OmniSurfaceLite.mdl" or mdl_module["uri"] == "mdl:///OmniSurfaceLite.mdl"
                )

                if "extensionsRequired" in gltf:
                    self.assertNotIn("NV_materials_mdl", gltf["extensionsRequired"])
                self.assertIn("NV_materials_mdl", gltf["extensionsUsed"])
