# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from dataclasses import dataclass

import omni.client
from omni.asset_validator.core import IssueCSVData
from omni.kit.window.file_exporter import get_file_exporter

from ._base import CommandFn

__all__ = ["SaveCSVAction"]

_FIX_RESULT_COLUMN = "Fix Result"


@dataclass
class SaveCSVAction(CommandFn):
    """
    Command to save the selected issues in the model to a CSV file.
    It is invoked from a context menu in the report section of the UI.
    """

    def export_csv(self, file_name: str, dir_name: str, extension: str, selections: list[str]) -> None:
        """
        Exports the selected issues in the model to a CSV file.

        Args:
            file_name: The name of the CSV file.
            dir_name: The directory where the CSV file will be saved.
            extension: The file extension.
            selections: The files selected in the file export dialog.
        """
        extension = extension or ".csv"
        file_url = omni.client.combine_urls(dir_name, f"{file_name}{extension}")
        results = self.model.results
        csv_data = IssueCSVData.from_([model.issue for model in results.selected_issues])
        csv_data.append_column(
            _FIX_RESULT_COLUMN,
            [model.fix_status or "None" for model in results.selected_issues],
        )
        csv_data.export_csv(file_url)

    async def apply_async(self) -> None:
        file_exporter = get_file_exporter()
        if file_exporter:
            file_exporter.show_window(
                title="Save as CSV",
                export_button_label="Save",
                export_handler=self.export_csv,
                file_extension_types=[(".csv", "CSV Files")],
                show_only_folders=False,
                enable_filename_input=True,
            )
