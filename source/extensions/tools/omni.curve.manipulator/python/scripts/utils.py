# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import Callable, List, Tuple, Union

import carb
from pxr import Gf, Usd, UsdGeom, Vt

TOLERANCE = 1e-4


def find_anchor_index(index: int) -> int:
    remainder = index % 3
    if remainder == 1:
        return index // 3 * 3
    elif remainder == 2:
        return (index // 3 + 1) * 3
    else:
        return index


def get_array_index_offset_and_curve_index(id: int, curve_vertex_counts: Union[List[int], Vt.IntArray]):
    id_curve_offset = 0
    curve_index = 0

    while id_curve_offset + curve_vertex_counts[curve_index] <= id:
        id_curve_offset += curve_vertex_counts[curve_index]
        curve_index += 1

    return id_curve_offset, curve_index


def get_array_index_range(basis_curves: UsdGeom.BasisCurves, id: int) -> Tuple[int, int]:
    start = 0
    for vertex_count in basis_curves.GetCurveVertexCountsAttr().Get():
        end = start + vertex_count - 1
        if id >= start and id <= end:
            return start, end
        start = start + vertex_count
    return 0, start


def has_smooth_tangent(basis_curves: UsdGeom.BasisCurves, id: int) -> Tuple[bool, bool, int, int, int]:
    curve_vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
    curve_vertex_counts = curve_vertex_counts_attr.Get()
    points_attr = basis_curves.GetPointsAttr()
    points = points_attr.Get()
    wrap = basis_curves.GetWrapAttr().Get()

    id_curve_offset, curve_index = get_array_index_offset_and_curve_index(id, curve_vertex_counts)
    anchor_id = find_anchor_index(id - id_curve_offset) + id_curve_offset

    tgt0_id = None
    tgt1_id = None
    if id < anchor_id:
        tgt0_id = id
        tgt1_id = anchor_id + 1
    elif id > anchor_id:
        tgt0_id = anchor_id - 1
        tgt1_id = id
    else:
        tgt0_id = anchor_id - 1
        tgt1_id = anchor_id + 1

    if tgt1_id >= id_curve_offset + curve_vertex_counts[curve_index]:
        if wrap == UsdGeom.Tokens.periodic:
            tgt1_id = id_curve_offset + 1
        else:
            tgt1_id = None

    if tgt0_id < id_curve_offset:
        if wrap == UsdGeom.Tokens.periodic:
            tgt0_id = id_curve_offset + curve_vertex_counts[curve_index] - 2
        else:
            tgt0_id = None

    if tgt0_id is None or tgt1_id is None:
        return False, False, tgt0_id, anchor_id, tgt1_id

    tgt_0 = points[tgt0_id] - points[anchor_id]
    tgt_1 = points[tgt1_id] - points[anchor_id]

    l_0 = tgt_0.Normalize()
    l_1 = tgt_1.Normalize()

    dot = Gf.Dot(tgt_0, tgt_1)
    cross = Gf.Cross(tgt_0, tgt_1)

    return (
        dot < 0 and Gf.IsClose(cross, Gf.Vec3f(0.0), TOLERANCE),
        Gf.IsClose(l_0, l_1, TOLERANCE),
        tgt0_id,
        anchor_id,
        tgt1_id,
    )


def has_tangents(basis_curves: UsdGeom.BasisCurves) -> bool:
    if basis_curves.GetTypeAttr().Get() == UsdGeom.Tokens.cubic:
        if basis_curves.GetBasisAttr().Get() == UsdGeom.Tokens.bezier:
            return True
    return False


def get_primvars_value_and_interpolation(
    basis_curves: UsdGeom.BasisCurves,
    get_attr_fn: Callable[[UsdGeom.BasisCurves], None],
    get_interpolation_fn: Callable[[UsdGeom.BasisCurves], None],
    attr_name: str,
) -> tuple[Usd.Attribute, list, str]:
    value = None
    interpolation = None
    attr = get_attr_fn(basis_curves)
    if attr:
        interpolation = get_interpolation_fn(basis_curves)
        if (
            interpolation == UsdGeom.Tokens.varying
            or interpolation == UsdGeom.Tokens.vertex
            or interpolation == UsdGeom.Tokens.constant
        ):
            value = attr.Get()
            if value:
                value = list(value)  # convert from VtArray to list to be size editable
        else:
            carb.log_warn(f"Unsupported interpolation mode for {attr_name} attribute")

    return attr, value, interpolation
