# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from ..models._model import ApplicationModel
from ..models._options import OptionsItemModel
from ..models._profiles import ProfilesModel
from ._options import OptionsWidget

__all__ = ["ProfilesWidget"]


class ProfilesWidget(OptionsWidget):
    def __init__(self, model: ProfilesModel | None = None):
        super().__init__(model=OptionsItemModel(model or ApplicationModel.get().profiles_model))
