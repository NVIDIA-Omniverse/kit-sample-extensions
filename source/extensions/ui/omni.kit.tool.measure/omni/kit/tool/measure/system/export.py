# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["ExportPanel"]

import os
import platform
import webbrowser
from pathlib import Path
from typing import List

import carb
import omni.usd as ou
from carb.settings import get_settings
from carb.tokens import get_tokens_interface
from omni import ui
from omni.kit.window.filepicker import FilePickerDialog

from ..common import EXPORT_FOLDER
from ..common.notification import post_info_notification, post_warn_notification
from ..interface.style import STYLE_BUTTON_DIRECTORY, STYLE_CHECKBOX
from ..manager import MeasurementManager
from ._measure_prim import MeasurePrim


def _export_csv(stage_url: str, export_folder: str, measure_prims: List[MeasurePrim]) -> None:
    stage_name = stage_url.split("/")[-1].split(".")[0]
    export_filepath = Path(f"{export_folder}/{stage_name}.csv")
    with export_filepath.open(mode="w") as f:
        f.write(f"{stage_url}\n")
        f.write("Name,UUID,Tool Mode,Tool Sub Mode,Prim Paths,Points,Unit Type,Value,Alt Value(s)\r")
        for m in measure_prims:
            p = m.payload

            # Precalculate data to help line length of write
            mode = p.tool_mode.name
            sub_mode = "N/A" if p.tool_sub_mode == -1 else p.tool_sub_mode
            points = ",".join([f"({vec[0]},{vec[1]},{vec[2]})" for vec in p.computed_points])
            unit = p.unit_type.value
            primary = p.primary_value
            secondary = "N/A" if len(p.secondary_values) == 0 else p.secondary_values

            f.write(f'{p.name},{p.uuid},{mode},{sub_mode},"{p.prim_paths}","{points}",{unit},{primary},"{secondary}"\r')


class ExportPanel(ui.Window):
    _WINDOW_NAME = "Measure Export"

    def __init__(self) -> None:
        self._settings = get_settings()
        export_dir = Path(get_tokens_interface().resolve("${documents}"))
        self._settings.set_default_string(EXPORT_FOLDER, str(export_dir.resolve()))

        self._filepicker = FilePickerDialog(
            "Select Measure Export Directory",
            allow_multi_selection=False,
            apply_button_label="Select",
            click_apply_handler=lambda _f, dir_name: self._on_export_dir_picked(dir_name),
        )
        self._filepicker.hide()

        super().__init__(
            title=self._WINDOW_NAME,
            name=self._WINDOW_NAME,
            auto_resize=True,
            padding_x=10,
            padding_y=10,
            flags=ui.WINDOW_FLAGS_NO_COLLAPSE
            | ui.WINDOW_FLAGS_NO_DOCKING
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR,
        )

        self.frame.set_build_fn(self._build_ui)

    @property
    def export_folder(self) -> str:
        return self._settings.get_as_string(EXPORT_FOLDER)

    @property
    def _export_path(self) -> str:
        return os.path.join(self.export_folder, f"{ou.get_context().get_stage_url().split('/')[-1].split('.')[0]}.csv")

    def destroy(self) -> None:
        self.visible = False
        super().destroy()

    def _on_browse_clicked(self) -> None:
        current_path = Path(self.export_folder)
        self._filepicker.show(str(current_path))

    def _on_export_dir_picked(self, export_directory: str) -> None:
        if export_directory.lower().startswith("bookmarks:"):
            post_warn_notification("Cannot export Measure data to the root bookmarks folder.")
            return
        elif export_directory.lower().startswith("omniverse:"):
            post_warn_notification("Cannot export Measure data to a Nucleus location.")
            return

        _export_dir = str(Path(export_directory))
        self._settings.set(EXPORT_FOLDER, _export_dir)
        self._export_dir_field.model.set_value(_export_dir)
        self._path_label.text = self._export_path
        self._filepicker.hide()

    def _on_export_clicked(self) -> None:
        stage_url = ou.get_context().get_stage_url()
        measure_prims: List[MeasurePrim] = MeasurementManager()._model.get_items()

        if len(measure_prims) > 0:
            _export_csv(stage_url, self.export_folder, measure_prims)
            if self._export_open_cb.model.as_bool:
                if platform.system() == "Windows":
                    os.startfile(self.export_folder)
                elif platform.system() == "Linux":
                    os.system(f"xdg-open {self.export_folder}")
                else:
                    webbrowser.open(self.export_folder)
            self.visible = False
            post_info_notification(f"Exported Measurement CSV Data to the path:\n{self._export_path}")
            return

        post_warn_notification("Failed to Export CSV: No Measurement Data To Export.")

    def _build_ui(self) -> None:
        with self.frame:
            with ui.VStack(spacing=4):
                with ui.HStack():
                    ui.Label("Export Directory")
                    ui.Spacer()
                with ui.HStack(height=24, spacing=4):
                    self._export_dir_field = ui.StringField(read_only=True, height=24, width=350)
                    self._export_dir_field.model.set_value(self._settings.get_as_string(EXPORT_FOLDER))
                    ui.Button(style=STYLE_BUTTON_DIRECTORY, width=24, height=24, clicked_fn=self._on_browse_clicked)
                # Set Initial path
                self._path_label = ui.Label(self._export_path, style={"font_size": 10}, width=350, elided_text=True)
                ui.Spacer(height=4)
                with ui.HStack(height=24, spacing=4):
                    ui.Spacer()
                    with ui.VStack(width=0):
                        ui.Spacer()
                        self._export_open_cb = ui.CheckBox(style=STYLE_CHECKBOX, width=12)
                        ui.Spacer()
                    ui.Label("Open folder on export")
                    ui.Button("Export", clicked_fn=self._on_export_clicked)
