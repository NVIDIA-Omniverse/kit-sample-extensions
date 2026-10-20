import webbrowser
from enum import IntEnum

import omni.kit.window.content_browser as content
import omni.ui as ui

from .file_picker import FilePicker
from .filebrowser import FileBrowserMode, FileBrowserSelectionType
from .utils import Utils

__all__ = ["SharedImportOptions", "Destination", "Format", "SharedImportOptionsBuilder"]

"""
Currently shared import options contain
1. whether to import to current stage or external stage
2. export directory for external stage option

More shared options can be added as needed
"""


class SharedImportOptions:
    def __init__(self) -> None:
        # import_as_reference means we write an external usd file
        # if import_as_reference is false import to current stage
        self.import_as_reference = True
        # Only relevant if import as reference is true.
        # if this is true, add reference to the external stage.
        self.add_reference = True
        self.export_folder = ""
        self.export_file_name = ""
        self.export_file_format = ".usd"
        self.scene_optimizer_str = ""
        self.create_usdz = False
        self._destination_collection = None


class Destination(IntEnum):
    Stage = 0
    Reference = 1


class Format(IntEnum):
    USD = 0
    USDA = 1
    USDC = 2
    USDZ = 3


class SharedImportOptionsBuilder:
    def __init__(self):
        self._folder_picker = None
        self._file_picker = None
        self._export_folder_model = ui.SimpleStringModel("")
        self._export_file_name_model = ui.SimpleStringModel("")
        self._export_file_format_items = [".usd", ".usda", ".usdc", ".usdz"]
        self._file_format_combobox = None
        self._is_workflow_import = None
        self._cb_persist_value = True
        self._add_reference_model = ui.SimpleBoolModel(True)
        self._add_reference_model.add_value_changed_fn(self._set_persist_value)
        self._import_destination_model = ui.SimpleIntModel(1)
        self._scene_optimizer_str_model = ui.SimpleStringModel("")
        self._scene_optimizer_stack = None

    def set_default_target_folder(self, folder: str):
        self._export_folder_model.as_string = folder

    def set_default_target_file_name(self, file_name: str):
        self._export_file_name_model.as_string = file_name

    def reset(self):
        self._export_folder_model.as_string = ""
        self._export_file_name_model.as_string = ""
        self._scene_optimizer_str_model.as_string = ""
        self._file_format_combobox = None
        self._destination_collection = None
        self._scene_optimizer_stack = None
        self._import_destination_model.as_int = Destination.Reference
        self._is_workflow_import = None

    def _set_persist_value(self, model: ui.SimpleBoolModel):
        """
        Callback. Set persist value when 'Convert to USD' workflow is selected
        """
        if not self._is_workflow_import:
            self._cb_persist_value = model.as_bool

    def _check_workflow(self, is_workflow_import):
        """
        Check user-selected workflow. If 'Import' workflow selected, set add_reference to true by default
        """
        self._is_workflow_import = is_workflow_import
        if self._is_workflow_import:
            self._add_reference_model.as_bool = self._is_workflow_import

    def destroy(self):
        self._folder_button = None

    def _build_dest_header(self, _: bool, title: str):
        ui.Label(title)

    def build_ui(
        self, is_workflow_import, multiselect, show_dest_frame, show_advanced_options, show_scene_optimizer_config_frame
    ):
        if show_dest_frame:
            self._check_workflow(is_workflow_import)
            self._destination_collection = ui.RadioCollection()
            with ui.CollapsableFrame("Destination:", build_header_fn=self._build_dest_header, height=0):
                with ui.VStack(height=0, spacing=4):
                    self._build_advanced_options(show_advanced_options, self._destination_collection)
                    self._folder_picker_stack = ui.HStack(height=0, spacing=4)
                    with self._folder_picker_stack:
                        ui.Label("Path:", width=0)
                        ui.StringField(
                            name="Path",
                            model=self._export_folder_model,
                            tooltip="Left this empty will export USD to the folder that assets are under.",
                        )
                        self._folder_button = ui.Button(name="dest_folder", width=0, image_width=16, image_height=16)
                        self._folder_button.set_tooltip("Choose folder")
                        self._folder_button.set_clicked_fn(self._show_folder_picker)
                    self._build_ref_in_stage_option()

                    # UI elements for users to pick the file name.
                    with ui.HStack(height=0, spacing=4):
                        if not multiselect:
                            ui.StringField(
                                name="file_name",
                                model=self._export_file_name_model,
                                tooltip="The desired file name for the converted file.",
                            )
                        else:
                            ui.Label("USD File Format:", width=0)
                        self._file_format_combobox = ui.ComboBox(
                            0,
                            *self._export_file_format_items,
                            name="file_format",
                            tooltip="Desired USD file format for conversion.",
                        )

            if show_advanced_options:
                self._destination_collection.model.set_value(Destination.Reference)
                self._destination_collection.model.add_value_changed_fn(self._radio_collection_value_changed)
                self._radio_collection_value_changed(self._destination_collection.model)

        if show_scene_optimizer_config_frame:
            self._scene_optimizer_stack = ui.VStack(height=0, spacing=4)
            with self._scene_optimizer_stack:
                with ui.HStack(height=0, spacing=4):
                    ui.Label("Scene Optimizer Config:")
                    info_btn = ui.Button(
                        height=12,
                        width=12,
                        text="?",
                        tooltip="View documentation",
                    )
                    info_btn.set_clicked_fn(self._open_scene_optimizer_ui_doc)
                with ui.HStack(height=0, spacing=4):
                    ui.StringField(
                        name="scene_optimizer_config_path",
                        model=self._scene_optimizer_str_model,
                        tooltip="Experimental feature - Provide a path to a saved Scene Optimizer JSON configuration file for executing a predefined optimization process stack.",
                    )
                    self._scene_optimize_config_button = ui.Button(
                        name="so_folder", width=0, image_width=16, image_height=16
                    )
                    self._scene_optimize_config_button.set_tooltip("Choose file")
                    self._scene_optimize_config_button.set_clicked_fn(self._show_file_picker)

    def _build_advanced_options(self, show_advanced_options: bool, destination_collection: ui.RadioCollection):
        """
        If supported, display advanced converter options
        Args:
            show_advanced_options (bool): True if converter supports USD Stage Cache
            destination_collection (ui.RadioCollection): Radio Collection
        """
        if show_advanced_options and self._is_workflow_import:
            with ui.VStack():
                with ui.HStack():
                    ui.RadioButton(width=22, height=22, radio_collection=destination_collection)
                    ui.Label("Import to Stage", tooltip="No USD file is created. Prim is imported into USD Stage Cache")
                with ui.HStack():
                    ui.RadioButton(width=22, height=22, radio_collection=destination_collection)
                    ui.Label(
                        "Import as Reference",
                        tooltip="Generates a USD file and imports to current stage as a referenced prim",
                    )

    def _build_ref_in_stage_option(self):
        """
        If the Import workflow is True, do not display checkbox for adding reference in current stage
        """
        if self._is_workflow_import is False:
            self._add_reference_model.as_bool = self._cb_persist_value
            with ui.HStack(height=0, spacing=4):
                ui.CheckBox(name="cb_ref_in_stage", model=self._add_reference_model, width=0)
                ui.Label("Reference in Current Stage")

    def _radio_collection_value_changed(self, model: ui.SimpleIntModel) -> None:
        value = model.as_int
        self._import_destination_model.as_int = value
        self._folder_picker_stack.visible = value == Destination.Reference

    def _show_folder_picker(self):
        if not self._folder_picker:
            mode = FileBrowserMode.OPEN
            file_type = FileBrowserSelectionType.DIRECTORY_ONLY
            filters = [(".*", "All Files (*.*)")]
            self._folder_picker = FilePicker(
                title="Select Folder",
                apply_button_name="Select Folder",
                mode=mode,
                file_type=file_type,
                filter_options=filters,
            )
            self._folder_picker.set_file_selected_fn(self._select_picked_folder_callback)

        folder = self._export_folder_model.as_string
        if folder and Utils.is_folder(folder):
            self._folder_picker.show(folder)
        else:
            self._folder_picker.show(self._get_current_dir_in_content_window())

    def _show_file_picker(self):
        if self._file_picker:
            self._file_picker.destroy()
            self._file_picker = None
        if not self._file_picker:
            mode = FileBrowserMode.OPEN
            file_type = FileBrowserSelectionType.FILE_ONLY
            filters = [(".*", "JSON Files (*.json)")]
            self._file_picker = FilePicker(
                title="Select File..",
                apply_button_name="Select",
                mode=mode,
                file_type=file_type,
                filter_options=filters,
            )
            self._file_picker.set_file_selected_fn(self._select_picked_file_callback)

        folder = self._export_folder_model.as_string
        if folder and Utils.is_folder(folder):
            self._file_picker.show(folder)
        else:
            self._file_picker.show(self._get_current_dir_in_content_window())

    def _get_current_dir_in_content_window(self):
        content_window = content.get_content_window()
        return content_window.get_current_directory()

    def _select_picked_folder_callback(self, paths):
        if paths:
            self._export_folder_model.as_string = paths[0]

    def _select_picked_file_callback(self, paths):
        if paths:
            self._scene_optimizer_str_model.as_string = paths[0]

    def _open_scene_optimizer_ui_doc(self):
        webbrowser.open(
            "https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/user-manual.html#scene-optimizer-ui"
        )

    def get_options(self):
        _options = SharedImportOptions()
        _options.export_folder = self._export_folder_model.as_string.strip().replace("\\", "/")
        _options.export_file_name = self._export_file_name_model.as_string

        if self._file_format_combobox == None:
            _options.export_file_format = self._export_file_format_items[0]
        else:
            format_selected_index = self._file_format_combobox.model.get_item_value_model().as_int
            # if user wants to convert to .usdz, we'll convert to .usdc first then package to .usdz
            _options.create_usdz = format_selected_index == Format.USDZ
            if _options.create_usdz:
                format_selected_index = int(Format.USDC)

            _options.export_file_format = self._export_file_format_items[format_selected_index]
        _options.import_as_reference = self._import_destination_model.as_int == Destination.Reference
        _options.add_reference = self._add_reference_model.as_bool
        _options.scene_optimizer_str = self._scene_optimizer_str_model.as_string
        return _options

    def refresh_panel(self, show_scene_optimizer_options):
        if self._scene_optimizer_stack:
            self._scene_optimizer_stack.visible = show_scene_optimizer_options
