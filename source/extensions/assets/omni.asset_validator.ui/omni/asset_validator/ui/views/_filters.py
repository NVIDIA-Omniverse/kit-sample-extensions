# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from omni.kit.widget.filter import FilterButton
from omni.kit.widget.options_menu import OptionItem, OptionSeparator
from omni.kit.widget.searchfield import SearchField
from omni.ui import HStack

from ..models._model import ApplicationModel

__all__ = ["FilterWidget"]


class FilterWidget:

    def __init__(self, model: ApplicationModel | None = None):
        self._model = model or ApplicationModel.get()
        self._report_context_menu = None
        self._subscriptions = [
            option_model.subscribe_value_changed_fn(self._on_predicate_update)
            for option_model in self._model.filters_model.options_models
        ]
        with HStack(height=0):
            SearchField(on_search_fn=self._on_search_fn)
            FilterButton(
                [
                    OptionItem("Show root only issues", model=self._model.filters_model.root_only_model, default=False),
                    OptionItem(
                        "Show only issues with fixes", model=self._model.filters_model.fixes_model, default=False
                    ),
                    OptionSeparator(),
                    OptionItem("Show errors", model=self._model.filters_model.errors_model, default=True),
                    OptionItem("Show failures", model=self._model.filters_model.failures_model, default=True),
                    OptionItem("Show warnings", model=self._model.filters_model.warnings_model, default=True),
                    OptionItem("Show infos", model=self._model.filters_model.info_model, default=True),
                    OptionItem("Show success", model=self._model.filters_model.success_model, default=False),
                    OptionSeparator(),
                    OptionItem("Show tag essential", model=self._model.filters_model.essential_model, default=True),
                    OptionItem("Show tag correctness", model=self._model.filters_model.correctness_model, default=True),
                    OptionItem("Show tag limitations", model=self._model.filters_model.limitations_model, default=True),
                    OptionItem("Show tag performance", model=self._model.filters_model.performance_model, default=True),
                    OptionItem("Show other tags", model=self._model.filters_model.other_tags_model, default=True),
                ]
            )

    def _on_search_fn(self, tokens: list[str] | None):
        if tokens is not None:
            self._model.filters_model.tokens = tokens
            self._model.results.apply_filter(self._model.filters_model.predicate)
        else:
            self._model.filters_model.tokens = []
            self._model.results.apply_filter(self._model.filters_model.predicate)

    def _on_predicate_update(self, _):
        self._model.results.apply_filter(self._model.filters_model.predicate)
