# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from functools import singledispatchmethod

import omni.client
import omni.usd
from omni.asset_validator.core import (
    EditTargetId,
    Identifier,
    Issue,
    LayerId,
    PrimId,
    PropertyId,
    SchemaBaseId,
    StageId,
    Suggestion,
)
from omni.ui import AbstractItem, AbstractItemModel, AbstractValueModel

__all__ = ["FixAtItem", "FixAtItemModel", "FixAtModel", "SuggestionItemModel", "SuggestionModel"]


class FixAtModel(AbstractValueModel):
    def __init__(self, fix_sites: list[EditTargetId]):
        super().__init__()
        self._selected = 0
        self._fix_sites = fix_sites

    def set_value(self, value: int) -> None:
        self._selected = value
        self._value_changed()

    def get_value_as_int(self) -> int:
        return self._selected

    def reset(self, fix_sites: list[EditTargetId]) -> None:
        self._fix_sites = fix_sites
        self._selected = 0
        self._value_changed()

    @property
    def fix_sites(self) -> list[EditTargetId]:
        return self._fix_sites

    @property
    def fix_site(self) -> EditTargetId | None:
        if not self._fix_sites:
            return None
        return self._fix_sites[self._selected]


class FixAtItem(AbstractItem):
    """Every option in ComboBox."""

    def __init__(self, issue: Issue, target_id: EditTargetId):
        super().__init__()
        self.model = omni.ui.SimpleStringModel(self._format(issue, target_id))

    def _format(self, issue: Issue, target_id: EditTargetId) -> str:
        return f"{self._prefix(target_id)} {self._make_relative(self._path(issue.at), self._path(target_id))}"

    def _prefix(self, target_id: EditTargetId) -> str:
        if target_id.path is None:
            return ""
        elif target_id.path.IsPrimPath():
            return f"Prim({target_id.path}) at"
        elif target_id.path.IsPropertyPath():
            return f"Property({target_id.path}) at"
        else:
            return ""

    @singledispatchmethod
    def _path(self, identifier: Identifier) -> str:
        return ""

    @_path.register(LayerId)
    def _path_layer_id(self, identifier: LayerId) -> str:
        return identifier.identifier

    @_path.register(EditTargetId)
    def _path_spec_id(self, identifier: EditTargetId) -> str:
        return self._path(identifier.layer_id)

    @_path.register(StageId)
    def _path_stage_id(self, identifier: StageId) -> str:
        return self._path(identifier.root_layer)

    @_path.register(PrimId)
    def _path_prim_id(self, identifier: PrimId) -> str:
        return self._path(identifier.stage_id)

    @_path.register(PropertyId)
    def _path_property_id(self, identifier: PropertyId) -> str:
        return self._path(identifier.prim_id)

    @_path.register(SchemaBaseId)
    def _path_schema_base_id(self, identifier: SchemaBaseId) -> str:
        return self._path(identifier.prim_id)

    def _make_relative(self, base_path: str, path: str) -> str:
        url: omni.client.Url = omni.client.break_url(base_path)
        base_url: str = omni.client.make_url(
            url.scheme, url.user, url.host, url.port, url.path, url.query, url.fragment
        )
        url: omni.client.Url = omni.client.break_url(path)
        path_url: str = omni.client.make_url(
            url.scheme, url.user, url.host, url.port, url.path, url.query, url.fragment
        )
        return f"Layer({omni.client.make_relative_url(base_url, path_url)})"


class FixAtItemModel(AbstractItemModel):
    """
    Model for Nodes UI (ComboBox).
    """

    def __init__(self, model):
        super().__init__()
        self._model = model.as_fix
        self._issue = model.issue
        self._items = [FixAtItem(self._issue, fs) for fs in self._model.fix_sites]
        self._subscription = self._model.subscribe_value_changed_fn(self._on_fix_sites_changed)

    def _on_fix_sites_changed(self, _):
        self._items = [FixAtItem(self._issue, fs) for fs in self._model.fix_sites]
        self._item_changed(None)

    def get_item_children(self, _):
        return self._items

    def get_item_value_model(self, item, _):
        if item is None:
            return self._model
        return item.model

    @property
    def selected(self) -> EditTargetId | None:
        if not self._items:
            return None
        return self._model.fix_site


class SuggestionModel(AbstractValueModel):
    """Model for tracking which suggestion is currently selected."""

    def __init__(self, suggestions: tuple[Suggestion, ...]):
        super().__init__()
        self._suggestions = suggestions
        self._selected = 0

    def set_value(self, value: int) -> None:
        if value < 0 or value >= len(self._suggestions):
            raise IndexError(f"Suggestion index {value} out of range [0, {len(self._suggestions)})")
        self._selected = value
        self._value_changed()

    def get_value_as_int(self) -> int:
        return self._selected

    @property
    def suggestion(self) -> Suggestion | None:
        if not self._suggestions:
            return None
        return self._suggestions[self._selected]

    @property
    def suggestions(self) -> tuple[Suggestion, ...]:
        return self._suggestions


class _SuggestionItem(AbstractItem):
    """An item in the suggestion ComboBox."""

    def __init__(self, suggestion: Suggestion):
        super().__init__()
        self.model = omni.ui.SimpleStringModel(suggestion.message)


class SuggestionItemModel(AbstractItemModel):
    """Model for Suggestion ComboBox UI."""

    def __init__(self, suggestion_model: SuggestionModel):
        super().__init__()
        self._model = suggestion_model
        self._subscription = self._model.subscribe_value_changed_fn(lambda _: self._item_changed(None))
        self._items = [_SuggestionItem(s) for s in suggestion_model.suggestions]

    def get_item_children(self, _):
        return self._items

    def get_item_value_model(self, item, _):
        if item is None:
            return self._model
        return item.model
