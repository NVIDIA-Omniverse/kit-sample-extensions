# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from dataclasses import dataclass

import omni.ui
import omni.usd
from omni.asset_validator.core import (
    Identifier,
    Issue,
    IssuePredicates,
    IssueSeverity,
    IssuesList,
    PrimId,
    PropertyId,
    SchemaBaseId,
)
from pxr import Sdf

from ..commands import CopyAction, FixFn, SaveCSVAction
from ..models._asset import AssetMode
from ..models._model import ApplicationModel
from ..models._results import AssetResultsModel, GroupResultsModel, HasSelectedModel, IssueModel, ResultsModel
from ._filters import FilterWidget
from ._group_by import GroupByWidget
from ._icons import Icons
from ._identifiers import IdentifierLabel
from ._style import COMMAND_STYLE, STYLE, ReportStyle
from ._suggestion import SuggestionLocationWidget

__all__ = [
    "AssetItem",
    "GroupByItem",
    "IssueItem",
    "ReportModel",
    "ResultsWidget",
    "SuccessfulItem",
]

LEVEL_WIDTH = 20
EMPTY_LOCATION = "None"

SELECT_COLUMN = ""
ASSET_COLUMN = "Asset"
INFO_COLUMN = "Info"
SUGGEST_COLUMN = "Suggestion"
ACTION_COLUMN = "Action"
TREEVIEW_COLUMNS = [
    SELECT_COLUMN,
    ASSET_COLUMN,
    INFO_COLUMN,
    SUGGEST_COLUMN,
    ACTION_COLUMN,
]


@dataclass
class AssetStats:
    errors: int
    warnings: int
    failures: int

    def reset(self) -> None:
        self.errors = 0
        self.warnings = 0
        self.failures = 0


class TreeItem(omni.ui.AbstractItem):
    """
    A super class of all items in the tree. It adds selected, expanded and dumps.
    """

    def __init__(self, model: HasSelectedModel):
        super().__init__()
        self._model = model
        self._on_selected_id = model.selected_model.subscribe_value_changed_fn(self._on_selected_fn)
        self._children: list[TreeItem] = []

    def _on_selected_fn(self, _) -> None:
        for child in self.get_children():
            child._model.selected = self._model.selected

    def has_children(self) -> bool:
        return bool(self._children)

    def get_children(self) -> list[TreeItem]:
        return self._children

    def add_child(self, child: TreeItem) -> None:
        self._children.append(child)

    def clear_children(self) -> None:
        self._children.clear()

    def build_checkbox(self, enabled: bool = True) -> None:
        with omni.ui.VStack(width=12):
            omni.ui.Spacer(height=4)
            if enabled:
                omni.ui.CheckBox(self._model.selected_model)
            else:
                omni.ui.CheckBox(enabled=enabled)
            omni.ui.Spacer(height=4)

    def dumps(self) -> str:
        raise NotImplementedError()

    def build_branch(self, level: int, expanded: bool) -> None:
        with omni.ui.HStack(width=0, height=0):
            omni.ui.Spacer(width=level * LEVEL_WIDTH)
            if self.has_children():
                alignment = omni.ui.Alignment.CENTER_BOTTOM if expanded else omni.ui.Alignment.RIGHT_CENTER
                omni.ui.Spacer(width=3)
                omni.ui.Triangle(alignment=alignment, width=10, height=10, name="branch")
                omni.ui.Spacer(width=7)

    def build_label(self, label: str, style: ReportStyle, tooltip: str | None = None) -> omni.ui.Label:
        with omni.ui.HStack():
            omni.ui.Spacer(width=4)
            with omni.ui.VStack(width=16):
                omni.ui.Spacer(height=2)
                omni.ui.Image(style.icon, width=16, height=16, name=style.style)
                omni.ui.Spacer()
            omni.ui.Spacer(width=4)
            if tooltip is not None:
                return omni.ui.Label(label, word_wrap=True, tooltip=tooltip)
            else:
                return omni.ui.Label(label, word_wrap=True)

    def build_widget(self, column_id: int) -> None:
        raise NotImplementedError()


