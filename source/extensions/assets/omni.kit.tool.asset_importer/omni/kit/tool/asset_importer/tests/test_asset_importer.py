import asyncio
import os
import shutil
import unittest
from pathlib import Path
from typing import Dict, List, Union
from unittest.mock import Mock, patch

import carb
import carb.tokens
import omni.client
import omni.kit.app
import omni.kit.test
import omni.kit.tool.asset_importer as ai
import omni.kit.tool.asset_importer.utils as importer_utils
import omni.ui as ui
import omni.usd
from pxr import Usd

DATA_PATH = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)).joinpath("data")
PERSISTENT_APP_IMPORT_SETTINGS_PATH = (
    "/persistent/app/stage/dragDropImport"  # Simulate the Preferences>Stage>Import settings.
)

# Kit temporary directory - deleted after Kit is finished running
token = carb.tokens.get_tokens_interface()
kit_temp_directory = token.resolve("${temp}")


class CustomAssetImporter(ai.AbstractImporterDelegate):
    def __init__(self, name, filters, descriptions, supports_usd_stage_cache=False) -> None:
        self._name = name
        self._filters = filters
        self._descriptions = descriptions
        self._supports_usd_stage_cache = supports_usd_stage_cache

    @property
    def name(self) -> str:
        return self._name

    @property
    def filter_regexes(self) -> List[str]:
        return self._filters

    @property
    def filter_descriptions(self) -> List[str]:
        return self._descriptions

    def build_options(self, paths: List[str]) -> None:
        with ui.VStack():
            ui.Label("test option")

        return True

    async def convert_assets(self, paths: List[str]) -> Dict[str, Union[str, None]]:
        return []

    def supports_usd_stage_cache(self):
        return self._supports_usd_stage_cache


