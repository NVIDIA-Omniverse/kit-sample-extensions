# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from functools import lru_cache

from ._omni_curve_manipulator import *


@lru_cache()
def get_curve_manipulator_interface() -> ICurveManipulator:
    """Returns cached :class:`carb.dictionary.IDictionary` interface"""
    return acquire_interface()


def get_interface() -> ICurveManipulator:
    """Returns cached :class:`carb.dictionary.IDictionary` interface (shorthand)."""
    return get_curve_manipulator_interface()