class ResultItem(TreeItem):
    def __init__(self, model: IssueModel):
        super().__init__(model)

    @property
    def issue(self) -> Issue | None:
        return self._model.issue

    @property
    def fix_status(self) -> str | None:
        return self._model.fix_status

    @property
    def style(self) -> ReportStyle:
        return ReportStyle.from_issue(self.issue)


class GroupByItem(TreeItem):
    def __init__(self, model: GroupResultsModel):
        super().__init__(model)
        self._on_value_changed_id = model.subscribe_value_changed_fn(self._on_value_changed_fn)
        self._on_value_changed_fn(model)

    def _on_value_changed_fn(self, _):
        self.clear_children()
        self.style = ReportStyle.WAITING
        if self._model.issues:
            issues = IssuesList([issue_model.issue for issue_model in self._model.issues])
            self.style = ReportStyle.from_issue_list(issues)
            for model in self._model.issues:
                if model.issue.severity is IssueSeverity.NONE:
                    self.add_child(SuccessfulItem(model))
                else:
                    self.add_child(IssueItem(model))

    def build_widget(self, column_id: int) -> None:
        if TREEVIEW_COLUMNS[column_id] == SELECT_COLUMN:
            self.build_checkbox()
        elif TREEVIEW_COLUMNS[column_id] == ASSET_COLUMN:
            self.build_label(self._model.name or "", self.style)

    def dumps(self) -> str:
        return f"GroupBy: {self._model.name}"


class AssetItem(TreeItem):
    def __init__(self, model: AssetResultsModel):
        super().__init__(model)
        self._groups: set[str] = set()
        self._on_value_changed_id = model.subscribe_value_changed_fn(self._on_value_changed_fn)
        self._on_value_changed_fn(model)

    def _on_value_changed_fn(self, model: AssetResultsModel) -> None:
        if not model.finished:
            self.style = ReportStyle.WAITING
            self.stats = AssetStats(0, 0, 0)
            for group_model in model.groups:
                if group_model.name not in self._groups:
                    self._groups.add(group_model.name)
                    self.add_child(GroupByItem(group_model))
        else:
            self._groups.clear()
            self.clear_children()
            if groups := model.groups:
                issues = IssuesList([issue_model.issue for issue_model in model.issues])
                self.style = ReportStyle.from_issue_list(issues)
                self.stats = AssetStats(
                    errors=issues.count_if(IssuePredicates.IsError()),
                    warnings=issues.count_if(IssuePredicates.IsWarning()),
                    failures=issues.count_if(IssuePredicates.IsFailure()),
                )
                for group_model in groups:
                    self.add_child(GroupByItem(group_model))
            else:
                self.style = ReportStyle.SUCCESS
                self.stats = AssetStats(0, 0, 0)
                self.add_child(SuccessfulItem(IssueModel(Issue.none())))

    def build_widget(self, column_id: int) -> None:
        if TREEVIEW_COLUMNS[column_id] == SELECT_COLUMN:
            self.build_checkbox()
        elif TREEVIEW_COLUMNS[column_id] == ASSET_COLUMN:
            if self.style is ReportStyle.WAITING:
                tooltip = "Waiting"
            else:
                tooltip = f"{self.stats.errors} errors, {self.stats.failures} failures, {self.stats.warnings} warnings"
            if self._model.outdated:
                self.build_label(f"(outdated) {self._model.asset_name or ''}", ReportStyle.OUTDATED, tooltip)
            else:
                self.build_label(self._model.asset_name or "", self.style, tooltip)
        elif TREEVIEW_COLUMNS[column_id] == INFO_COLUMN:
            omni.ui.ProgressBar(self._model.as_progress, style={"color": 0xFFFF9E3D, "margin_width": 8})

    def dumps(self) -> str:
        return f"Asset: {self._model.asset_id}"


