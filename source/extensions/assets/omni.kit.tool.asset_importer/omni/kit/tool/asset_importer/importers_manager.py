__all__ = ["ImportersManager"]

import inspect
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import carb
import omni.kit.notification_manager as nm
import omni.ui as ui
from omni.kit.usd.layers import get_layers
from omni.kit.usdz_export import usdz_export
from pxr import Sdf

from .importer_delegate import AbstractImporterDelegate, BuiltInImporterDelegate
from .shared_options_builder import SharedImportOptions, SharedImportOptionsBuilder
from .styles import OPTIONS_STYLE


class ImportersManager:
    def __init__(self, usd_context, buitin_importer):
        self._builtin_importer = BuiltInImporterDelegate(usd_context, buitin_importer)
        self._importers: List[AbstractImporterDelegate] = [self._builtin_importer]
        self._shared_options_builder = SharedImportOptionsBuilder()

        self._converter_labels = {}
        self._converter_selectors = {}
        self._converter_stacks = {}
        self._converter_selector_cb_ids = {}

    def destroy(self):
        self._shared_options_builder.destroy()
        self._shared_options_builder = None
        self._builtin_importer.destroy()
        self._builtin_importer = None

    def set_builtin_importer_default_target_folder(self, folder: str):
        self._builtin_importer.set_default_target_folder(folder)

    def set_builtin_importer_default_target_file_name(self, paths: str):
        # only set default name when one file is selected. Otherwise the default name is irrelavent
        if len(paths) == 1:
            self._shared_options_builder.set_default_target_file_name(Path(paths[0]).stem)
        else:
            self._shared_options_builder.set_default_target_file_name("")

    def reset_shared_options(self):
        self._shared_options_builder.reset()

    def add_importer(self, importer_delegate: AbstractImporterDelegate):
        if importer_delegate not in self._importers:
            self._importers.append(importer_delegate)

    def remove_importer(self, importer):
        if importer in self._importers:
            self._importers.remove(importer)

    def is_supported_format(self, path: str):
        for importer in self._importers:
            if importer.is_supported_format(path):
                return True

        return False

    def on_converter_selected(self, path, importers):
        """Show or hide the converter stack based on the selected converter for the given path"""
        show_scene_optimizer_options = False
        index = self._converter_selectors[path].model.get_item_value_model().as_int
        for idx, importer in enumerate(importers):
            if idx in self._converter_stacks[path]:
                selected = index == idx
                self._converter_stacks[path][idx].visible = selected

                if selected and importer.show_scene_optimizer_config_frame():
                    show_scene_optimizer_options = True

        # if no converter panel that supports scene optimizer post processing is shown,
        # we hide the scene optimizer option from shared import options panel
        self._shared_options_builder.refresh_panel(show_scene_optimizer_options)

    def get_supported_converters_map(self, paths: List[str]) -> Dict[str, List[AbstractImporterDelegate]]:
        """Returns a Dict where key = input path and value = list of supported converters for that path"""
        converters_map = {}
        for path in paths:
            for importer in self._importers:
                if importer.is_supported_format(path):
                    if path not in converters_map:
                        converters_map[path] = []
                    converters_map[path].append(importer)

        # Sort importers by priority (highest first), with registration order preserved for same priority
        for path in converters_map:
            converters_map[path].sort(key=lambda imp: imp.priority, reverse=True)

        return converters_map

    def build_options_for_file(self, path, importers):
        """
        build options panel for the selected file path
        """
        with ui.VStack(height=0, spacing=5, style=OPTIONS_STYLE):
            importer_names = self._get_importer_display_names(importers)
            self._converter_labels[path] = ui.Label("Choose a Converter:")
            self._converter_selectors[path] = ui.ComboBox(0, *importer_names, height=20)

            self._converter_stacks[path] = {}
            for idx, importer in enumerate(importers):
                self._converter_stacks[path][idx] = ui.VStack(height=0, spacing=5, style=OPTIONS_STYLE)
                with self._converter_stacks[path][idx]:
                    importer.build_options([path])
            self._converter_selector_cb_ids[path] = self._converter_selectors[path].model.add_item_changed_fn(
                lambda a, b: self.on_converter_selected(path, importers)
            )
            self._converter_labels[path].visible = len(importers) > 1
            self._converter_selectors[path].visible = len(importers) > 1

            if self._converter_selectors[path].visible:
                self.on_converter_selected(path, importers)

    def build_options_pane(self, paths: List[str], add_reference_to_stage: bool = True):
        supported_converters_map = self.get_supported_converters_map(paths)
        # no supported converter found for any of the paths
        if len(supported_converters_map) == 0:
            return False
        with ui.VStack(height=0, spacing=5, style=OPTIONS_STYLE):
            show_dest_frame = False
            show_advanced_options = False
            show_scene_optimizer_config_frame = False
            for path, importers in supported_converters_map.items():
                if len(supported_converters_map) > 1:
                    file_name = Path(path).name
                    with ui.CollapsableFrame(f"Convert Options of {file_name}", height=0):
                        self.build_options_for_file(path, importers)
                else:
                    self.build_options_for_file(path, importers)

                for importer in importers:
                    if importer.show_destination_frame():
                        show_dest_frame = True
                    if importer.supports_usd_stage_cache():
                        show_advanced_options = True
                    if importer.show_scene_optimizer_config_frame():
                        show_scene_optimizer_config_frame = True

            # add_reference_to_stage can be used to determine user workflow (i.e. if File->Import was selected)
            self._shared_options_builder.build_ui(
                add_reference_to_stage,
                len(paths) > 1,
                show_dest_frame,
                show_advanced_options,
                True,
            )

            for path, importers in supported_converters_map.items():
                self.on_converter_selected(path, importers)

        return True

    def _get_importer_display_names(self, importers):
        seen_names = {}
        importer_names = []
        for importer in importers:
            seen_names[importer.name] = seen_names.get(importer.name, 0) + 1
            if seen_names[importer.name] == 1:
                importer_names.append(importer.name)
            else:
                importer_names.append(f"{importer.name} ({seen_names[importer.name]})")
        return importer_names

    async def convert_assets(
        self,
        paths: List[str],
        add_reference=False,
        shared_import_options: Optional[SharedImportOptions] = None,
    ) -> Dict[str, Union[str, None]]:
        # find out which importer is responsible to convert which files
        supported_converters_map = self.get_supported_converters_map(paths)
        # importer_file_map's key = importer name, value = list of paths to convert
        importer_files_map = {}
        for path, importers in supported_converters_map.items():
            selected_importer = None
            if path in self._converter_stacks:
                for idx, importer in enumerate(importers):
                    if self._converter_stacks[path][idx].visible:
                        selected_importer = importer
                        break
            elif importers:
                # In drag/drop or other no-options flows, choose the default converter instead of running every match.
                selected_importer = importers[0]

            if selected_importer:
                if selected_importer not in importer_files_map:
                    importer_files_map[selected_importer] = []
                importer_files_map[selected_importer].append(path)

        result: Dict[str, Union[str, None]] = {}
        for importer in self._importers:
            if importer not in importer_files_map:
                continue

            to_convert_paths = importer_files_map[importer]

            converted_assets = {}
            if to_convert_paths:
                try:
                    argspec = inspect.getfullargspec(importer.convert_assets)
                    # This is for back compatibility of old interface.
                    if not argspec.varkw:
                        converted_assets = await importer.convert_assets(to_convert_paths)
                    else:
                        if shared_import_options is None:
                            shared_import_options = self._shared_options_builder.get_options()

                        # we don't support import to stage in live sessions
                        if (
                            not shared_import_options.import_as_reference
                            and get_layers().get_live_syncing().is_stage_in_live_session()
                        ):
                            nm.post_notification(
                                "Import to Stage is not supported during live session",
                                duration=4,
                                status=nm.NotificationStatus.WARNING,
                            )
                            continue
                        converted_assets = await importer.convert_assets(
                            to_convert_paths,
                            # keeping this for backward compatibility..same as import_to_stage but import_to_stage was
                            # created to differentiate between add_reference and import_as_reference
                            add_reference=add_reference,
                            # whether we want to add converted USD to stage
                            import_to_stage=add_reference,
                            # either import as USD reference (External Stage) or
                            # copy content from UsdStageCache (Current Stage)
                            import_as_reference=shared_import_options.import_as_reference,
                            export_folder=shared_import_options.export_folder,
                            export_file_name=shared_import_options.export_file_name,
                            export_file_format=shared_import_options.export_file_format,
                            scene_optimizer_str=shared_import_options.scene_optimizer_str,
                        )

                        if shared_import_options.create_usdz:
                            for src_path, dest_path in converted_assets.items():
                                base, _ = os.path.splitext(dest_path)
                                usdz_path = base + ".usdz"
                                await usdz_export(dest_path, usdz_path)
                                converted_assets[src_path] = usdz_path
                                os.remove(dest_path)

                except Exception as e:
                    carb.log_warn(f"Failed to convert assets {to_convert_paths} since importer failed with {str(e)}.")
                    nm.post_notification(
                        f"Failed to convert assets due to unknown exception.\n"
                        "Please check console for more details.",
                        status=nm.NotificationStatus.WARNING,
                    )

                result.update(converted_assets)

        return result

    async def added_references(self, assets: Dict[str, Tuple[str, Sdf.Path]]):
        for importer in self._importers:
            to_convert_paths = {}
            for asset_pair in assets.items():
                asset_path, value = asset_pair
                if importer.is_supported_format(asset_path):
                    to_convert_paths[asset_path] = value

            if to_convert_paths:
                try:
                    await importer.added_reference(to_convert_paths)
                except Exception:
                    pass

    def get_all_filters(self) -> Tuple[List[str], List[str]]:
        all_filters = []
        all_filter_descriptions = []
        for importer in self._importers:
            all_filters.extend(importer.filter_regexes)
            all_filter_descriptions.extend(importer.filter_descriptions)

        return all_filters, all_filter_descriptions
