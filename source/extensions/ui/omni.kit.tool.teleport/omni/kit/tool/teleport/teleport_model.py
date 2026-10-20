# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["TeleportModel"]

import carb.settings
import omni.stageupdate
import omni.usd
from omni.ui import scene as sc
from pxr import Gf, UsdGeom

from .teleport_page import (
    TELE_BEAM_VISIBLE,
    TELEPORT_RING_MANIPULATOR_FIXED_SIZE,
    TELEPORT_RING_MANIPULATOR_MAX_SIZE,
    TELEPORT_RING_MANIPULATOR_MIN_SIZE,
    TELEPORT_RING_MANIPULATOR_SCALE,
    TELEPORT_RING_MANIPULATOR_VISIBLE,
)

# The gizmo, beam and label geometry is authored in centimeters, so that is the unit every
# hard-coded size constant in this extension is expressed in.
DEFAULT_METERS_PER_UNIT = 0.01


class TeleportModel(sc.AbstractManipulatorModel):
    """
    User part. The model tracks the circle and info of the brush.
    """

    class PositionItem(sc.AbstractManipulatorItem):
        """
        The Model Item represents the position
        """

        def __init__(self):
            super().__init__()
            self.value = Gf.Vec3d()

    class DistanceItem(sc.AbstractManipulatorItem):
        """The Model Item represents the teleport distance"""

        def __init__(self, value=100.1):
            super().__init__()
            self.value = value

    class WorldUpItem(sc.AbstractManipulatorItem):
        """The Model Item represents the teleport world up"""

        def __init__(self, value=Gf.Vec3d.YAxis()):
            super().__init__()
            self.value = value

    class AngleItem(sc.AbstractManipulatorItem):
        """The Model Item represents the teleport angle"""

        def __init__(self, value=0.0):
            super().__init__()
            self.value = value

    class VisibleItem(sc.AbstractManipulatorItem):
        """The Model Item represents the circle visible"""

        def __init__(self, value=False):
            super().__init__()
            self.value = value

    def __init__(self):
        super().__init__()

        self._position = TeleportModel.PositionItem()
        self._visual_up = TeleportModel.PositionItem()
        self._visual_front = TeleportModel.PositionItem()
        self._angle = TeleportModel.AngleItem()
        self._distance = TeleportModel.DistanceItem()
        self._world_up = TeleportModel.WorldUpItem()
        self._visible = TeleportModel.VisibleItem()

        self._usd_context = omni.usd.get_context()
        self._meters_per_unit = DEFAULT_METERS_PER_UNIT
        self._stage_update = omni.stageupdate.get_stage_update_interface()
        self._stage_subscription = self._stage_update.create_stage_update_node(
            "TeleportTool", self._on_attach, None, None, None, None, None
        )

        self._item_dict = {
            "position": self._position,
            "visual_up": self._visual_up,
            "visual_front": self._visual_front,
            "angle": self._angle,
            "distance": self._distance,
            "world_up": self._world_up,
            "visible": self._visible,
        }

    def get_item(self, identifier):
        return self._item_dict.get(identifier, None)

    def destroy(self):
        self._stage_subscription = None
        self._stage_update = None
        self._usd_context = None

    def _on_attach(self, stage_id, meters_per_unit):
        # Only seeds the fallback used when there is no stage to query: metersPerUnit can be
        # authored after the stage is attached, so meters_per_unit below re-reads the stage.
        if meters_per_unit and meters_per_unit > 0:
            self._meters_per_unit = meters_per_unit

    @property
    def meters_per_unit(self) -> float:
        """The stage's metersPerUnit.

        Live-queried rather than cached so that authoring metersPerUnit on an already-open stage
        takes effect. Falls back to the value reported when the stage was attached, then to
        centimeters.
        """
        stage = self._usd_context.get_stage() if self._usd_context else None
        if stage:
            meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)
            if meters_per_unit and meters_per_unit > 0:
                return meters_per_unit
        return self._meters_per_unit

    @property
    def units_scale(self) -> float:
        """Factor converting a centimeter-authored constant into stage units.

        Exactly 1.0 on a centimeter stage, so those stages are unaffected by the conversion.
        """
        return DEFAULT_METERS_PER_UNIT / self.meters_per_unit

    @property
    def position(self):
        return self._position.value

    @position.setter
    def position(self, value: Gf.Vec3d):
        self._position.value = value
        self._item_changed(self._position)

    @property
    def visual_up(self):
        return self._visual_up.value

    @visual_up.setter
    def visual_up(self, value: Gf.Vec3d):
        self._visual_up.value = value
        self._item_changed(self._visual_up)

    @property
    def visual_front(self):
        return self._visual_front.value

    @visual_front.setter
    def visual_front(self, value: Gf.Vec3d):
        self._visual_front.value = value
        self._item_changed(self._visual_front)

    @property
    def angle(self):
        return self._angle.value

    @angle.setter
    def angle(self, value: float):
        self._angle.value = value
        self._item_changed(self._angle)

    @property
    def world_up(self):
        return self._world_up.value

    @world_up.setter
    def world_up(self, value: Gf.Vec3d):
        self._world_up.value = value
        self._item_changed(self._world_up)

    @property
    def distance(self):
        return self._distance.value

    @distance.setter
    def distance(self, value: float):
        self._distance.value = value
        self._item_changed(self._distance)

    @property
    def visible(self):
        return self._visible.value

    @visible.setter
    def visible(self, value: float):
        beam_visible = carb.settings.get_settings().get_as_bool(TELE_BEAM_VISIBLE)
        ring_visible = carb.settings.get_settings().get_as_bool(TELEPORT_RING_MANIPULATOR_VISIBLE)
        self._visible.value = (beam_visible or ring_visible) and value
        self._item_changed(self._visible)

    @property
    def beam_visible(self):
        return carb.settings.get_settings().get_as_bool(TELE_BEAM_VISIBLE) and self._visible.value

    @property
    def ring_visible(self):
        return carb.settings.get_settings().get_as_bool(TELEPORT_RING_MANIPULATOR_VISIBLE) and self._visible.value

    @property
    def ring_fixed_size(self):
        return carb.settings.get_settings().get_as_bool(TELEPORT_RING_MANIPULATOR_FIXED_SIZE)

    @property
    def ring_scale(self):
        return carb.settings.get_settings().get_as_float(TELEPORT_RING_MANIPULATOR_SCALE)

    @property
    def ring_min_size(self):
        return carb.settings.get_settings().get_as_float(TELEPORT_RING_MANIPULATOR_MIN_SIZE)

    @property
    def ring_max_size(self):
        return carb.settings.get_settings().get_as_float(TELEPORT_RING_MANIPULATOR_MAX_SIZE)

    def get_as_floats(self, item):  # pragma: no cover -- currently unused
        # Get the value directly from the item
        if item == self._angle or item == self._distance:
            return item.value

    def set_floats(self, item, value):  # pragma: no cover -- currently unused
        if not value or not item or item.value == value:
            return

        # Set directly to the item
        if item == self._angle or item == self._distance:
            item.value = value
            # This makes the manipulator updated
            self._item_changed(item)

    def get_as_ints(self, item):  # pragma: no cover -- currently unused
        if item == self._position or item == self._world_up:
            return item.value

    def set_ints(self, item, value):  # pragma: no cover -- currently unused
        if not value or not item or item.value == value:
            return

        # Set directly to the item
        if item == self._position or item == self._world_up:
            item.value = value
            # This makes the manipulator updated
            self._item_changed(item)

    def get_as_bool(self, item):  # pragma: no cover -- currently unused
        if item == self._visible:
            return item.value
        return False

    def set_bool(self, item, value):  # pragma: no cover -- currently unused
        if not item or item.value == value:
            return

        # Set directly to the item
        if item == self._visible:
            item.value = value
            # This makes the manipulator updated
            self._item_changed(item)
