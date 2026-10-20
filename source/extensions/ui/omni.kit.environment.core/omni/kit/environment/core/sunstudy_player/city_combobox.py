# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni import ui

from ..models import CityModel


class CityComboBox(ui.ComboBox):
    """CityComboBox provides a combo box widget for selecting a city. It uses an internal CityModel to supply the list of available cities and inherits its base functionality from ui.ComboBox.

    Additional keyword arguments accepted by ui.ComboBox can be passed to customize the widget. No specific keyword arguments are defined by CityComboBox.

    Note:
        The drop down list is automatically populated using data from CityModel.
    """

    def __init__(self, **kwargs):
        self._city_model = CityModel()
        super().__init__(self._city_model, **kwargs)
