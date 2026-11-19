# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


import omni.ui as ui

from .generic import GenericWidget
from .merge_results import MergeResultsPanel


class MergeWidget(GenericWidget):
    def __init__(self, entries):
        # Filter out INFO used to build the Merge Results GUI, show only errors and warnings in the log table.
        filtered_entries = list(filter(lambda e: e.level != "INFO", entries))
        # Always add the last log entry (summary of the operation).
        filtered_entries.append(entries[-1])
        super().__init__(filtered_entries)
        self._entries = entries
        self._button = None
        self._merge_results_panel = None

    def build_widget(self):
        with ui.VStack(style={"margin": 0, "padding": 0}, height=ui.Percent(100)):
            # Build the log view.
            super().build_widget(height=0)
            with ui.VStack(style={"margin": 0, "padding": 0}):
                self._button = ui.Button(
                    "Merge Results",
                    width=ui.Percent(100),
                    height=20,
                    clicked_fn=lambda: self._on_show_merge_results_clicked(),
                )

    def _on_show_merge_results_clicked(self):
        self._merge_results_panel = MergeResultsPanel(self._entries)
