# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from functools import partial

import omni.ui
from omni.asset_validator.core import EditTargetId, IssueSeverity

from ..models._fix import FixAtItem
from ..models._results import IssueModel
from ._icons import Icons

__all__ = ["SuggestionLocationWidget"]


class SuggestionLocationWidget:
    """Label + dropdown for selecting a fix suggestion and its target location."""

    def __init__(self, issue_model: IssueModel) -> None:
        self._model = issue_model
        self._label: omni.ui.Label | None = None
        self._menu: omni.ui.Menu | None = None
        self._suggestion_sub = issue_model.as_suggestion.subscribe_value_changed_fn(self._on_model_changed)
        self._fix_sub = issue_model.as_fix.subscribe_value_changed_fn(self._on_model_changed)

        if not self._model.issue.suggestions:
            if self._model.issue.severity != IssueSeverity.INFO:
                omni.ui.Label("Fix Manually", word_wrap=True, name="suggestion_disabled")
            return

        with omni.ui.HStack(style={"margin": 2, "spacing": 0}):
            self._label = omni.ui.Label(
                self.current_label,
                word_wrap=True,
                name="suggestion",
            )
            omni.ui.Button(
                "",
                image_url=Icons.ARROW_DOWN,
                image_width=12,
                image_height=12,
                clicked_fn=self._show_menu,
                width=20,
                name="suggestion",
                tooltip="Select fix strategy and location",
            )

    @property
    def current_label(self) -> str:
        """Current selection as ``"{suggestion} at {location}"``, or just the suggestion message if no fix site is set."""
        suggestion = self._model.as_suggestion.suggestion
        if not suggestion:
            return ""
        site = self._model.fix_at
        if site is None:
            return suggestion.message
        return f"{suggestion.message} at {self._location_label(site)}"

    def _on_model_changed(self, _) -> None:
        if self._label:
            self._label.text = self.current_label

    def _location_label(self, site: EditTargetId) -> str:
        return FixAtItem(self._model.issue, site).model.get_value_as_string()

    def _show_menu(self) -> None:
        suggestions = self._model.as_suggestion.suggestions
        self._menu = omni.ui.Menu(menu_compatibility=False)
        with self._menu:
            for suggestion_index, suggestion in enumerate(suggestions):
                for location_index, site in enumerate(self._model.issue.fix_sites_for(suggestion)):
                    omni.ui.MenuItem(
                        f"{suggestion.message} at {self._location_label(site)}",
                        triggered_fn=partial(self._select, suggestion_index, location_index),
                    )
        self._menu.show()

    def _select(self, suggestion_index: int, location_index: int) -> None:
        self._model.as_suggestion.set_value(suggestion_index)
        self._model.as_fix.set_value(location_index)
