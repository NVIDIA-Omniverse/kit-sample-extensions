# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from enum import Enum


class MarkupState(Enum):
    DEACTIVATED = 1
    READY = 2
    EDIT = 3
    SHAPE = 4
    ARROW = 5
    LINE = 6
    DRAW = 7
    STYLE_CHANGE = 8
    EDIT_COMMENT = 10
    COLOR_PICKER = 11


__current_state__ = MarkupState.DEACTIVATED
__previous_state__ = MarkupState.DEACTIVATED


def get_markup_state():
    global __current_state__
    return __current_state__


def set_markup_state(state: MarkupState):
    global __current_state__
    global __previous_state__

    if state == MarkupState.READY and __current_state__ in (MarkupState.EDIT, MarkupState.EDIT_COMMENT):
        from ..extension import get_instance

        get_instance().set_selected_element(None)

    __previous_state__ = __current_state__
    __current_state__ = state


def return_to_previous_state():
    global __current_state__
    global __previous_state__

    __current_state__ = __previous_state__
    __previous_state__ = MarkupState.READY


__all__ = ["MarkupState", "get_markup_state", "set_markup_state", "return_to_previous_state"]