class TestAssetImporter(omni.kit.test.AsyncTestCase):
    def get_test_dir(self):
        token = carb.tokens.get_tokens_interface()
        data_dir = token.resolve("${omni_data}")

        return f"{data_dir}/asset_importer_tests"

    async def setUp(self):
        test_data_dir = Path(self.get_test_dir()) / "test_data"
        await omni.client.create_folder_async(str(test_data_dir))
        for file in ["cu be.fbx", "cube.bin", "cube.fbx", "cube.gltf", "airplane.ply"]:
            test_src_data = omni.client.normalize_url(str(DATA_PATH / file))
            result = await omni.client.copy_async(test_src_data, str(test_data_dir / file))
            self.assertEqual(result, omni.client.Result.OK)

        self.data_path = DATA_PATH
        self.test_data_dir = test_data_dir
        await omni.usd.get_context().new_stage_async()

        # store permanent user settings in case tests run inside an app
        _settings = carb.settings.get_settings()
        self._user_dragDropImport = _settings.get_as_string(PERSISTENT_APP_IMPORT_SETTINGS_PATH)

    async def tearDown(self):
        # New stage to make sure all holding handles will be released.
        await omni.usd.get_context().new_stage_async()
        await omni.client.delete_async(self.get_test_dir())
        await omni.client.delete_async(str(self.data_path.joinpath("cube")))
        await omni.client.delete_async(str(self.data_path.joinpath("cube.usd")))

        # restore permanent user settings to original in case tests run inside an app
        if self._user_dragDropImport:
            _settings = carb.settings.get_settings()
            _settings.set_string(PERSISTENT_APP_IMPORT_SETTINGS_PATH, self._user_dragDropImport)

    async def test_saved_directory(self):
        importer = ai.AssetImporterExtension.get_instance()
        settings = carb.settings.get_settings()
        default_settings_path = settings.get_as_string("/exts/omni.kit.tool.asset_importer/appSettings")
        directory_ori = settings.get_as_string(f"{default_settings_path}/directory")
        settings.set(f"{default_settings_path}/directory", "omniverse:/test")
        all_asset_paths = []
        for file in ["cube.fbx", "cube.gltf"]:
            test_data_path = str(self.test_data_dir.joinpath(file))
            all_asset_paths.append(test_data_path)

        importer._on_menu_convert_click(True, False)
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        importer._converter_file_picker._on_file_open(all_asset_paths)
        await asyncio.sleep(5.0)
        importer._converter_file_picker.destroy()

        importer._on_menu_convert_click(False, True)
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        importer._converter_file_picker._on_file_open(all_asset_paths)
        await asyncio.sleep(5.0)
        importer._converter_file_picker.destroy()

        directory = settings.get_as_string(f"{default_settings_path}/directory")
        settings.set(f"{default_settings_path}/directory", directory_ori)
        self.assertTrue(os.path.samefile(directory, self.test_data_dir))

    async def test_api(self):
        i1 = CustomAssetImporter("test importer 1", [".*\\.custom1$"], ["custom1"])
        i2 = CustomAssetImporter("test importer 2", [".*\\.custom2$", ".*\\.custom3"], ["custom2", "custom3"])

        self.assertFalse(ai.is_supported_format("omniverse://bcd/test.custom1"))
        self.assertFalse(ai.is_supported_format("omniverse://bcd/test.custom2"))
        self.assertFalse(ai.is_supported_format("omniverse://bcd/test.custom3"))
        ai.register_importer(i1)
        ai.register_importer(i2)
        self.assertTrue(ai.is_supported_format("omniverse://bcd/test.custom1"))
        self.assertTrue(ai.is_supported_format("omniverse://bcd/test.custom2"))
        self.assertTrue(ai.is_supported_format("omniverse://bcd/test.custom3"))

        def mock_is_folder(path):
            return True

        # OMPE-39242: should not support folder
        with patch.object(importer_utils.Utils, "is_folder", side_effect=mock_is_folder):
            self.assertFalse(ai.is_supported_format("omniverse://bcd/test.custom1"))
            self.assertFalse(ai.is_supported_format("omniverse://bcd/test.custom2"))
            self.assertFalse(ai.is_supported_format("omniverse://bcd/test.custom3"))

        ai.remove_importer(i1)
        self.assertFalse(ai.is_supported_format("omniverse://bcd/test.custom1"))
        self.assertTrue(ai.is_supported_format("omniverse://bcd/test.custom2"))
        self.assertTrue(ai.is_supported_format("omniverse://bcd/test.custom3"))
        ai.remove_importer(i2)
        self.assertFalse(ai.is_supported_format("omniverse://bcd/test.custom1"))
        self.assertFalse(ai.is_supported_format("omniverse://bcd/test.custom2"))
        self.assertFalse(ai.is_supported_format("omniverse://bcd/test.custom3"))
        self.assertFalse(ai.is_supported_format("omniverse://bcd/test.custom3?abc=1&bcd=2"))

    async def test_file_import_with_context_menu(self):
        # get file from content window
        import omni.kit.ui_test as ui_test
        from omni.kit.window.content_browser.test_helper import ContentBrowserTestHelper

        test_ouput_dir = Path(omni.kit.test.get_test_output_path()) / "test_file_import_with_context_menu"
        if os.path.exists(test_ouput_dir):
            shutil.rmtree(test_ouput_dir)

        await omni.client.create_folder_async(str(test_ouput_dir))
        test_file = "cube.fbx"
        test_src_data = omni.client.normalize_url(str(self.data_path / test_file))
        result = await omni.client.copy_async(test_src_data, str(test_ouput_dir / test_file))
        self.assertEqual(result, omni.client.Result.OK)
        test_data = test_ouput_dir / test_file
        self.assertTrue(os.path.isfile(test_data))

        async with ContentBrowserTestHelper() as content_browser_helper:
            test_ouput_dir = str(Path(test_ouput_dir).resolve())
            await content_browser_helper.navigate_to_async(test_ouput_dir)
            # Mock the context menu click as there is no better way to do that.
            importer = ai.AssetImporterExtension.get_instance()
            importer._on_menu_convert_click()
            file_picker = ui_test.find("Select File")
            self.assertTrue(file_picker)

            importer._converter_file_picker._on_selection_changed(str(test_data))
            importer._converter_file_picker.set_current_filename(str(test_data))

            importer._on_menu_convert_click(False, True)
            await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()

            importer._converter_file_picker._on_file_open([str(test_data)])

            # 2s is enough for all files to be imported
            await asyncio.sleep(2.0)
            target_absolute_paths, _ = await importer_utils.Utils.list_folder_async(test_ouput_dir)

            target_absolute_filenames = [os.path.basename(path) for path in target_absolute_paths]
            self.assertListEqual(
                sorted(target_absolute_filenames),
                ["cube.fbx", "cube.usd"],
                msg=f"Expected files from {test_ouput_dir} not found.",
            )
            importer._converter_file_picker.destroy()

    async def test_file_upload_with_context_menu(self):
        # get file from content window
        import omni.kit.ui_test as ui_test
        from omni.kit.window.content_browser.test_helper import ContentBrowserTestHelper

        temp_directory = kit_temp_directory + "/test_file_upload_with_context_menu"
        os.mkdir(temp_directory)

        async with ContentBrowserTestHelper() as content_browser_helper:
            temp_directory = str(Path(temp_directory).resolve())
            await content_browser_helper.navigate_to_async(temp_directory)
            test_data_dir = omni.client.normalize_url(str(self.test_data_dir))

            # Mock the context menu click as there is no better way to do that.
            importer = ai.AssetImporterExtension.get_instance()
            importer._on_menu_upload_click()

            await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()

            file_picker = ui_test.find("Select Files or Folder")
            await file_picker.focus()
            self.assertTrue(file_picker)

            import_button = file_picker.find("**/Button[*].text=='Import'")
            self.assertTrue(import_button)
            self.assertFalse(import_button.widget.enabled)

            # FIXME: It seems not a stable way to find the input field for file picker.
            input_field = file_picker.find("**/StringField[*].style_type_name_override=='Field'")
            await input_field.input(test_data_dir, human_delay_speed=20)
            self.assertTrue(import_button.widget.enabled)

            importer._upload_file_picker._on_file_open([test_data_dir + "/"])

            # 2s is enough for all files to be uploaded
            await asyncio.sleep(2.0)
            source_absolute_paths, _ = await importer_utils.Utils.list_folder_async(test_data_dir)
            source_absolute_filenames = [os.path.basename(path) for path in source_absolute_paths]
            target_absolute_paths, _ = await importer_utils.Utils.list_folder_async(temp_directory)
            target_absolute_filenames = [os.path.basename(path) for path in target_absolute_paths]

            self.assertEqual(source_absolute_filenames.sort(), target_absolute_filenames.sort())

    async def test_file_import(self):
        importer = ai.AssetImporterExtension.get_instance()

        all_imported_asset_paths = []

        def imported_callback(file_paths):
            nonlocal all_imported_asset_paths
            all_imported_asset_paths.extend(file_paths)
            self.assertEqual(all_asset_paths, all_imported_asset_paths)

        importer.add_import_complete_callback(imported_callback)

        all_asset_paths = []
        # airplane.ply downloaded from https://people.sc.fsu.edu/~jburkardt/data/ply/ply.html
        for file in ["cube.fbx", "cube.gltf", "airplane.ply"]:
            test_data_path = str(self.data_path.joinpath(file))
            all_asset_paths.append(test_data_path)

        importer._on_menu_convert_click(False, True)
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

        importer._converter_file_picker._on_file_open(all_asset_paths)

        # 5s is enough to import 3 small files

        await asyncio.sleep(5.0)
        importer.remove_import_complete_callback(imported_callback)

        stage = omni.usd.get_context().get_stage()
        self.assertIsNotNone(stage.GetPrimAtPath("/cube"))
        self.assertIsNotNone(stage.GetPrimAtPath("/cube_01"))
        self.assertIsNotNone(stage.GetPrimAtPath("/airplane"))
        importer._converter_file_picker.destroy()

    async def test_drag_drop_support_filters_and_schedules_import(self):
        from omni.kit.tool.asset_importer.drag_drop import AssetImporterDragDropSupport

        class FakeImportersManager:
            def get_all_filters(self):
                return [".*\\.custom$", "(.*\\.foo$)|(.*\\.bar$)", ".*\\.usd$"], []

        class FakeImporterExtension:
            def __init__(self):
                self._importers_manager = FakeImportersManager()
                self._import_paths_async = Mock(return_value=asyncio.Future())

            def is_supported_format(self, path: str):
                return path.endswith(".custom")

        support = AssetImporterDragDropSupport.__new__(AssetImporterDragDropSupport)
        support._importer_ext = FakeImporterExtension()
        target_item = Mock()
        target_item.path = "/World"

        self.assertTrue(support._accept_stage_drop("C:/Assets/part.custom", target_item))
        self.assertFalse(support._accept_stage_drop("C:/Assets/part.txt", target_item))
        self.assertListEqual(
            sorted(support._get_supported_extensions()),
            [".bar", ".custom", ".foo"],
        )

        with patch("omni.kit.tool.asset_importer.drag_drop.asyncio.ensure_future") as ensure_future:
            self.assertTrue(support._drop_stage("C:/Assets/part.custom", target_item))
            support._importer_ext._import_paths_async.assert_called_once_with(
                ["C:/Assets/part.custom"],
                add_reference=True,
                parent_path="/World",
                use_default_options=True,
            )
            ensure_future.assert_called_once_with(support._importer_ext._import_paths_async.return_value)

    async def test_file_import_reference(self):
        """Test converting a USD and adding this external USD as a reference."""
        # set (persistent) value for this tests, need to simulate app/stage/dragDropImport behavior.
        settings = carb.settings.get_settings()
        settings.set_string(PERSISTENT_APP_IMPORT_SETTINGS_PATH, "reference")

        importer = ai.AssetImporterExtension.get_instance()

        all_imported_asset_paths = []

        def imported_callback(file_paths):
            nonlocal all_imported_asset_paths
            all_imported_asset_paths.extend(file_paths)
            self.assertEqual(all_asset_paths, all_imported_asset_paths)

        importer.add_import_complete_callback(imported_callback)

        all_asset_paths = []

        for file in ["cube.fbx", "cube.gltf", "cube.bin"]:
            test_src_data = omni.client.normalize_url(str(self.test_data_dir / file))
            if file != "cube.bin":
                all_asset_paths.append(test_src_data)

        importer._on_menu_convert_click(True, False)
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

        importer._converter_file_picker._on_file_open(all_asset_paths)

        # 5s is enough to import 2 small files
        await asyncio.sleep(5.0)
        importer.remove_import_complete_callback(imported_callback)

        # run checks after the file conversion is done.
        stage = omni.usd.get_context().get_stage()
        cube_prim = stage.GetPrimAtPath("/cube")
        self.assertIsNotNone(cube_prim)
        # this tests expected to have refereces ONLY - payloads should be [].
        payloads = omni.usd.get_composed_payloads_from_prim(cube_prim)
        self.assertListEqual(payloads, [])
        # There should only be 1 ref path.
        references = omni.usd.get_composed_references_from_prim(cube_prim)
        self.assertEqual(len(references), 1)
        ref, layer = references[0]
        usd_file_path = layer.ComputeAbsolutePath(ref.assetPath)
        # verify the converted asset path.
        result, _ = await omni.client.stat_async(usd_file_path)
        self.assertEqual(result, omni.client.Result.OK)
        self.assertIsNotNone(stage.GetPrimAtPath("/cube_01"))

        importer._converter_file_picker.destroy()

    async def test_file_import_bogus(self):
        """Test bogus/corrupted user setting, should behave the same as test_file_import_reference."""
        # set (persistent) value for this tests, need to simulate app/stage/dragDropImport behavior.
        settings = carb.settings.get_settings()
        settings.set_string(PERSISTENT_APP_IMPORT_SETTINGS_PATH, "bogus")

        importer = ai.AssetImporterExtension.get_instance()

        all_imported_asset_paths = []

        def imported_callback(file_paths):
            nonlocal all_imported_asset_paths
            all_imported_asset_paths.extend(file_paths)
            self.assertEqual(all_asset_paths, all_imported_asset_paths)

        importer.add_import_complete_callback(imported_callback)

        all_asset_paths = []

        for file in ["cube.fbx", "cube.gltf", "cube.bin"]:
            test_src_data = omni.client.normalize_url(str(self.test_data_dir / file))
            if file != "cube.bin":
                all_asset_paths.append(test_src_data)

        importer._on_menu_convert_click(True, False)
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

        importer._converter_file_picker._on_file_open(all_asset_paths)

        # 5s is enough to import 2 small files
        await asyncio.sleep(5.0)
        importer.remove_import_complete_callback(imported_callback)

        # run checks after the file conversion is done.
        stage = omni.usd.get_context().get_stage()
        cube_prim = stage.GetPrimAtPath("/cube")
        self.assertIsNotNone(cube_prim)
        # this tests expected to have refereces ONLY - payloads should be [].
        payloads = omni.usd.get_composed_payloads_from_prim(cube_prim)
        self.assertListEqual(payloads, [])
        # There should only be 1 ref path.
        references = omni.usd.get_composed_references_from_prim(cube_prim)
        self.assertEqual(len(references), 1)
        ref, layer = references[0]
        usd_file_path = layer.ComputeAbsolutePath(ref.assetPath)
        # verify the converted asset path.
        result, _ = await omni.client.stat_async(usd_file_path)
        self.assertEqual(result, omni.client.Result.OK)

        self.assertIsNotNone(stage.GetPrimAtPath("/cube_01"))

        importer._converter_file_picker.destroy()

    async def test_file_import_payload(self):
        """Test converting a USD and adding this external USD as a payload."""
        # set (persistent) value for this tests, need to simulate app/stage/dragDropImport behavior.
        settings = carb.settings.get_settings()
        settings.set_string(PERSISTENT_APP_IMPORT_SETTINGS_PATH, "payload")

        importer = ai.AssetImporterExtension.get_instance()

        all_imported_asset_paths = []

        def imported_callback(file_paths):
            nonlocal all_imported_asset_paths
            all_imported_asset_paths.extend(file_paths)
            self.assertEqual(all_asset_paths, all_imported_asset_paths)

        importer.add_import_complete_callback(imported_callback)
        all_asset_paths = []

        for file in ["cube.fbx", "cube.gltf", "cube.bin"]:
            test_src_data = omni.client.normalize_url(str(self.test_data_dir / file))
            if file != "cube.bin":
                all_asset_paths.append(test_src_data)

        importer._on_menu_convert_click(True, False)
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

        importer._converter_file_picker._on_file_open(all_asset_paths)

        # 5s is enough to import 2 small files
        await asyncio.sleep(5.0)
        importer.remove_import_complete_callback(imported_callback)

        # run checks after the file conversion is done.
        stage = omni.usd.get_context().get_stage()
        cube_prim = stage.GetPrimAtPath("/cube")
        self.assertIsNotNone(cube_prim)
        # There should only be 1 payload path.
        payloads = omni.usd.get_composed_payloads_from_prim(cube_prim)
        self.assertEqual(len(payloads), 1)
        pyld, layer = payloads[0]
        usd_file_path = layer.ComputeAbsolutePath(pyld.assetPath)
        # verify the converted asset path.
        result, _ = await omni.client.stat_async(usd_file_path)
        self.assertEqual(result, omni.client.Result.OK)

        references = omni.usd.get_composed_references_from_prim(cube_prim)
        # this tests expected to have payloads ONLY - references should be [].
        self.assertListEqual(references, [])

        self.assertIsNotNone(stage.GetPrimAtPath("/cube_01"))

        importer._converter_file_picker.destroy()

    async def _test_ui_import_internal(self, right_click_menu):
        from omni.kit.window.content_browser.test_helper import ContentBrowserTestHelper

        importer = ai.AssetImporterExtension.get_instance()
        test_data_path = omni.client.normalize_url(str(self.test_data_dir.joinpath("cube.fbx")))
        all_imported_asset_paths = []

        def imported_callback(file_paths):
            nonlocal all_imported_asset_paths
            all_imported_asset_paths.extend(file_paths)

            expected_path = omni.client.normalize_url(all_imported_asset_paths[0])
            self.assertTrue(len(all_imported_asset_paths), 1)
            self.maxDiff = None
            self.assertEqual(expected_path.lower(), test_data_path.lower())

            # verify output file name is cube1.usdz
            self.assertTrue(os.path.exists(str(self.test_data_dir.joinpath("cube1.usdz"))))

        importer.add_import_complete_callback(imported_callback)

        import omni.kit.ui_test as ui_test

        await ui_test.find("Content").focus()
        await asyncio.sleep(2.0)

        # get file from content window
        async with ContentBrowserTestHelper() as content_browser_helper:
            await content_browser_helper.navigate_to_async(str(self.test_data_dir))
            await asyncio.sleep(1.0)
            await content_browser_helper.select_items_async(str(self.test_data_dir), ["cube.fbx"])
            await asyncio.sleep(1.0)
            fbx_item = await content_browser_helper.get_gridview_item_async("cube.fbx")
            self.assertTrue(fbx_item)

            if right_click_menu:
                await fbx_item.right_click()
                await ui_test.select_context_menu("Convert to USD")
            else:
                # convert options panel would show up upon double click with Kit 107
                await fbx_item.double_click()

            import_options_window = ui_test.find("Convert Options")
            self.assertTrue(import_options_window)

            # file name defaults to the input file name without the extension on single file selection
            file_name_field = import_options_window.find("**/StringField[*].name=='file_name'")
            self.assertTrue(file_name_field)
            self.assertEqual(file_name_field.model.as_string, "cube")

            # verify file format combobox exists and defaults to index 0 (.usd)
            file_format_combobox = import_options_window.find("**/ComboBox[*].name=='file_format'")
            self.assertTrue(file_format_combobox)
            self.assertEqual(file_format_combobox.model.get_item_value_model().as_int, 0)

            # specify file name and format so that the output file name is cube1.usdz
            file_name_field.model.set_value("cube1")
            file_format_combobox.model.get_item_value_model().set_value(3)

            confirm_button = import_options_window.find("**/Button[*].text=='Convert'")
            await confirm_button.click()

            # 3s is enough to import a small file.
            await asyncio.sleep(3.0)
            await omni.kit.app.get_app().next_update_async()
            importer.remove_import_complete_callback(imported_callback)

    async def test_ui_import_from_menu(self):
        await self._test_ui_import_internal(True)

    async def test_import_by_ui_double_click(self):
        await self._test_ui_import_internal(False)

    async def test_ui_invalid_path(self):
        importer = ai.AssetImporterExtension.get_instance()
        import omni.kit.ui_test as ui_test

        importer._on_menu_convert_click()
        file_picker = ui_test.find("Select File")
        self.assertTrue(file_picker)

        # set current directory
        importer._converter_file_picker._ui_handler._file_picker._filepicker.set_current_directory(
            self.data_path.as_posix()
        )
        # import_button = file_picker.find("**/Button[*].text=='Convert'")

        # check that import button is disabled for invalid path
        invalid_path = self.data_path / "cube_invalid.fbx"

        # OM-78341: Disable apply button if no file is selected
        # this method is only available in more recent Kit 105
        importer._converter_file_picker._ui_handler._file_picker._on_filename_changed("cube_invalid.fbx")

        apply_button = (
            importer._converter_file_picker._ui_handler._file_picker._filepicker._widget.file_bar._apply_button
        )

        await omni.kit.app.get_app().next_update_async()
        self.assertFalse(invalid_path.is_file())
        self.assertFalse(
            apply_button.enabled, msg=f"Import button should be disabled with invalid filename in folder {invalid_path}"
        )

        # check that import button is enabled for valid path
        importer._converter_file_picker._ui_handler._file_picker._on_filename_changed("cube.fbx")
        await omni.kit.app.get_app().next_update_async()
        valid_path = self.data_path / "cube.fbx"
        self.assertTrue(valid_path.is_file())
        self.assertTrue(apply_button.enabled, msg=f"Import button should be enabled with valid path {valid_path}")

        importer._converter_file_picker.destroy()

    async def test_ui_space_path(self):
        importer = ai.AssetImporterExtension.get_instance()
        import omni.kit.ui_test as ui_test

        importer._on_menu_convert_click()
        file_picker = ui_test.find("Select File")
        self.assertTrue(file_picker)
        # set current directory
        importer._converter_file_picker._ui_handler._file_picker._filepicker.set_current_directory(
            self.data_path.as_posix()
        )

        apply_button = (
            importer._converter_file_picker._ui_handler._file_picker._filepicker._widget.file_bar._apply_button
        )
        # check that import button is enabled for valid path
        importer._converter_file_picker._ui_handler._file_picker._on_filename_changed("cu be.fbx")
        await omni.kit.app.get_app().next_update_async()
        self.assertTrue(apply_button.enabled)
        mock_handler = Mock()

        def mock(file_list):
            mock_handler()
            # OMFP-3129: filepicker should not return local paths with %20 instead of space
            self.assertTrue(file_list[0].find("%20") == -1)

        with patch.object(
            importer._converter_file_picker._ui_handler._file_picker, "_custom_select_fn", side_effect=mock
        ):
            importer._converter_file_picker._ui_handler._file_picker._on_click_open(self.data_path, "cu be.fbx")
            mock_handler.assert_called_once()

        importer._converter_file_picker.destroy()

    async def test_import_action(self):
        import omni.kit.actions.core

        action_registry = omni.kit.actions.core.get_action_registry()
        extension_id = omni.kit.app.get_app().get_extension_manager().get_extension_id_by_module(__name__)
        extension_name = omni.ext.get_extension_name(extension_id)

        # test that the import action becomes unavailable when the extension is disabled/shutdown
        importer = ai.AssetImporterExtension.get_instance()
        importer.on_shutdown()
        actions = action_registry.get_all_actions_for_extension(extension_name)
        self.assertEqual(len(actions), 0)

        # test that the import action is available in the action registry when the extension is enabled
        importer.on_startup(extension_id)
        actions = action_registry.get_all_actions_for_extension(extension_name)
        self.assertEqual(len(actions), 2)
        import_action = action_registry.get_action(extension_name, "import")
        self.assertIsNotNone(import_action, None)

        # test out the import action and close the file picker dialog afterwards
        import_action.execute()
        importer = ai.AssetImporterExtension.get_instance()
        importer._converter_file_picker.destroy()

    async def test_shared_options(self):
        """Test state of shared options for importers w/ and wo/ UsdStageCache support"""
        import omni.kit.ui_test as ui_test
        from omni.kit.window.content_browser.test_helper import ContentBrowserTestHelper

        await ui_test.find("Content").focus()
        await omni.kit.app.get_app().next_update_async()

        async def check_option(content_browser_helper, file_name, supports_stage_cache):
            temp_importer = CustomAssetImporter("test importer 3", [".*\\.bin$"], ["bin"], supports_stage_cache)
            ai.register_importer(temp_importer)

            # select the file to check its available options
            await content_browser_helper.select_items_async(str(self.data_path), [file_name])
            item = await content_browser_helper.get_gridview_item_async(file_name)
            self.assertTrue(item)

            await omni.kit.app.get_app().next_update_async()

            # open context menu and pick 'Convert to USD' option
            await item.right_click()
            await ui_test.select_context_menu("Convert to USD")
            import_options_window = ui_test.find("Convert Options")
            self.assertTrue(import_options_window)

            await omni.kit.app.get_app().next_update_async()

            # verify there are no advanced options via "Convert-to-USD" workflow
            label = import_options_window.find("**/Label[*].text=='Import to Stage'")
            if supports_stage_cache:
                self.assertIsNone(label)

                # test opening and closing output folder selection window
                folder_button = import_options_window.find("**/Button[*].name=='dest_folder'")
                self.assertTrue(folder_button)
                await folder_button.click()
                await omni.kit.app.get_app().next_update_async()
                folder_picker = ui_test.find("Select Folder")
                self.assertTrue(folder_picker)
                folder_picker.widget.destroy()

            else:
                self.assertIsNone(label)

            # Confirm output dir path is empty
            path_text = import_options_window.find("**/StringField[*].name=='Path'")
            self.assertEqual(path_text.model.get_value_as_string(), "")

            # Confirm "Add to current stage" checkbox is False
            check_box = import_options_window.find("**/CheckBox[*].name=='cb_ref_in_stage'")
            self.assertTrue(check_box.model.as_bool)

            # close options window
            cancel_button = import_options_window.find("**/Button[*].text=='Cancel'")
            self.assertTrue(cancel_button)
            await cancel_button.click()

            ai.remove_importer(temp_importer)

        async with ContentBrowserTestHelper() as content_browser_helper:
            await content_browser_helper.navigate_to_async(str(self.data_path))

            # it's fine to test with png files since we don't want to clear and overwrite importer required for other unit tests
            await check_option(content_browser_helper, "cube.bin", True)
            await check_option(content_browser_helper, "cube.bin", False)

    async def test_unload_extension(self):
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = "omni.kit.tool.asset_importer"
        self.assertTrue(manager.is_extension_enabled(ext_id))

        manager.set_extension_enabled(ext_id, False)
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        self.assertTrue(not manager.is_extension_enabled(ext_id))

        manager.set_extension_enabled(ext_id, True)
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        self.assertTrue(manager.is_extension_enabled(ext_id))

    async def test_duplicate_filter_options(self):
        # Ensure filter options contain no duplicates
        importer = ai.AssetImporterExtension.get_instance()
        temp_importer = CustomAssetImporter("temp_importer", [".*\\.png$"], ["png"])
        ai.register_importer(temp_importer)
        filters = importer.get_filter_options()
        size = len(filters)

        temp_importer2 = CustomAssetImporter("temp_importer2", [".*\\.png$"], ["png"])
        ai.register_importer(temp_importer2)
        filters = importer.get_filter_options()
        new_size = len(filters)

        # size would be equal since png from temp_importer2 would get ignored
        self.assertEqual(size, new_size)

        ai.remove_importer(temp_importer)
        ai.remove_importer(temp_importer2)
