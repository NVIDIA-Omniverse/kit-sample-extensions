# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

__all__ = ["AssetValidatorWidget"]

from collections.abc import Callable

import omni.ui
from omni.asset_validator.core import add_registry_rule_callback

from ..models._model import ApplicationModel
from ._asset import AssetWidget
from ._categories import CategoriesWidget
from ._commands import ClearFn, ValidatorCommandsWidget
from ._report import ResultsWidget
from ._settings import SettingsWidget

__all__ = ["AssetValidatorWidget", "EmbeddedValidatorWidget"]


class EmbeddedValidatorWidget:
    """
    An embedded widget for the extensions depending on the asset validator.
    """

    def __init__(
        self,
        *,
        model: ApplicationModel | None = None,
        offset_x_changed_fn: Callable[[omni.ui.Length], None] | None = None,
        show_mode_widget: bool = True,
    ) -> None:
        self._model = model or ApplicationModel.get()
        self._offset_x_changed_fn = offset_x_changed_fn
        self._show_mode_widget = show_mode_widget
        self._subscription = add_registry_rule_callback(self._update_categories)
        self._build_widget()

    @property
    def offset_x(self):
        return self._placer.offset_x

    @offset_x.setter
    def offset_x(self, value):
        self._placer.offset_x = value

    def reset(self, reset_assets: bool = False, reset_rules: bool = False) -> None:
        if reset_assets:
            self._model.uri = ""
            self._model.stage = None
        if reset_rules:
            self._model.categories_model.reset()
            self._model.results.clear()

    def _build_widget(self) -> None:
        with omni.ui.VStack():
            AssetWidget(visible=self._show_mode_widget)

            with omni.ui.HStack():
                with omni.ui.ZStack(width=0):
                    self._placer = omni.ui.Placer(
                        offset_x=300,
                        draggable=True,
                        drag_axis=omni.ui.Axis.X,
                        offset_x_changed_fn=self._offset_x_changed_fn,
                    )
                    with self._placer:
                        omni.ui.Rectangle(width=4, name="splitter")

                    with omni.ui.HStack():
                        self._panel = omni.ui.ScrollingFrame(build_fn=self._build_categories)
                        omni.ui.Spacer(width=4)

                with omni.ui.VStack():
                    SettingsWidget()
                    with omni.ui.VStack():
                        ResultsWidget()

            omni.ui.Spacer(width=0, height=10)
            ValidatorCommandsWidget(self._model)

    def _build_categories(self) -> None:
        CategoriesWidget(model=self._model.categories_model)

    def _update_categories(self) -> None:
        self._panel.rebuild()
        self._panel.scroll_y = 0
        ClearFn(self._model).apply()

    def destroy(self) -> None:
        self._placer = None
        self._subscription = None


AssetValidatorWidget = EmbeddedValidatorWidget
"""
.. deprecated:: 0.24.0
   Use :class:`EmbeddedValidatorWidget` instead.
"""
