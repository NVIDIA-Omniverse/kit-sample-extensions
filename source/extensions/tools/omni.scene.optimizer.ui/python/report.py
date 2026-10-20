# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


import re
import sys
from functools import partial

import omni.ui as ui

from .report_widgets import *
from .style import *
from .utils import show_tooltip

MULTILINE_START = "[["
MULTILINE_END = "]]"


REPORT_MAP = {
    "Deduplicate Geometry": "Deduplicate",
    "Find Coincident Geometry": "Coinciding",
    "Merge Static Meshes": "Merge",
}


class Entry:
    """An individual report entry"""

    def __init__(self, level: str, category: str, message: str):
        self.level = level
        self.category = category
        self.message = message


class EntryGroup:
    """A group of report entries, typically for an operation"""

    def __init__(self, operation: str):
        self.operation = operation
        self.entries = list()
        self.time = None

    def build_widget(self, reportTab):
        """Build the UI to display report information for this operation"""

        # Map the operation name to the widget name
        key = self.operation
        if key in REPORT_MAP:
            key = REPORT_MAP[key]

        # Look up an operation-specific widget class. If not available, fall
        # back to the generic widget (a simple log entry table)
        cls = None
        try:
            cls = getattr(sys.modules[__name__], key + "Widget")
        except:
            cls = getattr(sys.modules[__name__], "GenericWidget")

        instance = cls(self.entries)
        instance.build_widget()

        # Cache the widget. See the ReportTab class for more info.
        reportTab.widgets.append(instance)


class Report:
    """Class to parse and cache a raw SceneOptimizer report in a slightly more
    convenient way so that custom widgets can access it.

    The general format of a report is lots of lines of:

    SEVERITY | CATEGORY | MESSAGE

    Messages can be multiline, indicated by a MESSAGE of "[[", with the real
    message payload beginning on the next line and continuing until a line with
    only "]]". This class will reconstruct those back to a single message entry.
    """

    def __init__(self, reportPath: str):
        """Create and initialize a report."""

        self._reportPath = reportPath

        self.entryGroups = list()

        self._build_report()

    def _build_report(self):
        """Parses a Scene Optimizer report out in to chunks per operation, simplified
        for access in various widgets.

        TODO: This only supports simple/single operations. Operations that call others
        and nest their reports are not yet supported.
        """

        regexBegin = re.compile(r"^BEGIN\s(.+)$")
        regexEnd = re.compile(r"^END\s(.+)\s\((\d+\.\d+s)\)$")

        # Read the whole report.
        f = open(self._reportPath)

        entryGroup = None
        inMultiline = False

        with open(self._reportPath) as f:

            for line in f:
                line = line.rstrip()

                # If we saw an open multiline statement then accumulate the message until
                # we see the end.
                if inMultiline:
                    if line == MULTILINE_END:
                        inMultiline = False
                    else:
                        entryGroup.entries[-1].message += line + "\n"

                    continue

                # Not in multiline, so we expect a standard set of fields.
                level, category, message = line.split("|", 2)

                # BEGIN: Start a new group.
                match = regexBegin.search(message)
                if match:
                    entryGroup = EntryGroup(match.group(1))
                    continue

                # END: Finish the current group.
                # Append the entryGroup and reset it.
                match = regexEnd.search(message)
                if match:
                    entryGroup.time = match.group(2)
                    self.entryGroups.append(entryGroup)
                    entryGroup = None
                    continue

                # Not begin/end, so append this entry to the current group.
                entryGroup.entries.append(Entry(level, category, message))

                # If the message itself is the multiline token, mark that we are now
                # processing multiline. Replaced the latest entry with an empty string
                # that we can append to.
                if message == MULTILINE_START:
                    entryGroup.entries[-1].message = ""
                    inMultiline = True