class IssueItem(ResultItem):
    def __init__(self, model: IssueModel):
        super().__init__(model)
        self._info_label: omni.ui.Label | None = None
        self._on_value_changed_id = model.subscribe_value_changed_fn(self._on_value_changed_fn)

    def _on_value_changed_fn(self, _) -> None:
        if self._info_label:
            self._info_label.text = self._info_text()

    def _info_text(self) -> str:
        label = self.issue.message or ""
        if self.fix_status:
            label = f"({self.fix_status}) {label}"
        return label

    def build_widget(self, column_id: int) -> None:
        if TREEVIEW_COLUMNS[column_id] == SELECT_COLUMN:
            enabled: bool = self.issue.suggestion
            self.build_checkbox(enabled=enabled)
        elif TREEVIEW_COLUMNS[column_id] == ASSET_COLUMN:
            if self.issue.at:
                with omni.ui.HStack(style={"margin": 2}):
                    IdentifierLabel(self.issue.at)
        elif TREEVIEW_COLUMNS[column_id] == INFO_COLUMN:
            self._info_label = self.build_label(self._info_text(), self.style)
        elif TREEVIEW_COLUMNS[column_id] == SUGGEST_COLUMN:
            SuggestionLocationWidget(self._model)
        elif TREEVIEW_COLUMNS[column_id] == ACTION_COLUMN:
            with omni.ui.HStack(height=30, spacing=10, style=COMMAND_STYLE):
                if self.issue.suggestion:
                    omni.ui.Button(
                        " Apply",
                        clicked_fn=self._apply_fix,
                        image_url=Icons.FIX,
                        image_width=18,
                        image_height=18,
                        name="action",
                        spacing=4,
                        tooltip="Apply the selected suggestion",
                    )
                elif ApplicationModel.get().mode is not AssetMode.Uri and self.issue.at:
                    omni.ui.Button(
                        " Select",
                        clicked_fn=self._select_prim,
                        image_url=Icons.SELECT_PRIM,
                        image_width=18,
                        image_height=18,
                        name="action",
                        spacing=4,
                        tooltip="Select object(s) in stage",
                    )

    def _apply_fix(self) -> None:
        FixFn(issue=self.issue).apply()

    @staticmethod
    def _to_prim_paths(at) -> list[str]:
        if isinstance(at, tuple):
            locations = at
        elif at is not None:
            locations = [at]
        else:
            return []
        paths = []
        for loc in locations:
            if isinstance(loc, PrimId):
                paths.append(f"{loc.path}")
            elif isinstance(loc, PropertyId):
                paths.append(f"{loc.prim_id.path}")
            elif isinstance(loc, SchemaBaseId):
                paths.append(f"{loc.prim_id.path}")
            else:
                paths.append(f"{Sdf.Path.absoluteRootPath.pathString}")
        return paths

    def _select_prim(self) -> None:
        selection = omni.usd.get_context().get_selection()
        selection.set_selected_prim_paths(self._to_prim_paths(self.issue.at), False)

    def dumps(self) -> str:
        if isinstance(self.issue.at, tuple):
            location_str = ", ".join(loc.as_str() for loc in self.issue.at)
        elif isinstance(self.issue.at, Identifier):
            location_str = self.issue.at.as_str()
        else:
            location_str = EMPTY_LOCATION
        return f"{self.rule}, {self.issue.message}, {location_str}"


class SuccessfulItem(ResultItem):
    """No issues found message."""

    def __init__(self, model: IssueModel):
        super().__init__(model)

    def build_widget(self, column_id: int) -> None:
        if TREEVIEW_COLUMNS[column_id] == SELECT_COLUMN:
            self.build_checkbox(enabled=True)
        elif TREEVIEW_COLUMNS[column_id] == ASSET_COLUMN:
            self.build_label(self.dumps(), self.style)

    def dumps(self) -> str:
        return "No issues found"


ItemType = AssetItem | GroupByItem | IssueItem | SuccessfulItem
"""Alias of Asset, GroupBy and Issue items."""


