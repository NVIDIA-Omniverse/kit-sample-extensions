# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["ViewportMeasurementModel"]

from typing import Dict, List, Optional

import omni.ui.scene as sc

from ..common import MeasureMode
from ..system import MeasurePrim
from ._measurement_items import (
    AngleMeasurementItem,
    AreaMeasurementItem,
    DiameterMeasurementItem,
    LinearMeasurementItem,
    MultiPointMeasurementItem,
    _MeasurementItem,
)


class ViewportMeasurementModel(sc.AbstractManipulatorModel):
    """
    The Model tracks the attributes of the selected measurement
    """

    def __init__(self):
        super().__init__()
        self._measurements = {}

    def __del__(self):
        self.clear()

    @property
    def measurements(self) -> Dict[int, _MeasurementItem]:
        return self._measurements

    def clear(self):
        self._measurements = {}

    # CRUD Operations [Create, Read, Update, Delete]
    def create(self, measure_prim: MeasurePrim) -> bool:

        if measure_prim.mode == MeasureMode.MULTI_POINT:
            measurement_item = MultiPointMeasurementItem(measure_prim)
        elif measure_prim.mode == MeasureMode.ANGLE:
            measurement_item = AngleMeasurementItem(measure_prim)
        elif measure_prim.mode == MeasureMode.DIAMETER:
            measurement_item = DiameterMeasurementItem(measure_prim)
        elif measure_prim.mode == MeasureMode.AREA:
            measurement_item = AreaMeasurementItem(measure_prim)
        elif measure_prim.mode == MeasureMode.VOLUME:
            return False
        else:
            measurement_item = LinearMeasurementItem(measure_prim)

        uuid = measure_prim.uuid
        if self.measurements.get(uuid, None):
            return False

        self.measurements[uuid] = measurement_item
        self._item_changed(self.measurements[uuid])
        return True

    def read(self, uuid: int) -> Optional[_MeasurementItem]:
        return self.measurements.get(uuid, None)

    def update(self, payload: "MeasurePayload") -> None:
        if measurement := self.measurements.get(payload.uuid, None):
            measurement.payload = payload
            self._item_changed(measurement)

    def delete(self, uuid: int) -> Optional["MeasurePayload"]:
        if not (measurement := self.measurements.get(uuid, None)):
            return None

        measurement.clear()
        payload = measurement.payload
        self.measurements.pop(uuid)
        return payload

    # Selection
    @property
    def selected(self) -> List[int]:
        return [measurement.uuid for measurement in self.measurements.values() if measurement.selected]

    def select(self, uuid: int) -> None:
        if not (measurement := self.measurements.get(uuid, None)) or measurement.selected == True:
            return
        # We don't want to run it through the property becasuse of the consistent update
        # issues that the TreeView selection changed would cause
        measurement._selected = True
        self._item_changed(measurement)

    def deselect_all(self) -> None:
        for measurement in self.measurements.values():
            measurement._selected = False
            self._item_changed(measurement)

    def clear_hovered(self):
        for measurement in self._measurements.values():
            measurement._on_hover_end(None)
            self._item_changed(measurement)

    def set_hovered(self, uuid: int, active: bool) -> None:
        selected_measurement = self._measurements.get(uuid, None)
        if selected_measurement is None or selected_measurement.selected:
            return

        if active:
            self.clear_hovered()

        selected_measurement._on_hover_start(None) if active else selected_measurement._on_hover_end(None)
        self._item_changed(selected_measurement)
