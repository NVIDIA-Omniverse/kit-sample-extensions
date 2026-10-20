# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from collections.abc import Callable

import omni.usd
from pxr import Usd

from ..models._asset import AssetMode
from ..models._model import ApplicationModel
from ._icons import Icons


class StageMenu:

    def __init__(self, model: ApplicationModel, *, clicked_fn: Callable[[], None] | None = None):
        import omni.kit.context_menu

        self._model: ApplicationModel = model
        self._clicked_fn = clicked_fn
        self._stage_menu = omni.kit.context_menu.add_menu(
            {
                "name": "Validate Stage",
                "glyph": Icons.CONTEXT_MENU,
                "onclick_fn": self._validate_stage,
                "show_fn": self._show_stage,
            },
            "MENU",
            "omni.kit.widget.stage",
        )
        self._prims_menu = omni.kit.context_menu.add_menu(
            {
                "name": "Validate Prims",
                "glyph": Icons.CONTEXT_MENU,
                "onclick_fn": self._validate_prims,
                "show_fn": self._show_prims,
            },
            "MENU",
            "omni.kit.widget.stage",
        )

    def release(self):
        self._stage_menu = None
        self._prims_menu = None
        self._clicked_fn = None

    @property
    def clicked_fn(self) -> Callable[[], None]:
        return self._clicked_fn

    @clicked_fn.setter
    def clicked_fn(self, fn: Callable[[], None]) -> None:
        self._clicked_fn = fn

    def click(self) -> None:
        if self._clicked_fn:
            self._clicked_fn()

    def _show_stage(self, objects: dict) -> bool:
        import omni.kit.context_menu

        context_menu = omni.kit.context_menu.get_instance()
        return not context_menu.is_prim_selected(objects)

    def _show_prims(self, objects: dict) -> bool:
        import omni.kit.context_menu

        context_menu = omni.kit.context_menu.get_instance()
        return context_menu.is_prim_selected(objects)

    def _validate_stage(self, objects: dict) -> None:
        stage: Usd.Stage = objects["stage"]

        self._model.asset = stage
        self.click()

    def _validate_prims(self, objects: dict) -> None:
        self._model.mode = AssetMode.Prims
        self._model.prims = list(omni.usd.get_context().get_selection().get_selected_prim_paths())
        self.click()