class ReportModel(omni.ui.AbstractItemModel):
    """
    Data Model of Results, i.e. Assets and Issues.
    """

    def __init__(self, model: ResultsModel):
        super().__init__()
        self._model = model
        self._on_value_changed_id = model.subscribe_value_changed_fn(self._on_value_changed_fn)
        self._on_selected_id = model.selected_model.subscribe_value_changed_fn(self._on_selected_fn)
        self._assets = {}
        self._on_asset_changed_ids = []
        self._on_value_changed_fn(model)

    def _on_value_changed_fn(self, model: ResultsModel):
        updated: bool = False
        if not model.assets:
            updated = True
            self._assets.clear()
            self._on_asset_changed_ids.clear()
        else:
            for asset_model in model.assets:
                if asset_model.asset_id not in self._assets:
                    updated = True
                    item = AssetItem(asset_model)
                    self._assets[asset_model.asset_id] = item
                    self._on_asset_changed_ids.append(asset_model.subscribe_value_changed_fn(self._on_asset_changed))
        if updated:
            self._item_changed(None)

    def _on_asset_changed(self, asset: AssetResultsModel):
        if item := self._assets.get(asset.asset_id):
            self._item_changed(item)

    def _on_selected_fn(self, _) -> None:
        for asset_model in self._model.assets:
            asset_model.selected = self._model.selected

    def get_item_children(self, item: ItemType | None) -> list[ItemType]:
        """
        Override. Get the items at specific hierarchy.
        """
        if item is None:
            return list(self._assets.values())
        else:
            return item.get_children()

    @classmethod
    def get_item_value_model_count(cls, _: ItemType | None) -> int:
        """
        Override. Returns the number of columns.
        """
        return len(TREEVIEW_COLUMNS)

    def get_item_value_model(self, item, column_id):
        """
        Return value model.
        """
        if item is None:
            return self._model
        else:
            return None


class ReportTableDelegate(omni.ui.AbstractItemDelegate):
    """
    UI delegate to render `ReportModel` as a table.
    """

    def __init__(self, model: ResultsModel):
        super().__init__()
        self._model = model

    def build_branch(self, model, item, column_id, level, expanded) -> None:
        """
        Override. Build expand/collapse if applies.
        """
        if item and TREEVIEW_COLUMNS[column_id] == ASSET_COLUMN:
            item.build_branch(level, expanded)

    def build_widget(self, model, item, column_id, level, expanded) -> None:
        """
        Override. Build widgets for specific item.
        """
        if item:
            item.build_widget(column_id)

    def build_header(self, column_id: int) -> None:
        """
        Override. Build headers.
        """
        with omni.ui.ZStack():
            omni.ui.Rectangle(style={"background_color": 0xFF555453})
            if column_id == 0:
                with omni.ui.VStack():
                    omni.ui.Spacer(height=4)
                    omni.ui.CheckBox(self._model.selected_model)
                    omni.ui.Spacer()
            else:
                omni.ui.Label(
                    TREEVIEW_COLUMNS[column_id],
                    height=25,
                    alignment=omni.ui.Alignment.CENTER,
                )


# Report


class ResultsWidget:
    def __init__(self):
        self._app_model: ApplicationModel = ApplicationModel.get()
        self._model: ResultsModel = self._app_model.results
        self._item_model = ReportModel(self._model)
        self._item_delegate = ReportTableDelegate(self._model)
        with omni.ui.VStack():
            with omni.ui.HStack(height=0):
                FilterWidget(self._app_model)
                GroupByWidget(self._app_model)
            with omni.ui.ScrollingFrame(style=STYLE):
                omni.ui.TreeView(
                    self._item_model,
                    delegate=self._item_delegate,
                    root_visible=False,
                    column_widths=[
                        20,  # checkbox
                        omni.ui.Fraction(2),  # asset
                        omni.ui.Fraction(2),  # info
                        omni.ui.Fraction(2),  # suggestion + location
                        75,  # action
                    ],
                    columns_resizable=True,
                    header_visible=True,
                    mouse_pressed_fn=self._show_report_context_menu,
                )

    def _show_report_context_menu(self, x: int, y: int, button: int, modifier: int) -> None:
        """Build and show Context menu when mouse right click"""
        # Display context menu only if the right button is pressed
        if button != 1:
            return

        # Reset the previous context popup
        self._report_context_menu = omni.ui.Menu(menu_compatibility=False)
        with self._report_context_menu:
            omni.ui.MenuItem(
                "Copy Selected Issue Items",
                tooltip="Copy selected issue items",
                triggered_fn=CopyAction(self._app_model).apply,
                enabled=bool(self._model.selected_issues),
            )
            omni.ui.MenuItem(
                "Save Selected Issue Items",
                tooltip="Save selected issue items to csv file",
                triggered_fn=SaveCSVAction(self._app_model).apply,
                enabled=bool(self._model.selected_issues),
            )
        self._report_context_menu.show()
