# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import List, Optional

from omni import ui

PRESET_CITIES = {
    "Abu Dhabi": (24.4428, 54.5291),
    "Amsterdam": (52.3611, 4.8901),
    "Atlanta": (33.7474, -84.3973),
    "Barcelona": (41.4027, 2.1599),
    "Beijing": (39.9094, 116.3931),
    "Berlin": (52.507, 13.4083),
    "Brussels": (50.8591, 4.3701),
    "Chicago": (41.8709, -87.7791),
    "Copenhagen": (55.6697, 12.5662),
    "Dallas": (32.7915, -96.8059),
    "Denver": (39.7524, -104.9799),
    "Dubai": (25.1345, 55.2827),
    "Helsinki": (60.1668, 24.9412),
    "Hong Kong": (22.2784, 114.184),
    "Istanbul": (41.0152, 28.9768),
    "Kuala Lumpur": (3.1455, 101.6842),
    "Las Vegas": (36.1561, -115.1413),
    "London": (51.5104, 0),
    "Los Angeles": (34.0354, -118.2446),
    "Madrid": (40.4134, -3.6979),
    "Mexico City": (19.3476, -99.1368),
    "Miami": (25.7752, -80.2073),
    "Montreal": (45.4936, -73.6838),
    "Moscow": (55.7499, 37.6222),
    "Mumbai": (19.0406, 72.8711),
    "New Delhi": (28.6252, 77.2102),
    "New Jersey": (40.1182, -74.5433),
    "New York": (40.6679, -73.9558),
    "Orlando": (28.5378, -81.3868),
    "Paris": (48.8555, 2.3475),
    "Prague": (50.0753, 14.4364),
    "Rio de Janeiro": (-22.9312, -43.3687),
    "Rome": (41.894, 12.4852),
    "San Fransisco": (37.7601, -122.4229),
    "San Jose": (37.3602, -121.901),
    "Sao Paulo": (-23.5414, -46.6225),
    "Seattle": (47.5948, -122.3275),
    "Seoul": (37.5389, 126.9924),
    "Shanghai": (31.2285, 121.4693),
    "Shenzhen": (22.6189, 114.0253),
    "Singapore": (1.3253, 103.8477),
    "St. Louis": (38.6306, -90.206),
    "Stockholm": (59.3296, 18.0679),
    "Sydney": (-33.8778, 151.2056),
    "Taipei": (25.0467, 121.5125),
    "Tokyo": (35.6788, 139.7706),
    "Toronto": (43.6564, -79.3972),
    "Vancouver": (49.2787, -123.1187),
    "Venice": (45.4375, 12.3248),
    "Washington DC": (38.894, -77.0125),
    "Zurich": (47.3754, 8.5367),
}


class LocationItem(ui.AbstractItem):
    def __init__(self, city: str, longitude: float, latitude: float):
        super().__init__()
        self.city_model = ui.SimpleStringModel(city)
        self.longitude_model = ui.SimpleFloatModel(longitude)
        self.latitude_model = ui.SimpleFloatModel(latitude)

    def __repr__(self) -> str:
        return self.city_model.as_string


class CityModel(ui.AbstractItemModel):
    """
    The model that has int value in the root, so it's acceptable by city combo box.
    """

    def __init__(self):
        super().__init__()

        self._children: List[LocationItem] = [LocationItem("Custom", 0.0, 0.0)]

        for city in PRESET_CITIES:
            city_info = PRESET_CITIES[city]
            self._children.append(LocationItem(city, city_info[1], city_info[0]))

        # The current index of the combo box
        self._current_index = ui.SimpleIntModel(-1)
        self._current_index.add_value_changed_fn(lambda a: self._item_changed(None))

    @property
    def current_index(self) -> int:
        """Gets the current index value of the model.

        Returns:
            int: Current index value from the SimpleIntModel.
        """
        return self._current_index.as_int

    @current_index.setter
    def current_index(self, value: int) -> None:
        """Sets the current index value of the model.

        Args:
            value (int): New current index to set.
        """
        if value != self.current_index:
            self._current_index.set_value(value)

    def set_location(self, longitude: float, latitude: float) -> None:
        """
        Set location to refresh city.
        Args:
            longitude (float): Longitude.
            latitude (float): Latitude.
        """
        city_index = -1
        for index, item in enumerate(self._children):
            if index == 0:
                continue
            if (
                abs(latitude - item.latitude_model.as_float) <= 0.00001
                and abs(longitude - item.longitude_model.as_float) < 0.00001
            ):
                city_index = index
                break
        else:
            city_index = 0
        if self.current_index != city_index:
            self.current_index = city_index

    def get_item_value_model(self, item: Optional[LocationItem] = None, column_id=0) -> ui.AbstractValueModel:
        """Get the item value model.

        Args:
            item (Optional[LocationItem]): Item to query. If provided, its value model is returned.
            column_id (int): Column id used to determine which model to return.

        Returns:
            ui.AbstractValueModel: If item is None, returns the current index model; otherwise, returns the model corresponding to the provided column id.
        """
        if item is None:
            return self._current_index
        elif column_id == 0:
            return item.city_model
        elif column_id == 1:
            return item.longitude_model
        elif column_id == 2:
            return item.latitude_model

    def get_item_children(self, item=None) -> List[LocationItem]:
        """Returns all the children items when requested by the widget.

        Args:
            item (Optional[LocationItem]): Item to query for children.

        Returns:
            List[LocationItem]: List of children items if item is None; otherwise, an empty list.
        """
        if item is None:
            return self._children
        else:
            return []

    def get_item_value_model_count(self, item=None) -> int:
        """Returns the number of columns in the model. The provided item parameter is ignored.

        Args:
            item (Optional[LocationItem]): Unused parameter.

        Returns:
            int: Number of columns (always 1).
        """
        return 1
