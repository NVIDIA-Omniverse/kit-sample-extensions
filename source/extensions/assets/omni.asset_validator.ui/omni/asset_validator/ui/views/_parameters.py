# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from functools import partial

from omni.asset_validator.core import ParameterType
from omni.ui import (
    Alignment,
    Button,
    CheckBox,
    CollapsableFrame,
    ComboBox,
    FloatField,
    HStack,
    IntField,
    Label,
    Spacer,
    Triangle,
    VStack,
)

from ..models._model import ApplicationModel
from ..models._options import OptionsItemModel
from ..models._parameters import EnumerationValueModel, ParametersModel, UserParameterGroupModel

__all__ = ["ParametersWidget"]


class ParametersWidget:
    def __init__(self, model: ParametersModel | None = None):
        self._model = OptionsItemModel(model or ApplicationModel.get().parameters_model)
        with VStack(height=0):
            with HStack(height=30):
                Button(text="Reset All", clicked_fn=self._reset_all)
            Spacer(height=10)
            for item in self._model.get_item_children(None):
                with CollapsableFrame(item.model.name, build_header_fn=partial(self._build_header_fn, item.model)):
                    with VStack():
                        for child_item in self._model.get_item_children(item):
                            with VStack():
                                with HStack():
                                    Label("Name:", width=64)
                                    Label(child_item.model.display_name)
                                with HStack():
                                    Label("Default:", width=64)
                                    Label(str(child_item.model.default_value))
                                with HStack():
                                    Label("Override:", width=64)
                                    match child_item.model.type:
                                        case ParameterType.INT:
                                            IntField(child_item.model)
                                        case ParameterType.FLOAT:
                                            FloatField(child_item.model)
                                        case ParameterType.BOOL:
                                            CheckBox(child_item.model)
                                        case ParameterType.ENUM:
                                            ComboBox(EnumerationValueModel(child_item.model))
                                        case _:
                                            continue
                                Spacer(height=10)

    def _reset_all(self) -> None:
        for item in self._model.get_item_children(None):
            for child_item in self._model.get_item_children(item):
                child_item.model.assigned_value = child_item.model.default_value

    def _build_header_fn(self, model: UserParameterGroupModel, collapsed: bool, title: str) -> None:
        alignment = Alignment.CENTER_BOTTOM if not collapsed else Alignment.RIGHT_CENTER
        with HStack():
            with VStack(width=10):
                Spacer()
                with HStack():
                    Spacer(width=3)
                    Triangle(alignment=alignment, width=8, height=8, style={"background_color": 0xFFFFFFFF})
                    Spacer(width=7)
                Spacer()
            Label(model.name)
            Spacer()
