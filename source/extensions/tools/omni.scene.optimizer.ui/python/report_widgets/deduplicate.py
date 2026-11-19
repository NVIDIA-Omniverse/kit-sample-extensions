# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


import re
from functools import partial

import omni.ui as ui

from ..utils import show_tooltip
from .deduplicate_detail import DeduplicateDetailPanel

CATEGORY = "DEDUPLICATE_GEOMETRY"
SUMMARY_PATTERN = re.compile(r"Found (\d+) sets? of equal meshes")


class DeduplicateWidget:
    def __init__(self, entries):
        """Initialise widget"""

        self._entries = entries

    def build_widget(self):
        """Build the actual widget"""

        # Default summary, will be used if the detailed message is not found
        summary = "No prims to process"

        for entry in self._entries:
            if entry.category != CATEGORY:
                continue

            match = re.match(SUMMARY_PATTERN, entry.message)
            if match:
                summary = entry.message
                break

        with ui.VStack(style={"margin": 0, "padding": 0}, height=ui.Percent(100)):

            ui.Label(
                summary,
                style={"margin": 10, "padding": 10, "alignment": ui.Alignment.CENTER},
            )

            with ui.HStack():

                ui.Spacer(width=ui.Fraction(30))

                ui.Button(
                    "Details",
                    width=ui.Fraction(40),
                    height=20,
                    clicked_fn=lambda: self._show_detail(),
                    style={"padding": 6},
                    tooltip_fn=partial(show_tooltip, "Inspect detailed results of what was or wasn't deduplicated"),
                )

                ui.Spacer(width=ui.Fraction(30))

    def _show_detail(self):
        """Show the deduplicate details panel"""
        self._detail = DeduplicateDetailPanel(self._entries)
