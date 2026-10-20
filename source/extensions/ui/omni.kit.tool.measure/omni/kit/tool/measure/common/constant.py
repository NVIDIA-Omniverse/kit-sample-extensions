# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from enum import Enum

# ----- extension
EXTENSION_NAME = "Measure"


# # ----- Global -----
class DisplayAxisSpace(Enum):
    NONE = 0
    WORLD = 1
    LOCAL = 2


class MeasureAxis(Enum):
    NONE = 0
    X = 1
    Y = 2
    Z = 3


class UnitType(str, Enum):
    CENTIMETERS = "cm"
    MILLIMETERS = "mm"
    DECIMETERS = "dm"
    METERS = "m"
    KILOMETERS = "km"
    INCHES = "in"
    FEET = "ft"
    MILES = "mi"


# ----- State Machine
class MeasureEditState(Enum):
    SELECTED = 0
    POINT = 1
    LABEL = 2
    POSITION = 3


class MeasureCreationState(Enum):
    NONE = -1
    START_SELECTION = 0
    INTERMEDIATE_SELECTION = 1
    END_SELECTION = 2
    FINALIZE = 3


class MeasureMode(Enum):
    NONE = -1
    POINT_TO_POINT = 0
    MULTI_POINT = 1
    ANGLE = 2
    DIAMETER = 3
    AREA = 4
    VOLUME = 5
    SELECTED = 6


class MeasureState(Enum):
    NONE = 0
    CREATE = 1
    EDIT = 2


# # ----- UI -----
class ConstrainAxis(Enum):
    X = 0
    Y = 1
    Z = 2
    STAGE_UP = 3
    DYNAMIC = 4  # Could use the term Contextual too


class ConstrainMode(Enum):
    DEFAULT = 0
    VIEW_PLANE = 1


class DistanceType(Enum):
    MIN = 0
    MAX = 1
    CENTER = 2


class LabelSize(Enum):
    SMALL = 12
    MEDIUM = 15
    LARGE = 18
    EXTRA_LARGE = 21


LABEL_SCALE_MAPPING = {LabelSize.SMALL: 1, LabelSize.MEDIUM: 1.25, LabelSize.LARGE: 1.75, LabelSize.EXTRA_LARGE: 2.25}


class Precision(str, Enum):
    INTEGER = "#"
    TENTH = "#.0"
    HUNDRETH = "#.00"
    THOUSANDTH = "#.000"
    TEN_THOUSANDTH = "#.0000"
    HUNDRED_THOUSANDTH = "#.00000"


class SnapMode(Enum):
    SURFACE = 1
    VERTEX = 2
    PIVOT = 3
    EDGE = 4
    MIDPOINT = 5
    CENTER = 6


class SnapTo(Enum):
    CUSTOM = 0
    PERPENDICULAR = 1


# # ----- SNAPPING -----
SNAP_DISTANCE = 100
# Hysteresis multiplier for snap release threshold. Once snapped, the cursor must
# move SNAP_HYSTERESIS_FACTOR times further than SNAP_DISTANCE before the snap releases.
# This prevents flickering when the cursor hovers near the snap threshold boundary.
SNAP_HYSTERESIS_FACTOR = 1.5


MEASURE_WINDOW_VISIBLE_CONTEXT = "omni.kit.tool.measure-window-visible"
