# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from ..models._features import FeaturesModel
from ..models._model import ApplicationModel
from ..models._options import OptionsItemModel
from ._options import OptionsWidget

__all__ = ["FeaturesWidget"]


class FeaturesWidget(OptionsWidget):
    def __init__(self, model: FeaturesModel | None = None):
        super().__init__(model=OptionsItemModel(model or ApplicationModel.get().features_model))
