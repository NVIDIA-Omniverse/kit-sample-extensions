# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from dataclasses import dataclass

import pyperclip
from omni.asset_validator.core import IssueCSVData

from ._base import CommandFn

__all__ = ["CopyAction"]

_FIX_RESULT_COLUMN = "Fix Result"


@dataclass
class CopyAction(CommandFn):
    """
    Command to copy the selected issues in the model to the clipboard in CSV format.
    It is invoked from a context menu in the report section of the UI.
    """

    async def apply_async(self) -> None:
        results = self.model.results
        csv_data = IssueCSVData.from_([model.issue for model in results.selected_issues])
        csv_data.append_column(
            _FIX_RESULT_COLUMN,
            [model.fix_status or "None" for model in results.selected_issues],
        )
        pyperclip.copy(csv_data.get_csv_as_str())
