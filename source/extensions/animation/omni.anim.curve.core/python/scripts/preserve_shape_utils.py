from typing import Any

import AnimationSchema
import carb
import numpy as np
import omni.timeline
import omni.usd
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, Vt


def poly_to_power(P0, P1, P2, P3):
    """
    Bernstein polynomial basis -> Power basis
    """
    a = P3 - 3 * P2 + 3 * P1 - P0
    b = 3 * P2 - 6 * P1 + 3 * P0
    c = 3 * P1 - 3 * P0
    d = P0

    return a, b, c, d


def convert_time_to_parm_t(P0, P1, P2, P3, time) -> float:
    """
    Convert the Usd time to the parameter `t` used in Bezier curves.
    """
    a, b, c, d = poly_to_power(P0, P1, P2, P3)

    roots = np.polynomial.polynomial.polyroots([d[0] - time, c[0], b[0], a[0]])

    # carb.log_warn('roots: %s' % roots)
    for root in roots:
        if np.isreal(root) and np.real(root) >= 0 and np.real(root) <= 1:
            return np.real(root)

    carb.log_error("preserve_shape_utils.convert_time_to_parm_t: Can not find a valid root.")
    return 0.0


def evaluate_dummy(P0, P1, P2, P3, time, is_parm_t=False):
    """
    Just for debug purposes.
    """
    if is_parm_t:
        t = time
    else:
        t = convert_time_to_parm_t(P0, P1, P2, P3, time)

    a, b, c, d = poly_to_power(P0, P1, P2, P3)
    return t * (t * (t * a + b) + c) + d


def bezier_subdivision(P0, P1, P2, P3, prev_key, cur_key, next_key):
    """

    Reference: https://cg.informatik.uni-freiburg.de/course_notes/graphics_06_curves.pdf Page 41
    """
    t = convert_time_to_parm_t(P0, P1, P2, P3, cur_key.time)

    P00, P01, P02, P03 = P0, P1, P2, P3  # Pmn stands for P_n^m
    P10 = (1 - t) * P00 + t * P01
    P11 = (1 - t) * P01 + t * P02
    P12 = (1 - t) * P02 + t * P03
    P20 = (1 - t) * P10 + t * P11
    P21 = (1 - t) * P11 + t * P12
    P30 = (1 - t) * P20 + t * P21

    if prev_key.tangentWeighted or next_key.tangentWeighted:
        cur_key.tangentWeighted = True  # The new key should be weighted if either side is weighted
        prev_key.tangentWeighted = next_key.tangentWeighted = True  # The prev and next key should be weighted also.

    # we have to made the neighbouring 'auto' key to fixed
    if prev_key.inTangent.type == "auto":
        prev_key.inTangent.type = "fixed"
    if next_key.outTangent.type == "auto":
        next_key.outTangent.type = "fixed"

    # prev_key = P00
    if not np.allclose(np.array((prev_key.time, prev_key.value)), P00):
        carb.log_info("Preserve_shape: Precision can not be ensured at prev_key.")
    prev_key_out_tangent = P10 - P00  # it's relative
    prev_key.outTangent.type = "fixed"
    prev_key.outTangent.time, prev_key.outTangent.value = int(prev_key_out_tangent[0]), float(prev_key_out_tangent[1])

    # if key is unbroken, we should check the tangent
    if prev_key.tangentBroken == False and not np.isclose(
        prev_key.outTangent.time * prev_key.inTangent.value, prev_key.outTangent.value * prev_key.inTangent.time
    ):
        carb.log_info("Preserve_shape: Precision can not be ensured at prev_key_tangent.")

    # cur_key = P30
    if not np.allclose(np.array((cur_key.time, cur_key.value)), P30):
        carb.log_info("Preserve_shape: Precision can not be ensured at cur_key.")
    cur_key_in_tangent = P20 - P30
    cur_key_out_tangent = P21 - P30
    cur_key.inTangent.type = "fixed"
    cur_key.outTangent.type = "fixed"
    cur_key.inTangent.time, cur_key.inTangent.value = int(cur_key_in_tangent[0]), float(cur_key_in_tangent[1])
    cur_key.outTangent.time, cur_key.outTangent.value = int(cur_key_out_tangent[0]), float(cur_key_out_tangent[1])
    if not np.isclose(
        cur_key.outTangent.time * cur_key.inTangent.value, cur_key.outTangent.value * cur_key.inTangent.time
    ):
        # cur_key is of course unbroken.
        carb.log_info("Preserve_shape: Precision can not be ensured at cur_key_tangent.")

    # next_key = P03
    if not np.allclose(np.array((next_key.time, next_key.value)), P03):
        carb.log_info("Preserve_shape: Precision can not be ensured at next_key.")
    next_key_in_tangent = P12 - P03
    next_key.inTangent.type = "fixed"
    next_key.inTangent.time, next_key.inTangent.value = int(next_key_in_tangent[0]), float(next_key_in_tangent[1])
    if next_key.tangentBroken == False and not np.isclose(
        next_key.outTangent.time * next_key.inTangent.value, next_key.outTangent.value * next_key.inTangent.time
    ):
        carb.log_info("Preserve_shape: Precision can not be ensured at next_key_tangent.")
