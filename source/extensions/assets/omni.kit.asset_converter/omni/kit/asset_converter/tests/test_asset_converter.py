import asyncio
import filecmp
import json
import os
import platform
import unittest
from pathlib import Path

import carb.tokens
import omni.kit.asset_converter
import omni.kit.test
from pxr import Sdf, Usd, UsdShade

from ._utils import ENABLE_NEURAYLIB_UTILS, get_test_file_names


# NOTE: those tests belong to omni.kit.asset_converter extension.
class TestAssetConverter(omni.kit.test.AsyncTestCase):
    def get_test_dir(self):
        token = carb.tokens.get_tokens_interface()
        data_dir = token.resolve("${omni_data}")
        test_dir = Path(f"{data_dir}/asset_converter_tests").resolve()
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)
        return str(test_dir)

    async def setUp(self):
        pass

    async def tearDown(self):
        await omni.client.delete_async(self.get_test_dir())

    def progress_callback(self, i: int) -> int:
        print("Progress...", i)
        return i

    async def test_convert_assets_to_usd(self):
        current_path = Path(__file__).parent
        # invalid_mesh.obj includes an invalid mesh that has zero points
        for file in get_test_file_names():
            test_data_path = str(current_path.parent.parent.parent.parent.joinpath("data").joinpath(file))
            converter_manager = omni.kit.asset_converter.get_instance()
            self.assertIsNotNone(converter_manager.create_converter_task)
            context = omni.kit.asset_converter.AssetConverterContext()
            context.keep_all_materials = True
            context.merge_all_meshes = True
            for attr_name in dir(context):
                attr_value = getattr(context, attr_name)
                if isinstance(attr_value, bool):
                    setattr(context, attr_name, True)
            output_path = self.get_test_dir() + "/test.usd"
            task = converter_manager.create_converter_task(test_data_path, output_path, None, context)
            success = await task.wait_until_finished()
            self.assertTrue(success, f"Failed to convert asset {file}.")
            self.assertTrue(Path(output_path).is_file(), f"Failed to convert asset {file}.")
            await omni.client.delete_async(self.get_test_dir())

            # test cancel
            task = converter_manager.create_converter_task(
                "file:/" + test_data_path, "file:/" + output_path, None, context
            )
            task.cancel()
            success = await task.wait_until_finished()
            self.assertFalse(success, f"Failed to convert asset {file}.")
            self.assertFalse(Path(output_path).is_file(), f"Failed to convert asset {file}.")
            await omni.client.delete_async(self.get_test_dir())

    async def test_convert_usd_to_other_formats(self):
        current_path = Path(__file__).parent
        test_data_path = str(current_path.parent.parent.parent.parent.joinpath("data").joinpath("cube.fbx"))
        converter_manager = omni.kit.asset_converter.get_instance()
        context = omni.kit.asset_converter.AssetConverterContext()
        output_path = self.get_test_dir() + "/test.usd"

        # Creates usd firstly
        task = converter_manager.create_converter_task(test_data_path, output_path, self.progress_callback, context)
        success = await task.wait_until_finished()
        self.assertTrue(success)
        self.assertTrue(Path(output_path).is_file())

        for asset_name in [name.replace("cube", "test") for name in get_test_file_names()]:
            asset_path = self.get_test_dir() + f"/{asset_name}"
            context.export_mdl_gltf_extension = True if asset_name == "test_mdl.gltf" else False
            task = converter_manager.create_converter_task(output_path, asset_path, self.progress_callback, context)
            success = await task.wait_until_finished()
            self.assertTrue(success)
            self.assertTrue(Path(asset_path).is_file())

    async def test_convert_assets_to_anonymous_layer(self):
        layer = Sdf.Layer.CreateAnonymous()
        current_path = Path(__file__).parent
        for file in get_test_file_names():
            test_data_path = str(current_path.parent.parent.parent.parent.joinpath("data").joinpath(file))
            converter_manager = omni.kit.asset_converter.get_instance()
            context = omni.kit.asset_converter.AssetConverterContext()
            context.keep_all_materials = True
            context.merge_all_meshes = True
            context.baking_scales = True
            task = converter_manager.create_converter_task(
                test_data_path, layer.identifier, self.progress_callback, context
            )
            success = await task.wait_until_finished()
            self.assertTrue(success, f"Failed to convert asset {file}.")
            await omni.client.delete_async(self.get_test_dir())

    async def test_open_non_usd(self):
        current_path = Path(__file__).parent
        for file in get_test_file_names():
            test_data_path = str(current_path.parent.parent.parent.parent.joinpath("data").joinpath(file))
            self.assertIsNotNone(Usd.Stage.Open(test_data_path))

    async def test_overwrite_opened_stage(self):
        current_path = Path(__file__).parent
        output_path = self.get_test_dir() + "/test.usd"
        opened = False
        for i in range(10):
            test_data_path = str(current_path.parent.parent.parent.parent.joinpath("data").joinpath("cube.fbx"))
            converter_manager = omni.kit.asset_converter.get_instance()
            context = omni.kit.asset_converter.AssetConverterContext()
            task = converter_manager.create_converter_task(
                test_data_path, output_path, self.progress_callback, context, None, True
            )
            success = await task.wait_until_finished()
            self.assertTrue(success, "Failed to convert asset cube.fbx.")
            # For the first round, opening this stage for next overwrite
            if not opened:
                await omni.usd.get_context().open_stage_async(output_path)
                opened = True

        await omni.usd.get_context().close_stage_async()
        await omni.client.delete_async(self.get_test_dir())

    async def test_convert_in_parallel(self):
        current_path = Path(__file__).parent
        converter_manager = omni.kit.asset_converter.get_instance()
        context = omni.kit.asset_converter.AssetConverterContext()

        all_tasks = []
        all_outputs = []
        for i, asset_name in enumerate(get_test_file_names()):
            asset_path = str(current_path.parent.parent.parent.parent.joinpath("data").joinpath(asset_name))
            output_path = self.get_test_dir() + f"/test_{i}.usd"
            all_outputs.append(output_path)
            task = converter_manager.create_converter_task(asset_path, output_path, self.progress_callback, context)
            try:
                from omni.kit.async_engine import run_coroutine

                all_tasks.append(run_coroutine(task.wait_until_finished()))
            except:
                all_tasks.append(asyncio.ensure_future(task.wait_until_finished()))

        results = await asyncio.gather(*all_tasks)
        self.assertEqual(results, [True] * len(get_test_file_names()))

        for path in all_outputs:
            self.assertTrue(Path(path).is_file())
            self.assertTrue(os.stat(path).st_size != 0)

    async def test_unsupported_import_format_rejected_by_native(self):
        """Native converter should reject unsupported source formats (e.g. Revit)."""
        from unittest.mock import patch

        from omni.kit.asset_converter.native_bindings import OmniConverterStatus

        converter_manager = omni.kit.asset_converter.get_instance()
        context = omni.kit.asset_converter.AssetConverterContext()
        output_path = self.get_test_dir() + "/test.usd"

        # Use a real file so native rejection is format-based, not FILE_NOT_EXISTED.
        unsupported_path = self.get_test_dir() + "/model.rvt"
        Path(unsupported_path).write_text("not a real revit file", encoding="utf-8")

        # Expected rejection still emits [Error]; patch so the harness doesn't fail the suite.
        with patch("carb.log_error"):
            task = converter_manager.create_converter_task(
                unsupported_path, output_path, self.progress_callback, context
            )
            success = await task.wait_until_finished()
        self.assertFalse(success)
        self.assertEqual(task.get_status(), OmniConverterStatus.UNSUPPORTED_IMPORT_FORMAT)
        self.assertTrue(task.get_error_message())
        self.assertFalse(Path(output_path).is_file())

    async def test_convert_cancel(self):
        from omni.kit.asset_converter.native_bindings import OmniConverterStatus

        def on_task_done():
            print("Task Completed")

        current_path = Path(__file__).parent
        converter_manager = omni.kit.asset_converter.get_instance()
        context = omni.kit.asset_converter.AssetConverterContext()

        all_tasks = []
        all_outputs = []
        for i, asset_name in enumerate(get_test_file_names()):
            asset_path = str(current_path.parent.parent.parent.parent.joinpath("data").joinpath(asset_name))
            output_path = self.get_test_dir() + f"/test_{i}.usd"
            all_outputs.append(output_path)
            task = converter_manager.create_converter_task(asset_path, output_path, self.progress_callback, context)
            task.add_task_done_callback(on_task_done)
            task.cancel()
            all_tasks.append(asyncio.ensure_future(task.wait_until_finished()))
            task.remove_task_done_callback(on_task_done)
            self.assertEqual(task.get_status(), OmniConverterStatus.OK)

        results = await asyncio.gather(*all_tasks)
        self.assertEqual(results, [False] * len(get_test_file_names()))

    @unittest.skipIf(not ENABLE_NEURAYLIB_UTILS, "Neuraylib version is too old")
    @unittest.skipIf(os.getenv("ETM_ACTIVE"), "skipped in ETM")
    @unittest.skipIf(platform.machine() == "aarch64", "skipped on aarch64")
    async def test_convert_mdl_gltf_extension(self):
        converter_manager = omni.kit.asset_converter.get_instance()
        context = omni.kit.asset_converter.AssetConverterContext()
        context.export_mdl_gltf_extension = True
        context.embed_textures = False

        file = "MDL_to_glTF.usd"
        current_path = Path(__file__).parent
        test_data_path = str(current_path.parent.parent.parent.parent.joinpath("data"))
        input_path = test_data_path + "/" + file
        output_path = self.get_test_dir() + "/gltf/test.gltf"
        reference_file_path = test_data_path + "/references/MDL_to_glTF_reference.gltf"

        task = converter_manager.create_converter_task(input_path, output_path, None, context)
        success = await task.wait_until_finished()
        self.assertTrue(success, f"Failed to convert asset {file}.")
        self.assertTrue(Path(output_path).is_file(), f"Failed to convert asset {file}.")

        # check if all resource files were exported
        def check_dirs(result, prefix=""):
            self.assertFalse(result.right_only, f"Failed to export files: {[prefix + s for s in result.right_only]}")
            for dir_name in result.subdirs:
                check_dirs(result.subdirs[dir_name], prefix + dir_name + "/")

        check_dirs(
            filecmp.dircmp(
                str(Path(output_path).parent),
                str(Path(reference_file_path).parent),
                ignore=["test.gltf", "MDL_to_glTF_reference.gltf", "MDL_to_glTF_reference.usd"],
            )
        )

        # check if the exported glTF is valid
        self._compare_mdl_gltf_extension_json(output_path, reference_file_path)

        # complete the roundtrip by converting the output gltf back to usd
        input_path = output_path
        output_path = self.get_test_dir() + "/usd/test.usd"
        reference_file_path = test_data_path + "/references/MDL_to_glTF_reference.usd"

        task = converter_manager.create_converter_task(input_path, output_path, None, context)
        success = await task.wait_until_finished()
        self.assertTrue(success, f"Failed to convert asset {Path(input_path).name}.")
        self.assertTrue(Path(output_path).is_file(), f"Failed to convert asset {Path(input_path).name}.")

        # check if all resource files were exported
        check_dirs(
            filecmp.dircmp(
                str(Path(output_path).parent),
                str(Path(reference_file_path).parent),
                ignore=["test.usd", "MDL_to_glTF_reference.gltf", "MDL_to_glTF_reference.usd"],
            )
        )

        # check if the exported USD is valid
        stage = Usd.Stage.Open(output_path)
        self.assertIsNotNone(stage)

        reference_stage = Usd.Stage.Open(reference_file_path)
        self._compare_usd_materials(stage, reference_stage)

        await omni.client.delete_async(self.get_test_dir())

    @unittest.skipIf(not ENABLE_NEURAYLIB_UTILS, "Neuraylib version is too old")
    @unittest.skipIf(os.getenv("ETM_ACTIVE"), "skipped in ETM")
    @unittest.skipIf(platform.machine() == "aarch64", "skipped on aarch64")
    async def test_mdl_gltf_extension_module_dependencies(self):
        converter_manager = omni.kit.asset_converter.get_instance()
        context = omni.kit.asset_converter.AssetConverterContext()
        context.export_mdl_gltf_extension = True
        context.embed_textures = False

        # export USD to glTF
        current_path = Path(__file__).parent
        test_data_path = str(current_path.parent.parent.parent.parent.joinpath("data"))
        input_path = test_data_path + "/MDL_module_dependencies.usd"
        output_path = self.get_test_dir() + "/gltf/test.gltf"
        task = converter_manager.create_converter_task(input_path, output_path, None, context)
        success = await task.wait_until_finished()
        self.assertTrue(success, f"Failed to convert asset {input_path}.")
        self.assertTrue(Path(output_path).is_file(), f"Failed to convert asset {input_path}.")

        expected_files = [
            "materials/A.mdl",
            "materials/B.mdl",
            "materials/green.png",
            "materials/C/D/E/E.mdl",
            "materials/C/D/E/white.png",
            "materials/C/F/F.mdl",
            "materials/C/F/tile.1001.png",
            "materials/C/F/tile.1002.png",
            "materials/C/F/tile.1011.png",
            "materials/C/F/tile.1012.png",
        ]
        for file in expected_files:
            path = self.get_test_dir() + "/gltf/" + file
            self.assertTrue(Path(path).is_file(), f"Failed to export {file}.")

        # export glTF to USD
        input_path = output_path
        output_path = self.get_test_dir() + "/usd/test.usd"
        task = converter_manager.create_converter_task(input_path, output_path, None, context)
        success = await task.wait_until_finished()
        self.assertTrue(success, f"Failed to convert asset {input_path}.")
        self.assertTrue(Path(output_path).is_file(), f"Failed to convert asset {input_path}.")

        for file in expected_files:
            path = self.get_test_dir() + "/usd/" + file
            self.assertTrue(Path(path).is_file(), f"Failed to export {file}.")

        await omni.client.delete_async(self.get_test_dir())

    def _compare_mdl_gltf_extension_json(self, output_path, reference_path):
        with open(output_path) as gltf_file, open(reference_path) as reference_file:
            gltf = json.load(gltf_file)
            reference_gltf = json.load(reference_file)

            self.assertIn("extensions", gltf, "Failed to find 'extensions' field.")
            self.assertIn("NV_materials_mdl", gltf["extensions"], "Failed to find 'extensions.NV_materials_mdl' field.")
            nv_materials_mdl = gltf["extensions"]["NV_materials_mdl"]
            nv_materials_mdl_ref = reference_gltf["extensions"]["NV_materials_mdl"]

            # check modules
            self.assertIn("modules", nv_materials_mdl, "Failed to find 'NV_materials_mdl.modules' field.")

            num_modules = len(nv_materials_mdl["modules"])
            expected_num_modules = len(nv_materials_mdl_ref["modules"])
            self.assertEqual(
                expected_num_modules,
                num_modules,
                f"Unexpected amount of modules. Expected {expected_num_modules} but found {num_modules}.",
            )

            expected_module_uris = {module["uri"] for module in nv_materials_mdl_ref["modules"]}
            for module in nv_materials_mdl["modules"]:
                self.assertIn("uri", module, "Failed to find 'uri' field.")
                found = False
                if module["uri"].startswith("mdl:/"):
                    uri = module["uri"].removeprefix("mdl:///").removeprefix("mdl:/")
                    found = ("mdl:/" + uri) in expected_module_uris or ("mdl:///" + uri) in expected_module_uris
                else:
                    uri = module["uri"].removeprefix("./")
                    found = uri in expected_module_uris or ("./" + uri) in expected_module_uris
                self.assertTrue(found, f"Unexpected module {module['uri']} in 'modules'.")

            # check images
            self.assertIn("images", gltf, "Failed to find 'images' field.")

            num_images = len(gltf["images"])
            expected_num_images = len(reference_gltf["images"])
            self.assertEqual(
                num_images,
                expected_num_images,
                f"Unexpected amount of images. Expected {expected_num_images} but found {num_images}.",
            )

            expected_image_uris = {image["uri"] for image in reference_gltf["images"]}
            for image in gltf["images"]:
                self.assertTrue("uri" in image, f"Failed to find 'uri' field.")
                uri = image["uri"].removeprefix("./")
                found = uri in expected_image_uris or ("./" + uri) in expected_image_uris
                self.assertTrue(found, f"Unexpected image {image['uri']} in 'images'.")

            # check function call graph
            self.assertIn("functionCalls", nv_materials_mdl, "Failed to find 'NV_materials_mdl.functionCalls' field.")
            num_calls = len(nv_materials_mdl["functionCalls"])
            expected_num_calls = len(nv_materials_mdl_ref["functionCalls"])
            self.assertEqual(
                num_calls,
                expected_num_calls,
                f"Unexpected amount of function calls. Expected {expected_num_calls} but found {num_calls}.",
            )

            self.assertIn("materials", gltf, "Failed to find 'materials' field.")
            num_materials = len(gltf["materials"])
            expected_num_materials = len(reference_gltf["materials"])
            self.assertEqual(
                num_materials,
                expected_num_materials,
                f"Unexpected amount of modules. Expected {expected_num_materials} but found {num_materials}.",
            )

            def check_gltf_object(gltf_object, expected):
                for key in expected:
                    self.assertIn(key, gltf_object, f"Failed to find '{key}' field.")
                    value = gltf_object[key]
                    expected_value = expected[key]

                    if key == "functionCall":
                        call = nv_materials_mdl["functionCalls"][value]
                        expected_call = nv_materials_mdl_ref["functionCalls"][expected_value]
                        check_gltf_object(call, expected_call)
                    elif key == "module":
                        module = nv_materials_mdl["modules"][value]
                        expected_module = nv_materials_mdl_ref["modules"][expected_value]

                        if expected_module["uri"].startswith("mdl:/"):
                            self.assertTrue(module["uri"].startswith("mdl:/"))
                            self.assertEqual(
                                module["uri"].removeprefix("mdl:///").removeprefix("mdl:/"),
                                expected_module["uri"].removeprefix("mdl:///").removeprefix("mdl:/"),
                            )
                        else:
                            self.assertEqual(
                                module["uri"].removeprefix("./"), expected_module["uri"].removeprefix("./")
                            )
                    elif key == "arguments":
                        self.assertEqual(
                            len(value),
                            len(expected_value),
                            f"Unexpected amount of arguments. Expected {len(expected_value)} but found {len(value)}.",
                        )

                        expected_arguments = {arg["name"]: arg for arg in expected_value}
                        for argument in value:
                            self.assertIn(
                                argument["name"], expected_arguments, f"Unexpected argument '{argument['name']}' found."
                            )
                            check_gltf_object(argument, expected_arguments[argument["name"]])
                    elif key == "value" and gltf_object.get("name") == "name":
                        # special case for image index
                        image = gltf["images"][value]
                        expected_image = reference_gltf["images"][expected_value]
                        self.assertEqual(image["uri"].removeprefix("./"), expected_image["uri"].removeprefix("./"))
                    elif isinstance(expected_value, dict):
                        check_gltf_object(value, expected_value)
                    elif isinstance(expected_value, list):
                        for x, y in zip(value, expected_value):
                            self.assertTrue(abs(x - y) < 1e-5) if isinstance(value, float) else self.assertEqual(x, y)
                    elif isinstance(expected_value, float):
                        self.assertTrue(abs(value - expected_value) < 1e-5)
                    else:
                        self.assertEqual(value, expected_value)

            expected_materials = {material["name"]: material for material in reference_gltf["materials"]}
            for material in gltf["materials"]:
                self.assertIn(material["name"], expected_materials, f"Unexpected material {material['name']} found.")
                self.assertIn("extensions", material, "Failed to find 'extensions' field.")
                self.assertIn("NV_materials_mdl", material["extensions"], "Failed to find 'NV_materials_mdl' field.")
                self.assertIn(
                    "functionCall", material["extensions"]["NV_materials_mdl"], "Failed to find 'functionCall' field."
                )

                call_index = material["extensions"]["NV_materials_mdl"]["functionCall"]
                reference_call_index = expected_materials[material["name"]]["extensions"]["NV_materials_mdl"][
                    "functionCall"
                ]

                root_call = nv_materials_mdl["functionCalls"][call_index]
                expected_root_call = nv_materials_mdl_ref["functionCalls"][reference_call_index]
                check_gltf_object(root_call, expected_root_call)

            # check extensionsUsed/extensionsRequired
            self.assertIn("extensionsUsed", gltf, "Failed to find 'extensionsUsed' field.")
            self.assertIn("extensionsRequired", gltf, "Failed to find 'extensionsUsed' field.")
            self.assertEqual(
                "NV_materials_mdl" in gltf["extensionsUsed"], "NV_materials_mdl" in reference_gltf["extensionsUsed"]
            )
            self.assertEqual(
                "NV_materials_mdl" in gltf["extensionsRequired"],
                "NV_materials_mdl" in reference_gltf["extensionsRequired"],
            )

    def _compare_usd_materials(self, stage, reference_stage):
        def compare_usd_values(a, b):
            value_a = a.Get()
            value_b = b.Get()

            if isinstance(value_b, Sdf.AssetPath):
                self.assertEqual(value_a.path, value_b.path)
            elif isinstance(value_b, list):
                self.assertEqual(len(value_a), len(value_b))
                if len(value_b) > 0 and isinstance(value_b[0], float):
                    for item_a, item_b in zip(value_a, value_b):
                        self.assertTrue(abs(item_a - item_b) < 1e-5)
                else:
                    for item_a, item_b in zip(value_a, value_b):
                        self.assertEqual(item_a, item_b)
            elif isinstance(value_b, float):
                self.assertTrue(abs(value_a - value_b) < 1e-5)
            else:
                self.assertEqual(value_a, value_b)

        def compare_usd_connections(connections_a, connections_b):
            usd_connections_a = {connection.GetFullName(): connection for connection in connections_a}
            usd_connections_b = {connection.GetFullName(): connection for connection in connections_b}

            names_a = set(usd_connections_a.keys())
            names_b = set(usd_connections_b.keys())
            missing_names = names_b - names_a
            self.assertFalse(missing_names, f"Connections are missing: {missing_names}")
            self.assertEqual(len(names_a), len(names_b))

            for name in names_a:
                usd_connection_a = usd_connections_a[name]
                usd_connection_b = usd_connections_b[name]

                self.assertEqual(usd_connection_a.GetTypeName(), usd_connection_b.GetTypeName())
                self.assertEqual(usd_connection_a.GetAttr().GetColorSpace(), usd_connection_b.GetAttr().GetColorSpace())
                if UsdShade.Input.IsInput(usd_connection_a.GetAttr()):
                    compare_usd_values(usd_connection_a, usd_connection_b)

                self.assertEqual(usd_connection_a.HasConnectedSource(), usd_connection_b.HasConnectedSource())
                if usd_connection_a.HasConnectedSource():
                    source_a, source_name_a, source_type_a = usd_connection_a.GetConnectedSource()
                    source_b, source_name_b, source_type_b = usd_connection_b.GetConnectedSource()
                    self.assertEqual(source_name_a, source_name_b)
                    self.assertEqual(source_type_a, source_type_b)
                    compare_usd_connectable_api(source_a, source_b)

        def compare_usd_connectable_api(connectable_a, connectable_b):
            self.assertEqual(connectable_a.GetPrim().IsA(UsdShade.Shader), connectable_b.GetPrim().IsA(UsdShade.Shader))
            if connectable_a.GetPrim().IsA(UsdShade.Shader):
                shader_a = UsdShade.Shader(connectable_a)
                shader_b = UsdShade.Shader(connectable_b)

                self.assertEqual(shader_a.GetImplementationSource(), shader_b.GetImplementationSource())
                self.assertEqual(shader_a.GetSourceAsset("mdl").path, shader_b.GetSourceAsset("mdl").path)
                self.assertEqual(
                    shader_a.GetSourceAssetSubIdentifier("mdl"), shader_b.GetSourceAssetSubIdentifier("mdl")
                )

            compare_usd_connections(connectable_a.GetInputs(), connectable_b.GetInputs())
            compare_usd_connections(connectable_a.GetOutputs(), connectable_b.GetOutputs())

        materials = {
            prim.GetName(): UsdShade.Material(prim) for prim in stage.Traverse() if prim.IsA(UsdShade.Material)
        }
        expected_materials = {
            prim.GetName(): UsdShade.Material(prim)
            for prim in reference_stage.Traverse()
            if prim.IsA(UsdShade.Material)
        }

        names = set(materials.keys())
        expected_names = set(expected_materials.keys())
        missing_names = expected_names - names
        self.assertFalse(missing_names, f"Materials are missing: {missing_names}")
        self.assertEqual(len(names), len(expected_names))

        for name in materials:
            compare_usd_connectable_api(materials[name], expected_materials[name])

    @unittest.skipIf(platform.machine() == "aarch64", "skipped on aarch64")
    async def test_fbx_animation(self):
        # ensure fbx animation conversion has time samples in the output
        # this test was added to catch regressions like the conflict we had when introducing mimalloc in kit-kernel
        current_path = Path(__file__).parent
        test_data_path = str(current_path.parent.parent.parent.parent.joinpath("data").joinpath("box.fbx"))
        output_path = self.get_test_dir() + "/usd/test.usd"

        converter_manager = omni.kit.asset_converter.get_instance()
        context = omni.kit.asset_converter.AssetConverterContext()

        task = converter_manager.create_converter_task(test_data_path, output_path, None, context)
        success = await task.wait_until_finished()
        self.assertTrue(success, f"Failed to convert asset {test_data_path}.")
        self.assertTrue(Path(output_path).is_file(), f"Failed to convert asset {test_data_path}.")

        stage = Usd.Stage.Open(output_path)
        self.assertIsNotNone(stage)

        # Check for the xform prim at /World/Box001
        prim = stage.GetPrimAtPath("/World/Box001")
        self.assertTrue(prim.IsValid())

        # Verify that the translate attribute has timeSamples
        translate_attr = prim.GetAttribute("xformOp:translate")
        self.assertTrue(translate_attr.IsValid())

        num_translate_time_samples = translate_attr.GetNumTimeSamples()
        self.assertGreater(num_translate_time_samples, 0, "xformOp:translate on /World/Box001 has no timeSamples.")
        await omni.client.delete_async(self.get_test_dir())
