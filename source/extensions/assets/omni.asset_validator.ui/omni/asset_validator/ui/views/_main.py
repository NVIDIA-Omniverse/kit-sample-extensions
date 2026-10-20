# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from omni.asset_validator.core import add_registry_requirement_callback, add_registry_rule_callback
from omni.ui import HStack, ScrollingFrame, Spacer, VStack

from ..models._model import ApplicationModel
from ..models._options import OptionMode
from ._asset import AssetWidget
from ._capabilities import CapabilitiesWidget
from ._categories import CategoriesWidget
from ._commands import ClearFn, ValidatorCommandsWidget
from ._features import FeaturesWidget
from ._options import OptionModeViewsWidget
from ._panels import PanelWidget
from ._parameters import ParametersWidget
from ._profiles import ProfilesWidget
from ._report import ResultsWidget
from ._settings import SettingsWidget


class MainWidget:
    def __init__(self, model: ApplicationModel):
        self._model = model
        self._registry_rule_subscription = add_registry_rule_callback(self._update_panel)
        self._registry_requirement_subscription = add_registry_requirement_callback(self._update_panel)
        with VStack():
            AssetWidget(model=self._model)
            with VStack():
                self._panel = PanelWidget(
                    menu_build_fn=self._menu_build_fn,
                    view_build_fn=lambda: ResultsWidget(),
                )
                Spacer(height=10)
                ValidatorCommandsWidget(self._model)

    def _update_panel(self) -> None:
        self._panel.rebuild()
        ClearFn(self._model).apply()

    def _menu_build_fn(self) -> None:
        model = self._model.options_mode_model
        with VStack():
            with HStack(height=0):
                Spacer()
                SettingsWidget()
            with ScrollingFrame():
                OptionModeViewsWidget(model, build_fn=self._build_view)

    def _build_view(self, mode: OptionMode) -> None:
        match mode:
            case OptionMode.CATEGORIES:
                CategoriesWidget()
            case OptionMode.FEATURES:
                FeaturesWidget()
            case OptionMode.CAPABILITIES:
                CapabilitiesWidget()
            case OptionMode.PROFILES:
                ProfilesWidget()
            case OptionMode.PARAMETERS:
                ParametersWidget()
            case _:
                raise ValueError(f"Invalid option mode: {mode}")

    def destroy(self) -> None:
        self._model = None
        self._panel = None
        self._registry_rule_subscription = None
        self._registry_requirement_subscription = None
