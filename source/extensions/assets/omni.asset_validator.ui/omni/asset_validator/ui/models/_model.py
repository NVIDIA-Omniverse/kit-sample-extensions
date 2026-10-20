# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from functools import cache

from omni.asset_validator.core import AssetType, IssueGroupBy, ParameterMapping, ValidationEngine
from pxr import Sdf, Usd

from ..delegates import OptionsDelegate
from ._asset import AssetMode, ModeModel, PrimsModel, StageModel, UriModel
from ._capabilities import CapabilitiesModel
from ._categories import CategoriesModel
from ._features import FeaturesModel
from ._filters import FiltersModel
from ._group_by import GroupByModel
from ._options import OptionMode, OptionModeModel
from ._parameters import ParametersModel
from ._profiles import ProfilesModel
from ._results import ResultsModel
from ._settings import SettingsModel

__all__ = ["ApplicationModel"]


@dataclass
class ApplicationModel:
    """The main application model that holds all UI state.

    This class serves as the central data model for the Asset Validator application, managing all UI-related state including:

    - Asset information (URI, stage, validation mode)
    - Configuration settings (categories, capabilities)
    - User preferences (variant handling, root-only validation, persistence)
    - Validation results

    The model uses Omni UI's value models (AbstractValueModel and SimpleBoolModel) to enable reactive UI updates.

    Attributes:
        uri_model (UriModel): Model holding the asset URI
        stage_model (StageModel): Model holding the USD stage
        prims_model (PrimsModel): Model holding the asset prims
        mode_model (ModeModel): Model holding the validation mode
        categories_model (CategoriesModel): Model holding validation categories
        capabilities_model (CapabilitiesModel): Model holding validation capabilities
        features_model (FeaturesModel): Model holding validation features
        profiles_model (ProfilesModel): Model holding validation profiles
        parameters_model (ParametersModel): Model holding validation parameters
        options_mode_model (OptionModeModel): Model holding whether we validate categories or capabilities
        settings_model (SettingsModel): Model holding settings
        filters_model (FiltersModel): Model holding filters
        group_by_model (GroupByModel): Model holding grouping configuration
        results_model (ResultsModel): Model holding validation results
    """

    # Asset
    uri_model: UriModel = field(default_factory=UriModel)
    stage_model: StageModel = field(default_factory=StageModel)
    prims_model: PrimsModel = field(default_factory=PrimsModel)
    mode_model: ModeModel = field(default_factory=ModeModel)
    # Configurations
    categories_model: CategoriesModel = field(default_factory=CategoriesModel)
    capabilities_model: CapabilitiesModel = field(default_factory=CapabilitiesModel)
    features_model: FeaturesModel = field(default_factory=FeaturesModel)
    profiles_model: ProfilesModel = field(default_factory=ProfilesModel)
    parameters_model: ParametersModel = field(default_factory=ParametersModel)
    options_mode_model: OptionModeModel = field(default_factory=OptionModeModel)
    # Settings
    settings_model: SettingsModel = field(default_factory=SettingsModel)
    filters_model: FiltersModel = field(default_factory=FiltersModel)
    group_by_model: GroupByModel = field(default_factory=GroupByModel)
    # Results
    results_model: ResultsModel = field(default_factory=ResultsModel)
    _tasks: set[asyncio.Task] = field(init=False, default_factory=set)
    _options_delegate: OptionsDelegate = field(init=False, default=None)

    def __post_init__(self):
        self._options_delegate = OptionsDelegate(
            categories=self.categories_model,
            capabilities=self.capabilities_model,
            features=self.features_model,
            profiles=self.profiles_model,
        )

    # Asset
    @property
    def uri(self) -> str:
        """Get the asset URI."""
        return self.uri_model.uri

    @uri.setter
    def uri(self, value: str) -> None:
        """Set the asset URI."""
        self.uri_model.uri = value

    @property
    def stage(self) -> Usd.Stage:
        """Get the asset stage."""
        return self.stage_model.stage

    @stage.setter
    def stage(self, value: Usd.Stage) -> None:
        """Set the asset stage."""
        self.stage_model.stage = value

    @property
    def prims(self) -> list[Sdf.Path]:
        """Get the asset prims."""
        return self.prims_model.prims

    @prims.setter
    def prims(self, value: list[Sdf.Path]) -> None:
        """Set the asset prims."""
        self.prims_model.prims = value

    @property
    def mode(self) -> AssetMode:
        return self.mode_model.mode

    @mode.setter
    def mode(self, value: AssetMode) -> None:
        self.mode_model.mode = value

    @property
    def asset(self) -> AssetType:
        """Get the asset."""
        if self.mode is AssetMode.Uri:
            return self.uri
        elif self.mode is AssetMode.Stage:
            return self.stage
        elif self.mode is AssetMode.Prims:
            return self.prims_model.stage
        else:
            return None

    @asset.setter
    def asset(self, value: AssetType) -> None:
        """Set the asset."""
        if isinstance(value, str):
            self.mode = AssetMode.Uri
            self.uri = value
        elif isinstance(value, Usd.Stage):
            self.mode = AssetMode.Stage
            self.stage = value
        else:
            raise ValueError(f"Invalid asset type: {type(value)}")

    def reset_asset(self) -> None:
        """Reset the asset."""
        self.uri = ""
        self.stage = None
        self.prims = []

    # Configurations
    @property
    def options_mode(self) -> OptionMode:
        """Get the options mode."""
        return self.options_mode_model.mode

    @options_mode.setter
    def options_mode(self, mode: OptionMode) -> None:
        self.options_mode_model.mode = mode

    @property
    def group_by(self) -> IssueGroupBy:
        """Get the group by."""
        return self.group_by_model.group_by

    def create_engine(self) -> ValidationEngine:
        """Create a validation engine."""
        engine = ValidationEngine(
            init_rules=False,
            variants=self.settings_model.variants,
            instance_prototypes=self.settings_model.instance_prototypes,
        )
        for category in self.categories_model:
            for rule in category:
                if rule.selected:
                    engine.enable_rule(rule.value)
        for feature in self.features_model:
            for requirement in feature:
                if requirement.selected:
                    engine.enable_requirement(requirement.value)
        for capability in self.capabilities_model:
            for requirement in capability:
                if requirement.selected:
                    engine.enable_requirement(requirement.value)
        for profile in self.profiles_model:
            for capability in profile:
                if capability.selected:
                    engine.enable_capability(capability.value)
        engine_parameters: ParameterMapping = engine.parameters
        for parameters in self.parameters_model:
            for parameter in parameters:
                if not parameter.updated:
                    continue  # Parameter has not changed, skip it.
                elif parameter.parameter not in engine_parameters:
                    continue  # Parameter is not referenced by any rule or requirement, skip it.
                else:
                    engine.add_parameter(parameter.override)
        return engine

    # Results
    @property
    def results(self) -> ResultsModel:
        """Get the results model."""
        return self.results_model

    def reset_selection(self) -> None:
        """Reset the selection."""
        self._options_delegate.reset()
        self.results_model.clear()

    def add_task(self, task: asyncio.Task) -> None:
        """Add a task to the model."""
        task.add_done_callback(self._tasks.discard)
        self._tasks.add(task)

    def has_tasks(self) -> bool:
        return bool(self._tasks)

    async def wait_tasks(self) -> None:
        await asyncio.gather(*self._tasks)

    # Instance
    @classmethod
    @cache
    def get(cls) -> ApplicationModel:
        """Get the application model singleton."""
        return ApplicationModel()

    @classmethod
    def create(cls) -> ApplicationModel:
        """Create a new application model."""
        return ApplicationModel()
