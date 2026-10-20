# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from omni.kit.widget.options_button import OptionsButton
from omni.kit.widget.options_menu import OptionRadios
from omni.ui import HStack, Spacer

from ..models._group_by import GroupByOption
from ..models._model import ApplicationModel

__all__ = ["GroupByWidget"]


class GroupByWidget:
    def __init__(self, model: ApplicationModel | None = None):
        self._model = model or ApplicationModel.get()
        self._subscription = self._model.group_by_model.subscribe_value_changed_fn(self._on_value_changed_fn)
        with HStack(height=0, width=28):
            Spacer(width=2)
            OptionsButton(
                [
                    OptionRadios(
                        [
                            ("Group by rule", GroupByOption.RULE.value),
                            ("Group by requirement", GroupByOption.REQUIREMENT.value),
                        ],
                        model=self._model.group_by_model,
                    ),
                ]
            )
            Spacer(width=2)

    def _on_value_changed_fn(self, _):
        self._model.results.group_by = self._model.group_by_model.group_by
