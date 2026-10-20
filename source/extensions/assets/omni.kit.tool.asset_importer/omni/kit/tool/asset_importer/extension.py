# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import asyncio
import os
import urllib
from functools import partial
from pathlib import Path
from typing import Dict, List

import carb
import omni.client
import omni.ext
import omni.kit.actions.core
import omni.kit.app
import omni.kit.commands
import omni.kit.window.content_browser as content
import omni.usd
from omni.kit.menu.utils import MenuItemDescription
from omni.kit.widget.prompt import PromptButtonInfo, PromptManager
from pxr import Sdf, Tf, Usd, UsdUtils

from .builtin_importer import BuiltinImporter
from .file_picker import FilePicker
from .filebrowser import FileBrowserMode, FileBrowserSelectionType
from .importer_delegate import AbstractImporterDelegate
from .importers_manager import ImportersManager
from .options_window import OptionsWindow
from .shared_options_builder import SharedImportOptions
from .utils import Utils

__all__ = [
    "AssetImporterExtension",
    "register_importer",
    "remove_importer",
    "is_supported_format",
    "AbstractImporterDelegate",
]

_global_instance = None


class AssetImporterExtension(omni.ext.IExt):
    IMPORT_FILE_MENU_NAME = "Import"
    UPLOAD_MENU_NAME = "Upload Files and Folders"
    IMPORT_AND_CONVERT_MENU_NAME = "Import and Convert"
    CONVERT_TO_USD_MENU_NAME = "Convert to USD"
    IMPORT_ICON_MENU_NAME = "External Asset (FBX, OBJ...)"
    PERSISTENT_APP_IMPORT_SETTINGS_PATH = "/persistent/app/stage/dragDropImport"

    def on_startup(self, ext_id):
        global _global_instance
        _global_instance = self

        self._usd_context = omni.usd.get_context()
        self._app = omni.kit.app.get_app()
        self._buitin_importer = BuiltinImporter()
        self._buitin_importer.on_startup()
        self._importers_manager = ImportersManager(self._usd_context, self._buitin_importer)
        self._converter_file_picker = None
        self._upload_file_picker = None
        self._file_menu_items = []
        self._import_menu_items = []
        self._list_view_menu_items = []
        self._context_menu_items = []
        self._open_handler_items = []
        self._options_window: OptionsWindow = None
        self._complete_callbacks = []
        self._canceled_callbacks = []
        self._current_servers = []
        self._drag_drop_support = None
        self._client_bookmarks_changed_subscription = omni.client.list_bookmarks_with_callback(
            self._on_client_bookmarks_changed
        )
        self._register_menus()
        self._ext_name = omni.ext.get_extension_name(ext_id)
        self._register_action(self._ext_name)
        self._register_drag_drop_support()

        # Re-attempt to set default directory to `omniverse://` so import menu items are initialized.
        async def _set_default_dir():
            await self._app.next_update_async()
            content_window = content.get_content_window()
            try:
                content_window.navigate_to("omniverse://")
            except Exception as e:
                carb.log_warn(f"Failed to navigate to `omniverse://`: {e}")

        asyncio.ensure_future(_set_default_dir())

    def on_shutdown(self):

        if self._drag_drop_support:
            self._drag_drop_support.destroy()
            self._drag_drop_support = None

        if self._options_window:
            self._options_window.set_import_fn(None)
            self._options_window.destroy()

        self._unregister_menus()
        if self._upload_file_picker:
            self._upload_file_picker.destroy()
            self._upload_file_picker = None

        if self._converter_file_picker:
            self._converter_file_picker.destroy()
            self._converter_file_picker = None
        self._importers_manager.destroy()
        self._importers_manager = None
        self._buitin_importer.on_shutdown()
        self._buitin_importer = None
        self._deregister_action(self._ext_name)

        global _global_instance
        _global_instance = None

    def is_supported_format(self, path: str):
        return self._importers_manager.is_supported_format(path)

    def add_importer(self, importer_delegate: AbstractImporterDelegate):
        self._importers_manager.add_importer(importer_delegate)

    def remove_importer(self, importer_delegate: AbstractImporterDelegate):
        self._importers_manager.remove_importer(importer_delegate)

    def add_import_complete_callback(self, callback):
        self._complete_callbacks.append(callback)

    def remove_import_complete_callback(self, callback):
        self._complete_callbacks.remove(callback)

    def add_import_canceled_callback(self, callback):
        self._canceled_callbacks.append(callback)

    def remove_import_canceled_callback(self, callback):
        self._canceled_callbacks.remove(callback)

    def get_filter_options(self):
        # get filter options while ensuring there are no duplicates
        all_filters, all_filter_descriptions = self._importers_manager.get_all_filters()
        filters_combined = all_filters[0]
        for i in range(1, len(all_filters)):
            filters_combined += f"|{all_filters[i]}"

        added_extensions = set()

        filters = [(filters_combined, "All Supported Files (*.fbx, *.obj, ...)")]
        for format_filter, description in zip(all_filters, all_filter_descriptions):
            # extract extensions from the description
            # "glTF Files (*.GLTF, *.GLB)" would result in ["*.gltf", "*.glb"]
            # "*.ABC" would result in ["*.abc"]
            extensions_str = None
            index = description.find("(")
            if index > -1:
                extensions_str = description[index + 1 : len(description) - 1]
            else:
                extensions_str = description
            extensions_str = extensions_str.replace(" ", "")
            extensions = extensions_str.split(",")

            # only append unique filters to prevent having duplicated items in the dropdown
            for extension in extensions:
                extension = extension.lower()
                if extension not in added_extensions:
                    filters.append((format_filter, description))
                    added_extensions.update(set(extensions))
                    break
        return filters

    def import_asset(self, add_reference=False, export_to_current_folder=True):
        def on_selection_changed(export_folder, paths: List[str]):
            if paths:
                target_dir = self._get_export_folder(paths, export_to_current_folder, export_folder)
                self._importers_manager.set_builtin_importer_default_target_folder(target_dir)
                self._importers_manager.set_builtin_importer_default_target_file_name(paths)

        self._importers_manager.reset_shared_options()
        export_folder = self._get_current_dir_in_content_window()
        default_export_folder = self._get_export_folder([], export_to_current_folder)
        self._importers_manager.set_builtin_importer_default_target_folder(default_export_folder)

        # Generate file picker

        # if 'Convert-to-USD' window is open, close it
        if self._options_window:
            self._options_window.destroy()
        if self._converter_file_picker:
            self._converter_file_picker.destroy()

        self._converter_file_picker = FilePicker(
            title="Select File",
            mode=FileBrowserMode.OPEN,
            file_type=FileBrowserSelectionType.FILE_ONLY,
            filter_options=self.get_filter_options(),
            allow_multi_selections=True,
            import_to_stage=add_reference,
            options_pane_build_fn=self._importers_manager.build_options_pane,
            on_selection_changed=partial(on_selection_changed, export_folder),
        )
        self._converter_file_picker.set_file_selected_fn(lambda paths: self._convert_file(paths, add_reference))
        current_dir = self._get_current_dir_in_content_window()

        if export_to_current_folder:
            current_dir = self._get_current_dir_in_content_window()
        else:
            default_settings = self._load_default_settings()
            current_dir = default_settings.get("directory")
        self._converter_file_picker.show(current_dir)

        def _cancel():
            for callback in self._canceled_callbacks:
                callback()
            self._converter_file_picker = None

        self._converter_file_picker.set_cancel_fn(lambda: _cancel())

    def _save_default_settings(self, default_settings: Dict):
        settings = carb.settings.get_settings()
        default_settings_path = settings.get_as_string("/exts/omni.kit.tool.asset_importer/appSettings")
        settings.set_string(f"{default_settings_path}/directory", default_settings["directory"] or "")

    def _load_default_settings(self) -> dict:
        settings = carb.settings.get_settings()
        default_settings_path = settings.get_as_string("/exts/omni.kit.tool.asset_importer/appSettings")

        default_settings = {}
        directory = settings.get_as_string(f"{default_settings_path}/directory")
        if directory.startswith("omniverse"):
            default_settings["directory"] = ""
            mounted_servers = {}
            mounted_servers_value = settings.get_settings_dictionary(
                "exts/omni.kit.window.content_browser/mounted_servers"
            )
            if mounted_servers_value:
                mounted_servers = mounted_servers_value.get_dict()
            # OM-83885: Load default derectory only if it's server is in current servers
            for server in list(mounted_servers.values()) + self._current_servers:
                if directory.startswith(server):
                    default_settings["directory"] = directory
                    break
        else:
            default_settings["directory"] = directory
        return default_settings

    def _on_client_bookmarks_changed(self, client_bookmarks: Dict):
        self._current_servers = [url for name, url in client_bookmarks.items() if self._is_nucleus_server_url(url)]

    def _is_nucleus_server_url(self, url: str):
        if not url:
            return False
        broken_url = omni.client.break_url(url)
        if broken_url.scheme == "omniverse" and broken_url.path == "/" and broken_url.host is not None:
            # Url of the form "omniverse://server_name/" should be recognized as server connection
            return True
        return False

    def _unregister_menus(self):
        # unregister actions
        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.deregister_all_actions_for_extension("omni.kit.tool.asset_importer")

        content_window = content.get_content_window()
        for item in self._context_menu_items:
            content_window.delete_context_menu(item)
        self._context_menu_items.clear()
        content_window.delete_import_menu(self.IMPORT_ICON_MENU_NAME)
        self._import_menu_items.clear()
        for item in self._list_view_menu_items:
            content_window.delete_listview_menu(item)
        self._list_view_menu_items.clear()
        for item in self._open_handler_items:
            content_window.delete_file_open_handler(item)
        self._open_handler_items.clear()
        if self._file_menu_items:
            omni.kit.menu.utils.remove_menu_items(self._file_menu_items, "File")
        self._file_menu_items.clear()

    def _register_menus(self):
        # register actions
        action_registry = omni.kit.actions.core.get_action_registry()
        actions_tag = "Collect Tool Actions"

        # actions
        action_registry.register_action(
            "omni.kit.tool.asset_importer",
            "menu_convert",
            lambda: self._on_menu_convert_click(True, False),
            display_name="menu_convert",
            description="menu_convert",
            tag=actions_tag,
        )

        content_window = content.get_content_window()

        self._list_view_menu_items.append(
            content_window.add_listview_menu(
                self.UPLOAD_MENU_NAME,
                "upload.svg",
                lambda a, b: self._on_menu_upload_click(),
                self._is_show_upload_visible,
            )
        )

        self._list_view_menu_items.append(
            content_window.add_listview_menu(
                self.IMPORT_AND_CONVERT_MENU_NAME,
                "upload.svg",
                lambda a, b: self._on_menu_convert_click(),
                self._is_show_upload_visible,
            )
        )

        self._context_menu_items.append(
            content_window.add_context_menu(
                self.CONVERT_TO_USD_MENU_NAME,
                "upload.svg",
                lambda b, c: self._on_icon_menu_click(b, c),
                self._is_show_convert_visible,
            )
        )

        self._import_menu_items.append(
            content_window.add_import_menu(
                self.IMPORT_ICON_MENU_NAME,
                "plus.svg",
                lambda a, b: self._on_menu_convert_click(),
                lambda a: self._is_show_import_menu(),
            )
        )

        self._open_handler_items.append(
            content_window.add_file_open_handler(
                self.CONVERT_TO_USD_MENU_NAME,
                lambda file_path: self._show_options_window_and_convert([file_path]),
                self._is_show_open_visible,
            )
        )

        self._file_menu_items = [
            MenuItemDescription(
                name=self.IMPORT_FILE_MENU_NAME,
                glyph="none.svg",
                appear_after=["Reopen", "Open Recent"],
                onclick_action=("omni.kit.tool.asset_importer", "menu_convert"),
            )
        ]

        omni.kit.menu.utils.add_menu_items(self._file_menu_items, "File")

    def _is_show_open_visible(self, content_url):
        # List of available formats: carb/source/plugins/carb.imaging/Imaging.cpp
        return self._importers_manager.is_supported_format(content_url)

    def _is_show_import_menu(self):
        content_window = content.get_content_window()
        current_dir = content_window.get_current_directory()

        return current_dir is not None

    def _is_show_upload_visible(self, url):
        # OM-72882: Do not show upload menu items in read-only context
        # FIXME: Ideally, we shouldn't need to manually find the item again, but we had to here since when we use `add_list_menu` or
        #  `add_context_menu`, the show_fn and click_fn for the menu item was only getting the context['item'].path instead of the
        #  full context item
        async def check_writeable(url):
            content_window = content.get_content_window()
            item = await content_window.api.model.find_item_async(url)
            if item:
                return item.writeable
            # Fallback to show upload if item cannot be found
            return True

        # need to run this synchronously to get the correct show_fn result
        future = asyncio.ensure_future(check_writeable(url))
        if not future.done():
            asyncio.get_event_loop().run_until_complete(future)
        return future.result()

    def _is_show_convert_visible(self, content_url):
        return self._importers_manager.is_supported_format(content_url)

    def _get_current_dir_in_content_window(self):
        content_window = content.get_content_window()
        return content_window.get_current_directory()

    def _on_icon_menu_click(self, menu, value):
        # Context menu provides last selected file path. Multi-selected files must be retrieved from 'Content' window
        selections = content.get_content_window().get_current_selections()
        if len(selections) > 1:
            self._show_options_window_and_convert(selections)
        else:
            # Users can hover over a file and right click -> 'Convert to USD'
            # once the mouse cursors leaves the file, content.get_content_window().get_current_selections() would return empty list
            # so we fallback to using last selected file
            self._show_options_window_and_convert([value])

    def _on_menu_upload_click(self):
        filters = [(".*", "All Files (*.*)")]
        if not self._upload_file_picker:
            self._upload_file_picker = FilePicker(
                title="Select Files or Folder",
                mode=FileBrowserMode.OPEN,
                file_type=FileBrowserSelectionType.ALL,
                filter_options=filters,
                allow_multi_selections=True,
            )

        export_dir = self._get_current_dir_in_content_window()

        async def upload_file(file_paths):
            if not file_paths:
                return

            if not export_dir or export_dir == os.path.dirname(file_paths[0]):
                return

            upload_absolute_paths = []
            upload_relative_paths = []
            prompt = PromptManager.post_simple_prompt(
                "Waiting", "Listing all files to be copied...", ok_button_info=None, cancel_button_info=None
            )

            # Waits two updates to show prompt.
            await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()

            for file_path in file_paths:
                if prompt and not prompt.is_visible():
                    return

                absolute_paths, relative_paths = await Utils.list_folder_async(file_path)
                upload_absolute_paths += absolute_paths
                upload_relative_paths += relative_paths

            prompt.hide()
            prompt = None

            await self._buitin_importer.create_import_task(
                False, upload_absolute_paths, upload_relative_paths, export_dir, "", "", None
            )

        def _on_file_selected_fn(paths):
            asyncio.ensure_future(upload_file(paths))

        self._upload_file_picker.set_file_selected_fn(_on_file_selected_fn)
        self._upload_file_picker.show(export_dir)

    def _show_options_window_and_convert(self, paths: List[str]):
        if self._converter_file_picker:
            self._converter_file_picker.destroy()
        if self._options_window:
            self._options_window.destroy()
        self._importers_manager.reset_shared_options()
        self._options_window = OptionsWindow(self._usd_context, self._importers_manager)
        self._options_window.set_import_fn(self._convert_file)

        absolute_paths = []
        for file_path in paths:
            if not Utils.is_folder(file_path):
                absolute_paths.append(file_path)

        self._options_window.show(absolute_paths, True)

    def _register_drag_drop_support(self):
        try:
            from .drag_drop import AssetImporterDragDropSupport

            self._drag_drop_support = AssetImporterDragDropSupport(self)
        except Exception as e:
            carb.log_warn(f"Failed to register Asset Importer drag/drop support: {e}")

    def _convert_file(self, file_paths, add_reference=True):
        if not file_paths:
            return
        saved_export_diretory = os.path.dirname(file_paths[0])
        self._save_default_settings({"directory": saved_export_diretory})

        asyncio.ensure_future(self._import_paths_async(file_paths, add_reference))

    async def _import_paths_async(
        self, paths: List[str], add_reference=True, parent_path=None, use_default_options=False
    ):
        if not paths:
            return

        shared_options = SharedImportOptions() if use_default_options else None
        converted_assets = await self._importers_manager.convert_assets(paths, add_reference, shared_options)

        if add_reference:
            await self._add_converted_assets_to_stage(converted_assets, paths, parent_path, shared_options)

    async def _add_converted_assets_to_stage(
        self, converted_assets, file_paths: List[str], parent_path=None, shared_options=None
    ):
        if shared_options is None:
            shared_options = self._importers_manager._shared_options_builder.get_options()
        import_as_reference = shared_options.import_as_reference
        added_reference_assets = {}

        with omni.kit.undo.group():
            prompt = None
            if import_as_reference:
                prompt = PromptManager.post_simple_prompt("Add Reference", "", ok_button_info=None)
            else:
                prompt = PromptManager.post_simple_prompt("Add Stage Data", "", ok_button_info=None)
            await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()
            try:
                for asset_pair in converted_assets.items():
                    asset_path, usd_path = asset_pair
                    if not usd_path:
                        continue

                    path = Path(usd_path) if import_as_reference else Path(asset_path)
                    path_stem, _ = Utils.strip_file_regex(path, r"\.(asm|prt)(\.[0-9]+)?$")
                    path_stem = urllib.parse.unquote(path_stem)
                    display_name = path_stem
                    stem = Tf.MakeValidIdentifier(path_stem)
                    stage: Usd.Stage = self._usd_context.get_stage()
                    prim_path = self._get_next_import_prim_path(stage, stem, parent_path)

                    if import_as_reference:
                        prompt.set_text(f"Creating reference for {path.name}...")
                    else:
                        prompt.set_text(f"Creating stage data for {path.name}...")
                    await omni.kit.app.get_app().next_update_async()

                    settings = carb.settings.get_settings()
                    import_settings_string = settings.get_as_string(self.PERSISTENT_APP_IMPORT_SETTINGS_PATH)
                    if not import_as_reference:
                        cache: Usd.StageCache = UsdUtils.StageCache.Get()
                        stage_id = usd_path
                        stage.DefinePrim(prim_path)
                        cached_stage = cache.Find(Usd.StageCache.Id.FromString(stage_id))
                        if not cached_stage:
                            carb.log_error(f"Could not find stage from stage cache: {usd_path}")

                        Sdf.CopySpec(
                            cached_stage.GetRootLayer(),
                            cached_stage.GetDefaultPrim().GetPath(),
                            stage.GetRootLayer(),
                            Sdf.Path(prim_path),
                        )
                        carb.log_info(f"Asset: '{asset_path}' inserted into current stage.")
                    elif import_as_reference and shared_options.add_reference:
                        if import_settings_string == "payload":
                            omni.kit.commands.execute(
                                "CreatePayloadCommand",
                                path_to=prim_path,
                                asset_path=usd_path,
                                usd_context=self._usd_context,
                            )
                        else:
                            omni.kit.commands.execute(
                                "CreateReferenceCommand",
                                path_to=prim_path,
                                asset_path=usd_path,
                                usd_context=self._usd_context,
                            )

                        # Set the display name metadata for the reference prim
                        ref_prim = stage.GetPrimAtPath(prim_path)
                        if ref_prim:
                            ref_prim.SetMetadata("displayName", display_name)

                        added_reference_assets[asset_path] = (usd_path, Sdf.Path(prim_path))
                        carb.log_info(
                            f"Asset: '{asset_path}' added as {import_settings_string}. (can be set in Preferences>Stage>Import)"
                        )
            finally:
                prompt.destroy()
                prompt = None

        await self._importers_manager.added_references(added_reference_assets)

        for callback in self._complete_callbacks:
            callback(file_paths)

    def _get_next_import_prim_path(self, stage: Usd.Stage, stem: str, parent_path=None):
        parent = Sdf.Path.absoluteRootPath
        if parent_path:
            try:
                candidate = Sdf.Path(str(parent_path))
                if candidate.IsAbsolutePath() and not candidate.IsAbsoluteRootPath():
                    parent = candidate
            except Exception:
                carb.log_warn(f"Invalid import parent path: {parent_path}")

        path = parent.AppendChild(stem)
        return omni.usd.get_stage_next_free_path(stage, str(path), True)

    def _get_export_folder(self, asset_paths, export_to_current_folder, current_folder=None):
        # Sets the default export folder
        stage = self._usd_context.get_stage()
        if export_to_current_folder:
            if current_folder:
                export_folder = current_folder
            else:
                export_folder = self._get_current_dir_in_content_window()
        elif not stage or stage.GetRootLayer().anonymous:
            export_folder = None
        else:
            export_folder = os.path.dirname(stage.GetRootLayer().identifier)

        if export_folder and len(asset_paths) == 1:
            if export_folder.endswith("/"):
                export_folder = export_folder[:-1]
            export_folder += "/" + Path(asset_paths[0]).stem
        elif not export_folder:
            export_folder = ""

        return export_folder

    def _on_menu_convert_click(self, add_reference=True, export_to_current_folder=True):
        self.import_asset(add_reference, export_to_current_folder)

    def _register_action(self, extension_id: str):
        action_registry = omni.kit.actions.core.get_action_registry()
        actions_tag = "File Actions"
        action_registry.register_action(
            extension_id,
            "import",
            lambda: self._on_menu_convert_click(True, False),
            display_name="Import",
            description="Import asset to the stage",
            tag=actions_tag,
        )

    def _deregister_action(self, extension_id: str):
        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.deregister_all_actions_for_extension(extension_id)

    @staticmethod
    def get_instance():
        global _global_instance
        return _global_instance


def register_importer(importer_delegate: AbstractImporterDelegate):
    """Register external importer. Asset importer includes builtin
    importers to convert FBX/OBJ/GLTF... files that Assimp supports.
    This is used to register external importers that's not supported
    by builtin importers.

    Args:
        importer_delegate (omni.kit.tool.asset_importer.AbstractImporterDelegate):
            The delegate to define the details of an importer. Refer class `AbstractImporterDelegate`
            for reference.
    """

    instance = AssetImporterExtension.get_instance()
    if instance:
        instance.add_importer(importer_delegate)
    else:
        carb.log_error(f"AssetImporter Extension is not enabled.")


def remove_importer(importer_delegate: AbstractImporterDelegate):
    """Unregister importer."""

    instance = AssetImporterExtension.get_instance()
    if instance:
        instance.remove_importer(importer_delegate)
    else:
        carb.log_error(f"AssetImporter Extension is not enabled.")


def is_supported_format(path: str):
    """Check if this asset format is supported by any importers already."""

    instance = AssetImporterExtension.get_instance()
    if instance:
        return instance.is_supported_format(path)
    else:
        carb.log_error(f"AssetImporter Extension is not enabled.")

    return False
