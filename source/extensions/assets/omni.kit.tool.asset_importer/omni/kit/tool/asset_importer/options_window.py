__all__ = ["OptionsWindow"]

import os

import omni.kit.window.content_browser as content
import omni.ui as ui

try:
    from omni.kit.widget.farm import FarmSettingsWidget, FarmSubmissionWidget, TaskDefinition

    ENABLE_FARM_SUBMISSION = True
except Exception as exc:
    ENABLE_FARM_SUBMISSION = False

from pathlib import Path
from typing import List

from .importers_manager import ImportersManager


class OptionsWindow:
    def __init__(self, usd_context, importers_manager: ImportersManager, modal=False):
        super().__init__()
        self._usd_context = usd_context
        self._import_fn = None
        self._window = ui.Window(
            "Convert Options",
            visible=False,
            height=400,
            dockPreference=ui.DockPreference.DISABLED,
        )
        self._window.flags = ui.WINDOW_FLAGS_NO_COLLAPSE | ui.WINDOW_FLAGS_NO_SCROLLBAR | ui.WINDOW_FLAGS_NO_DOCKING

        if modal:
            self._window.flags = self._window.flags | ui.WINDOW_FLAGS_MODAL

        self._asset_paths = []
        self._export_to_current_folder = True
        self._importers_manager = importers_manager

        self._farm_settings_widget = None
        self._farm_submit_button = None

    def set_import_fn(self, import_fn):
        self._import_fn = import_fn

    def _build_window(self):
        with self._window.frame:
            with ui.VStack():
                with ui.ScrollingFrame():
                    with ui.VStack():
                        self._importers_manager.build_options_pane(self._asset_paths, False)
                        if ENABLE_FARM_SUBMISSION:
                            self._farm_settings_widget = FarmSettingsWidget()
                            self._farm_settings_widget.build_ui()
                with ui.HStack(height=0, spacing=5):
                    ui.Spacer(height=0)  # Fill left-side space.
                    ui.Button("Convert", width=80, height=0, clicked_fn=self._on_import_fn)
                    ui.Button("Cancel", width=80, height=0, clicked_fn=self._on_cancel_fn)
                    if ENABLE_FARM_SUBMISSION:
                        self._farm_submit_button = FarmSubmissionWidget(
                            task_definition_fn=self._collect_tasks,
                            farm_server_fn=self._farm_settings_widget.get_selected_farm,
                            finalize_fn=self.hide,
                        )

    def _collect_tasks(self) -> List["TaskDefinition"]:
        context = self._importers_manager._builtin_importer._options_builder.get_import_options()
        convert_settings = context.asset_import_context.to_dict()

        folder = self._importers_manager._shared_options_builder.get_options().export_folder
        file_format = self._importers_manager._shared_options_builder.get_options().export_file_format
        if not folder.endswith("/"):
            folder += "/"

        tasks = []
        for asset_path in self._asset_paths:
            output_path = folder + os.path.basename(asset_path) + file_format
            tasks.append(
                TaskDefinition(
                    task_type="convert-asset",
                    task_function="convert.asset.process",
                    task_function_args={
                        "import_path": asset_path,
                        "output_path": output_path,
                        "converter_settings": convert_settings,
                    },
                    task_comment=self._farm_settings_widget.get_task_comment(),
                )
            )

        return tasks

    def _on_import_fn(self):
        if self._import_fn:
            self._import_fn(self._asset_paths)
        self._window.visible = False

    def destroy(self):
        self._import_fn = None
        self._window = None
        self._importers_manager = None

        if self._farm_settings_widget:
            self._farm_settings_widget.destroy()
            self._farm_settings_widget = None
        self._farm_submit_button = None

    def _on_cancel_fn(self):
        self._window.visible = False

    def hide(self):
        self._window.visible = False

    def show(self, asset_paths, export_to_current_folder=True):
        self._asset_paths = asset_paths
        self._export_to_current_folder = export_to_current_folder

        # Sets the default export folder
        folder = self._get_export_folder()
        self._importers_manager.set_builtin_importer_default_target_folder(folder)
        self._importers_manager.set_builtin_importer_default_target_file_name(asset_paths)
        self._build_window()
        self._window.visible = True

    def _get_export_folder(self):
        # Sets the default export folder
        stage = self._usd_context.get_stage()
        if self._export_to_current_folder:
            export_folder = self._get_current_dir_in_content_window()
        elif not stage or stage.GetRootLayer().anonymous:
            export_folder = None
        else:
            export_folder = os.path.dirname(stage.GetRootLayer().identifier)

        if export_folder and len(self._asset_paths) == 1:
            if export_folder.endswith("/"):
                export_folder = export_folder[:-1]
            export_folder += "/" + Path(self._asset_paths[0]).stem
        elif not export_folder:
            export_folder = ""

        return export_folder

    @property
    def visible(self):
        return self._window.visible

    def _get_current_dir_in_content_window(self):
        content_window = content.get_content_window()
        return content_window.get_current_directory()
