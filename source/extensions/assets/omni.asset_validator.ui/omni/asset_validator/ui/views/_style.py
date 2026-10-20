# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from enum import Enum

from omni.asset_validator.core import Issue, IssuePredicates, IssueSeverity, IssuesList
from omni.ui import Alignment, CornerFlag, Direction, color

from ._icons import Icons

__all__ = ["STYLE", "ReportStyle"]

STYLE = {
    "ScrollingFrame": {"background_color": 0xFF333332},
    "Triangle::branch": {"background_color": 0xFFFFFFFF},
    "Line::border-bottom": {"color": 0xFFE0E0E0, "alignment": Alignment.V_CENTER},
    "Label::waiting": {"color": 0xFFFFFFFF},
    "Image::waiting": {"color": 0xFFFFFFFF},
    "Label::success": {"color": 0x60B0FFFF},
    "Image::success": {"color": 0x60B0FFFF},
    "Label::warning": {"color": 0xFF4ACBDF},
    "Image::warning": {"color": 0xFF4ACBDF},
    "Label::info": {"color": 0xFFE8A200},
    "Image::info": {"color": 0xFFE8A200},
    "Label::failed": {"color": 0xFF6060FF, "alignment": Alignment.LEFT_TOP},
    "Image::failed": {"color": 0xFF6060FF},
    "Label::suggestion": {"alignment": Alignment.LEFT_CENTER, "color": 0xFFBBBBBB, "margin": 4},
    "CheckBox": {"alignment": Alignment.V_CENTER},
    "TreeView": {"background_selected_color": 0x55555453, "secondary_color": 0xFF909090, "border_width": 1.5},
    "Rectangle::suggestion": {
        "background_color": 0xFF202020,
        "border_width": 1,
        "border_radius": 5,
    },
    "Rectangle::suggestion:hovered": {"background_color": 0xFF888888, "border_color": 0xFF353535},
    "Label::suggestion_disabled": {"alignment": Alignment.LEFT_CENTER, "color": 0xFFBBBBBB, "margin": 4},
    "Button::suggestion": {
        "background_color": 0xFF202020,
        "border_width": 1,
        "border_radius": 5,
    },
    "Button::suggestion:hovered": {"background_color": 0xFF888888, "border_color": 0xFF353535},
}

TAB_GROUP_STYLE = {
    "TabGroupBorder": {"background_color": color.transparent, "border_color": color(25), "border_width": 1},
    "Rectangle::TabGroupHeader": {
        "background_color": color(20),
    },
    "ZStack::TabGroupHeader": {"margin_width": 1},
}

TAB_STYLE = {
    "": {"background_color": color(31), "corner_flag": CornerFlag.TOP, "border_radius": 4, "color": color(127)},
    ":selected": {"background_color": color(56), "color": color(203)},
    "Label": {"margin_width": 5, "margin_height": 3},
}
PANEL_STYLE = {
    "Rectangle::splitter": {"background_color": 0x00000000, "margin": 0, "padding": 0},
    "Rectangle::splitter:hovered": {"background_color": 0xFFB0703B},
    "Rectangle::splitter:pressed": {"background_color": 0xFFB0703B},
}
FRAME_STYLE = {
    "Rectangle::splitter": {"background_color": 0x00000000, "margin": 0, "padding": 0},
    "Rectangle::splitter:hovered": {"background_color": 0xFFB0703B},
    "Rectangle::splitter:pressed": {"background_color": 0xFFB0703B},
}
COMMAND_STYLE = {
    "Button:disabled": {"background_color": color("#333332")},
    "Button.Label:disabled": {"color": color.gray},
    "Button::action": {"stack_direction": Direction.LEFT_TO_RIGHT},
    "Button.Label::action": {"alignment": Alignment.LEFT_CENTER},
    "Button.Image::action": {"alignment": Alignment.RIGHT_CENTER},
    "Button::action:disabled": {"background_color": color("#333332")},
    "Button.Label::action:disabled": {"alignment": Alignment.LEFT_CENTER, "color": color.gray},
    "Button.Image::action:disabled": {"alignment": Alignment.RIGHT_CENTER},
}


class ReportStyle(Enum):
    WAITING = ("waiting", Icons.WAITING)
    SUCCESS = ("success", Icons.SUCCESS)
    WARNING = ("warning", Icons.WARNING)
    FAILED = ("failed", Icons.ERROR)
    INFO = ("info", Icons.INFO)
    OUTDATED = ("waiting", Icons.WAITING)

    def __init__(self, style: str, icon: Icons):
        self._style = style
        self._icon = icon

    @property
    def style(self) -> str:
        return self._style

    @property
    def icon(self) -> Icons:
        return self._icon

    @classmethod
    def from_issue(cls, issue: Issue | None) -> ReportStyle:
        if issue is None:
            return ReportStyle.WAITING
        elif issue.severity is IssueSeverity.NONE:
            return ReportStyle.SUCCESS
        elif issue.severity is IssueSeverity.WARNING:
            return ReportStyle.WARNING
        elif issue.severity is IssueSeverity.FAILURE:
            return ReportStyle.FAILED
        elif issue.severity is IssueSeverity.ERROR:
            return ReportStyle.FAILED
        elif issue.severity is IssueSeverity.INFO:
            return ReportStyle.INFO

    @classmethod
    def from_issue_list(cls, issues: IssuesList) -> ReportStyle:
        if issues.count_if(IssuePredicates.Or(IssuePredicates.IsError(), IssuePredicates.IsFailure())) > 0:
            return ReportStyle.FAILED
        elif issues.count_if(IssuePredicates.IsWarning()) > 0:
            return ReportStyle.WARNING
        else:
            return ReportStyle.SUCCESS
