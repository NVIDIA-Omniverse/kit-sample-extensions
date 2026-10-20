import os
from functools import partial
from pathlib import Path
from typing import List

import omni.kit.window.content_browser as content
import omni.ui as ui
from omni.kit.asset_converter import AssetConverterContext

from .filebrowser import FileBrowserMode, FileBrowserSelectionType
from .minimal_model import MinimalItem, MinimalModal
from .styles import OPTIONS_STYLE
from .utils import Utils

__all__ = ["BuiltinImporterOptions", "BuiltinImporterOptionsBuilder"]


class BuiltinImporterOptions:
    def __init__(self) -> None:
        self.asset_import_context = AssetConverterContext()


class BuiltinImporterOptionsBuilder:
    def __init__(self, usd_context):
        super().__init__()
        self._file_picker = None
        self._usd_context = usd_context
        self._export_context = BuiltinImporterOptions()
        self._folder_button = None
        self._refresh_default_folder = False
        self._default_folder = None
        self._mat_model_sub = None
        self._clear()

    def _clear(self):
        self._built = False
        self._mat_checkbox = None
        self._preview_surface_checkbox = None
        self._animation_checkbox = None
        self._camera_checkbox = None
        self._light_checkbox = None
        self._bones_checkbox = None
        self._smooth_normals_checkbox = None
        self._rotation_checkbox = None
        self._meters_as_world_unit_checkbox = None
        self._create_world_as_default_root_prim_checkbox = None
        self._merge_all_meshes_checkbox = None
        self._export_folder_field = None
        self._convert_stage_up_combobox = None
        if self._folder_button:
            self._folder_button.set_clicked_fn(None)
            self._folder_button = None

    def set_default_target_folder(self, folder: str):
        self._default_folder = folder
        self._refresh_default_folder = True

    def build_pane(self, asset_paths: List[str]):
        self._export_context = self.get_import_options()
        if self._refresh_default_folder:
            self._export_context.export_folder = self._default_folder
            self._default_folder = None
            self._refresh_default_folder = False

        self._built = True

        with ui.VStack(height=0, style=OPTIONS_STYLE, spacing=4):
            self._mat_checkbox = self._build_option_checkbox(
                "Import Materials", not self._export_context.asset_import_context.ignore_materials
            )
            self._preview_surface_checkbox = self._build_option_checkbox(
                "Import as UsdPreviewSurface",
                self._export_context.asset_import_context.export_preview_surface,
                "By default, materials will be imported as built-in MDLs.",
                indent=16,
            )
            self._preview_surface_checkbox.enabled = self._mat_checkbox.model.as_bool

            def _on_mat_value_change(model: ui.SimpleBoolModel, child_widget: ui.CheckBox):
                if child_widget:
                    child_widget.enabled = model.as_bool

            self._mat_model_sub = self._mat_checkbox.model.subscribe_value_changed_fn(
                partial(_on_mat_value_change, child_widget=self._preview_surface_checkbox)
            )

            self._animation_checkbox = self._build_option_checkbox(
                "Import Animation", not self._export_context.asset_import_context.ignore_animations
            )
            self._camera_checkbox = self._build_option_checkbox(
                "Import Cameras", not self._export_context.asset_import_context.ignore_camera
            )
            self._light_checkbox = self._build_option_checkbox(
                "Import Lights", not self._export_context.asset_import_context.ignore_light
            )

            self._bones_checkbox = self._build_option_checkbox(
                "Import Unbound Bones", not self._export_context.asset_import_context.ignore_unbound_bones
            )

            self._smooth_normals_checkbox = self._build_option_checkbox(
                "Generate Smooth Normals", self._export_context.asset_import_context.smooth_normals
            )
            self._meters_as_world_unit_checkbox = self._build_option_checkbox(
                "Use Meter as World Unit",
                self._export_context.asset_import_context.use_meter_as_world_unit,
                "Sets world units to meters, this will also scale asset if it's centimeters model.",
            )
            self._create_world_as_default_root_prim_checkbox = self._build_option_checkbox(
                "Create '/World' Default Prim",
                self._export_context.asset_import_context.create_world_as_default_root_prim,
            )
            self._merge_all_meshes_checkbox = self._build_option_checkbox(
                "Merge Static Meshes",
                self._export_context.asset_import_context.merge_all_meshes,
                "Only if all meshes are not skinned and they are under the same transform.",
            )
            if hasattr(self._export_context.asset_import_context, "ignore_flip_rotations"):
                self._rotation_checkbox = self._build_option_checkbox(
                    "Generate Smooth Rotations",
                    not self._export_context.asset_import_context.ignore_flip_rotations,
                    "It will filter the flip rotations in animation.",
                )
            self._convert_stage_up_combobox = self._build_option_combobox(
                default_index=0,
                items=["File Default", "Y-up", "Z-up"],
                text="Up-axis",
                tooltip="Override the converted asset's USD stage up-axis to either Y-up, Z-up, or default to the imported asset's up-axis",
            )

    def get_import_options(self):
        context = BuiltinImporterOptions()
        if self._built:
            context.asset_import_context.ignore_materials = not self._mat_checkbox.model.get_value_as_bool()
            context.asset_import_context.ignore_animations = not self._animation_checkbox.model.get_value_as_bool()
            context.asset_import_context.smooth_normals = self._smooth_normals_checkbox.model.get_value_as_bool()
            if hasattr(context.asset_import_context, "ignore_flip_rotations") and self._rotation_checkbox:
                context.asset_import_context.ignore_flip_rotations = (
                    not self._rotation_checkbox.model.get_value_as_bool()
                )
            context.asset_import_context.export_preview_surface = (
                self._preview_surface_checkbox.model.get_value_as_bool()
            )
            context.asset_import_context.use_meter_as_world_unit = (
                self._meters_as_world_unit_checkbox.model.get_value_as_bool()
            )
            context.asset_import_context.create_world_as_default_root_prim = (
                self._create_world_as_default_root_prim_checkbox.model.get_value_as_bool()
            )
            context.asset_import_context.merge_all_meshes = self._merge_all_meshes_checkbox.model.get_value_as_bool()
            context.asset_import_context.ignore_camera = not self._camera_checkbox.model.get_value_as_bool()
            context.asset_import_context.ignore_light = not self._light_checkbox.model.get_value_as_bool()
            context.asset_import_context.ignore_unbound_bones = not self._bones_checkbox.model.get_value_as_bool()
            up_axis = self._convert_stage_up_combobox.model.get_item_value_model(None, None).get_value_as_int()
            if up_axis == 1:
                context.asset_import_context.convert_stage_up_y = True
            elif up_axis == 2:
                context.asset_import_context.convert_stage_up_z = True

        return context

    def destroy(self):
        self._clear()
        self._mat_model_sub = None
        if self._file_picker:
            self._file_picker.destroy()

    def _build_option_checkbox(self, text, default_value, tooltip="", indent=0):
        with ui.HStack(height=0):
            if indent:
                ui.Spacer(width=indent, height=0)
            checkbox = ui.CheckBox(width=20)
            checkbox.model.set_value(default_value)
            label = ui.Label(text, alignment=ui.Alignment.LEFT, word_wrap=True)
            if tooltip:
                label.set_tooltip(tooltip)

            return checkbox

    def _build_option_combobox(self, default_index, items, text, tooltip="", indent=0):
        model = MinimalModal(default_index, items)
        with ui.HStack(width=0, spacing=4):
            if indent:
                ui.Spacer(width=indent, height=0)
            # can't use model= due to bug OM-43014
            combobox = ui.ComboBox(model, width=100)
            label = ui.Label(text, alignment=ui.Alignment.LEFT, word_wrap=True)
            if tooltip:
                label.set_tooltip(tooltip)

            return combobox
