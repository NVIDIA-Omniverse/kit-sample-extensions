# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from omni.kit.widget.options_button import OptionsButton
from omni.kit.widget.options_menu import OptionItem, OptionRadios, OptionSeparator
from omni.ui import HStack, Spacer, color

from ..models._model import ApplicationModel
from ..models._options import OptionMode

__all__ = ["SettingsWidget"]


class SettingsWidget:
    """Build checkboxes for 'Variants', 'Show Issues on Root Layer only', and 'Save fixes' settings."""

    def __init__(self, model: ApplicationModel | None = None):
        self._model = model or ApplicationModel.get()
        style = {
            "Button": {"background_color": 0},
            "Button:selected": {"background_color": color.shade("#23211F")},
        }
        with HStack(height=0, style=style, width=28):
            Spacer(width=2)
            OptionsButton(
                [
                    OptionSeparator("Selections"),
                    OptionRadios(
                        [
                            ("Rules", OptionMode.CATEGORIES.name),
                            ("Requirements", OptionMode.CAPABILITIES.name),
                            ("Features", OptionMode.FEATURES.name),
                            ("Profiles", OptionMode.PROFILES.name),
                            ("Parameters", OptionMode.PARAMETERS.name),
                        ],
                        model=self._model.options_mode_model,
                    ),
                    OptionSeparator("Settings"),
                    OptionItem("variants", text="Enable variants", model=self._model.settings_model.variants_model),
                    OptionItem(
                        "instance_prototypes",
                        text="Validate instance prototypes",
                        model=self._model.settings_model.instance_prototypes_model,
                    ),
                    OptionItem("persist", text="Persist fixes", model=self._model.settings_model.persist_model),
                    OptionItem(
                        "autovalidate",
                        text="Validate after fix",
                        model=self._model.settings_model.autovalidate_model,
                    ),
                ],
            )
            Spacer(width=2)
