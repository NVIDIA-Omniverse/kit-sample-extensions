# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from omni.ui import scene as sc

from ..common import MeasureState, UserSettings
from ..manager import StateMachine


# TODO: Get this working appropriately. Still seems like a black box.
class PreventOthers(sc.GestureManager):
    """
    Hide other gestures
    """

    def __init__(self):
        self._manipulator = None
        self._white_list = [
            "PanGesture",
            "TumbleGesture",
            "LookGesture",
            "ZoomGesture",
            "MeasureClick",
            "MeasureHover",
            "MeasureDelete",
        ]
        super().__init__()

    def __del__(self):
        self._manipulator = None

    def can_be_prevented(self, gesture) -> bool:
        """
        Called per gesture. Determines if the gesture can be prevented.
        """
        return not UserSettings().visible

    def should_prevent(self, gesture, preventer) -> bool:
        """
        Called per gesture. Determines if the gesture should be prevented with another gesture.
        Useful to resolve intersections
        """
        if StateMachine().tool_state == MeasureState.CREATE:
            return False
        return UserSettings().visible and gesture.name not in self._white_list
