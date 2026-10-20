import os

import omni
import omni.ui

try:
    from omni.kit.widget.farm import FarmSettingsWidget, FarmSubmissionWidget, TaskDefinition

    ENABLE_FARM_SUBMISSION = True
except Exception as exc:
    ENABLE_FARM_SUBMISSION = False

from .common import BAKE_MDL_SUPPORTED

# Kit 111 EA1: MDL baking (omni.mdl.distill_and_bake) is not supported, so the "Export Baked MDL" option is hidden.
ENABLE_BAKE_MATERIAL = BAKE_MDL_SUPPORTED

from typing import Callable, List, Tuple

from omni.kit.asset_converter import AssetConverterContext


class ExportOptionsWindow:
    def __init__(self, import_fn, modal=False, farm_export_fn: Callable[[], Tuple[str, str]] = None):
        super().__init__()
        self._export_fn = import_fn
        self._farm_export_fn = farm_export_fn
        self._farm_settings_widget = None
        self._farm_submit_button = None
        self._window = None
        self._modal = modal
        self._build_window()

    # exclude from coverage because extension shutdown is not covered
    def destroy(self):  # pragma: no cover
        if self._export_button:
            self._export_button.set_clicked_fn(None)

        if self._cancel_button:
            self._cancel_button.set_clicked_fn(None)

        self._separate_gltf_container = None
        self._export_animations_containter = None
        self._mdl_gltf_extension_container = None
        self._export_animations_checkbox = None
        self._export_baked_mdl_checkbox = None
        self._export_lights_checkbox = None
        self._embed_textures_checkbox = None
        self._embed_textures_container = None
        self._export_cameras_checkbox = None
        self._export_materials_checkbox = None
        self._export_visible_only_checkbox = None
        self._export_separate_gltf_checkbox = None
        self._export_mdl_gltf_extension_checkbox = None

    def set_import_fn(self, import_fn):
        self._export_fn = import_fn

    def set_farm_export_fn(self, farm_export_fn):
        self._farm_export_fn = farm_export_fn

    def _build_window(self):
        self._window = omni.ui.Window(
            "Export Options", visible=False, height=0, dockPreference=omni.ui.DockPreference.DISABLED
        )
        self._window.flags = (
            omni.ui.WINDOW_FLAGS_NO_COLLAPSE | omni.ui.WINDOW_FLAGS_NO_RESIZE | omni.ui.WINDOW_FLAGS_NO_SCROLLBAR
        )
        if self._modal:
            self._window.flags = self._window.flags | omni.ui.WINDOW_FLAGS_MODAL

        with self._window.frame:
            with omni.ui.VStack(height=0):
                omni.ui.Spacer(width=0, height=20)
                self._export_materials_checkbox, _ = self._build_option_checkbox("Export Materials and Textures", True)
                self._export_animations_checkbox, self._export_animations_containter = self._build_option_checkbox(
                    "Export Animations", True
                )
                self._export_cameras_checkbox, _ = self._build_option_checkbox("Export Cameras", True)
                self._export_lights_checkbox, _ = self._build_option_checkbox("Export Lights", True)
                self._embed_textures_checkbox, self._embed_textures_container = self._build_option_checkbox(
                    "Embed Textures", True, tooltip="Currently, only FBX and glTF export supports this option."
                )
                self._export_visible_only_checkbox, _ = self._build_option_checkbox(
                    "Export Visible Only", True, tooltip="Only visible prims will be exported if it's enabled."
                )
                if ENABLE_BAKE_MATERIAL:
                    self._export_baked_mdl_checkbox, _ = self._build_option_checkbox(
                        "Export Baked MDL",
                        False,
                        tooltip="Baking MDL into UsdPreviewSurface before export if it's enabled.",
                    )
                else:
                    self._export_baked_mdl_checkbox = None
                self._export_separate_gltf_checkbox, self._separate_gltf_container = self._build_option_checkbox(
                    "Separate .bin for Gltf",
                    False,
                    tooltip="Gltf with Separate bin file will be exported if it's enabled.",
                )
                (
                    self._export_mdl_gltf_extension_checkbox,
                    self._mdl_gltf_extension_container,
                ) = self._build_option_checkbox(
                    "Export glTF NV_materials_mdl",
                    False,
                    tooltip="Materials will be exported with the NV_materials_mdl glTF extension.",
                )

                if ENABLE_FARM_SUBMISSION:
                    self._farm_settings_widget = FarmSettingsWidget()
                    self._farm_settings_widget.build_ui()
                    omni.ui.Spacer(width=0, height=10)

                with omni.ui.HStack(height=0):
                    omni.ui.Spacer(height=0)
                    self._export_button = omni.ui.Button("Export", name="export", width=80, height=0)
                    self._export_button.set_clicked_fn(self._on_export_fn)
                    omni.ui.Spacer(width=5, height=0)
                    self._cancel_button = omni.ui.Button("Cancel", name="cancel", width=80, height=0)
                    self._cancel_button.set_clicked_fn(self._on_cancel_fn)
                    if ENABLE_FARM_SUBMISSION:
                        omni.ui.Spacer(width=5, height=0)
                        self._farm_submit_button = FarmSubmissionWidget(
                            task_definition_fn=self._on_farm_export_fn,
                            farm_server_fn=self._farm_settings_widget.get_selected_farm,
                            finalize_fn=self.hide,
                        )
                    omni.ui.Spacer(height=0)
                omni.ui.Spacer(width=0, height=10)

    def _get_context(self) -> AssetConverterContext:
        asset_upload_context = AssetConverterContext()
        asset_upload_context.embed_textures = self._embed_textures_checkbox.model.get_value_as_bool()
        asset_upload_context.ignore_animations = not self._export_animations_checkbox.model.get_value_as_bool()
        asset_upload_context.ignore_light = not self._export_lights_checkbox.model.get_value_as_bool()
        asset_upload_context.ignore_camera = not self._export_cameras_checkbox.model.get_value_as_bool()
        asset_upload_context.ignore_materials = not self._export_materials_checkbox.model.get_value_as_bool()
        asset_upload_context.export_hidden_props = not self._export_visible_only_checkbox.model.get_value_as_bool()
        asset_upload_context.bake_mdl_material = (
            self._export_baked_mdl_checkbox.model.get_value_as_bool() if self._export_baked_mdl_checkbox else False
        )
        asset_upload_context.export_separate_gltf = self._export_separate_gltf_checkbox.model.get_value_as_bool()
        asset_upload_context.export_mdl_gltf_extension = (
            self._export_mdl_gltf_extension_checkbox.model.get_value_as_bool()
        )

        return asset_upload_context

    def _on_export_fn(self):
        if self._export_fn:
            asset_upload_context = self._get_context()
            self._export_fn(asset_upload_context)
        self._window.visible = False

    def _on_cancel_fn(self):
        self._window.visible = False

    def _on_farm_export_fn(self) -> List["TaskDefinition"]:
        if not self._farm_export_fn:
            return []

        usd_file, output_path = self._farm_export_fn()
        asset_upload_context = self._get_context()

        tasks = []
        tasks.append(
            TaskDefinition(
                task_type="convert-asset",
                task_function="convert.asset.process",
                task_function_args={
                    "import_path": usd_file,
                    "output_path": output_path,
                    "converter_settings": asset_upload_context.to_dict(),
                },
                task_comment=self._farm_settings_widget.get_task_comment(),
            )
        )

        return tasks

    def _build_option_checkbox(self, text, default_value, tooltip=None):
        container = omni.ui.VStack(height=0)
        with container:
            with omni.ui.HStack(height=0):
                omni.ui.Spacer(width=80, height=0)
                checkbox = omni.ui.CheckBox(width=20, style={"font_size": 16})
                checkbox.model.set_value(default_value)
                omni.ui.Label(text, alignment=omni.ui.Alignment.LEFT)
                omni.ui.Spacer(width=80, height=0)
            omni.ui.Spacer(width=0, height=10)

        if tooltip:
            container.set_tooltip(tooltip)

        return (checkbox, container)

    def show(self, output_path: str):
        self._window.visible = True
        self._window.height = 0
        self._separate_gltf_container.visible = False
        self._mdl_gltf_extension_container.visible = False
        self._export_animations_containter.visible = False
        self._embed_textures_container.visible = False
        if output_path:
            _, ext = os.path.splitext(output_path)
            ext = ext.lower()
            if ext == ".gltf" or ext == ".glb" or ext == ".fbx":
                self._export_animations_containter.visible = True
                self._embed_textures_container.visible = True
            if ext == ".gltf" or ext == ".glb":
                self._separate_gltf_container.visible = True
                self._mdl_gltf_extension_container.visible = True

    def hide(self):
        self._window.visible = False

    def is_visible(self):
        return self._window.visible
