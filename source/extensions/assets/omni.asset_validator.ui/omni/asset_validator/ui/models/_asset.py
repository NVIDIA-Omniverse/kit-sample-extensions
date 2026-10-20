# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from collections import deque
from enum import IntEnum
from functools import lru_cache

import omni.ui
from omni.asset_validator.core import is_omni_path
from pxr import Sdf, Usd

__all__ = [
    "AssetMode",
    "ModeItemModel",
    "ModeModel",
    "PrimsModel",
    "StageModel",
    "UriModel",
]


class AssetMode(IntEnum):
    Uri = 0
    """
    The asset is a URI
    """

    Stage = 1
    """
    The asset is a stage in memory.
    """

    Prims = 2
    """
    The asset is a list of prims.
    """


EMPTY_URI: str = ""


class UriModel(omni.ui.SimpleStringModel):
    def __init__(self):
        super().__init__(EMPTY_URI)

    @property
    def uri(self) -> str:
        return self.get_value_as_string()

    @uri.setter
    def uri(self, uri: str) -> None:
        self.set_value(uri)


class StageModel(omni.ui.AbstractValueModel):
    def __init__(self):
        super().__init__()
        self._stage = omni.usd.get_context().get_stage()

    @property
    def stage(self) -> Usd.Stage | None:
        return self._stage or omni.usd.get_context().get_stage()

    @stage.setter
    def stage(self, stage: Usd.Stage | None) -> None:
        self._stage = stage or omni.usd.get_context().get_stage()
        self._value_changed()

    def is_context_stage(self) -> bool:
        if self.stage is None:
            return False
        context_stage: Usd.Stage = omni.usd.get_context().get_stage()
        if context_stage is None:
            return False
        return self.stage.GetRootLayer() == context_stage.GetRootLayer()

    def get_value_as_string(self) -> str:
        if self.stage is None:
            return "Current stage is not available. Open a stage from the Stage or Layer Windows."
        elif self.is_context_stage():
            return "Validate the current stage."
        elif self.stage.GetRootLayer().anonymous:
            return f'Anonymous stage: "{self.stage.GetRootLayer().GetDisplayName()}"'
        else:
            return Usd.Describe(self.stage)


class PrimsModel(omni.ui.AbstractValueModel):

    def __init__(self):
        super().__init__()
        self._prims = []

    @property
    def prims(self) -> list[Sdf.Path]:
        return self._prims

    @prims.setter
    def prims(self, prims: list[Sdf.Path]) -> None:
        if self._prims != prims:
            self._prims = prims
            self._value_changed()

    @property
    def stage(self) -> Usd.Stage | None:
        original_stage: Usd.Stage = omni.usd.get_context().get_stage()
        if original_stage is None:
            return None

        mask: Usd.StagePopulationMask = Usd.StagePopulationMask()
        for path in self.prims:
            mask.Add(path)
        masked_stage: Usd.Stage = Usd.Stage.OpenMasked(
            original_stage.GetRootLayer(), original_stage.GetSessionLayer(), mask
        )
        return masked_stage

    @classmethod
    @lru_cache(maxsize=1)
    def _compute_suggestions(cls, stage: Usd.Stage) -> list[Sdf.Path]:
        suggestions: list[Sdf.Path] = []
        queue: deque[Usd.Prim] = deque([stage.GetPseudoRoot()])
        while queue:
            prim: Usd.Prim = queue.popleft()
            if is_omni_path(prim.GetPath()):
                continue
            suggestions.append(prim.GetPath())
            if len(suggestions) >= 100:
                break
            queue.extend(prim.GetChildren())
        return suggestions

    @property
    def suggestions(self) -> list[Sdf.Path]:
        context_stage: Usd.Stage = omni.usd.get_context().get_stage()
        if context_stage is None:
            return [Sdf.Path.absoluteRootPath]
        return self._compute_suggestions(context_stage)


class ModeModel(omni.ui.SimpleIntModel):
    def __init__(self) -> None:
        super().__init__(AssetMode.Stage.value)

    @property
    def mode(self) -> AssetMode:
        return AssetMode(self.get_value_as_int())

    @mode.setter
    def mode(self, mode: AssetMode) -> None:
        self.set_value(mode.value)


class ModeItemModel(omni.ui.AbstractItemModel):
    class Item(omni.ui.AbstractItem):
        def __init__(self, name: str):
            super().__init__()
            self.model = omni.ui.SimpleStringModel(name)

    def __init__(self, model: ModeModel):
        super().__init__()
        self._model = model
        self._subscription = self._model.subscribe_value_changed_fn(lambda _: self._item_changed(None))
        self._items = [
            ModeItemModel.Item(AssetMode.Uri.name),
            ModeItemModel.Item(AssetMode.Stage.name),
            ModeItemModel.Item(AssetMode.Prims.name),
        ]

    def get_item_children(self, item):
        if item is None:
            return self._items
        return []

    def get_item_value_model(self, item, _):
        if item is None:
            return self._model
        return item.model
