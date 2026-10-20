# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["draw_display_axis"]

from typing import Union

import omni.ui.scene as sc
from omni.ui import color
from pxr import Gf

from ..common import DisplayAxisSpace, convert_distance_and_units
from .manipulator_items import PrimRefItem
from .tools._scene_widget import MeasureAxisStackLabel


def draw_display_axis(
    start_prim_path: str,
    start_point: Union[Gf.Vec3d, Gf.Vec3f],
    end_point: Union[Gf.Vec3d, Gf.Vec3f],
    axis_space: DisplayAxisSpace,
    label_stack: MeasureAxisStackLabel,
    unit_type: str,
    precision: int,
) -> None:
    """
    Draws the World or local XYZ offset
    """
    # Early out if there's no need to display
    if axis_space == DisplayAxisSpace.NONE:
        return

    # Calculate the support line information
    if axis_space == DisplayAxisSpace.WORLD:
        x_start, x_end = start_point, Gf.Vec3d(end_point[0], start_point[1], start_point[2])
        y_start, y_end = x_end, Gf.Vec3d(end_point[0], end_point[1], start_point[2])
        z_start, z_end = y_end, end_point
    else:
        start_prim = PrimRefItem()
        start_prim.update(start_prim_path)
        if not start_prim.prim:
            return

        rot_matrix = start_prim.local_xform.GetOrthonormalized().ExtractRotationMatrix()
        x_vec, y_vec = (rot_matrix.GetRow(i) for i in range(2))

        base = start_point - end_point
        x_len = Gf.Dot(base, x_vec)
        y_len = Gf.Dot(base, y_vec)

        x_start, x_end = start_point, (x_vec * -x_len) + start_point
        y_start, y_end = x_end, (y_vec * -y_len) + x_end
        z_start, z_end = y_end, end_point

    # Calculate Line Lengths
    x_dist = (x_start - x_end).GetLength()
    y_dist = (y_start - y_end).GetLength()
    z_dist = (z_start - z_end).GetLength()

    # Calculate label position, Define Text
    centroid = (start_point + end_point) * 0.5
    label_stack.set_position(centroid)

    m_txt, m_unit = convert_distance_and_units((start_point - end_point).GetLength(), unit_type)
    x_txt, x_unit = convert_distance_and_units(x_dist, unit_type)
    y_txt, y_unit = convert_distance_and_units(y_dist, unit_type)
    z_txt, z_unit = convert_distance_and_units(z_dist, unit_type)

    label_stack.update_text(
        main=f"{m_txt:.{precision}f}{m_unit}",
        x=f"{x_txt:.{precision}f}{x_unit}",
        y=f"{y_txt:.{precision}f}{y_unit}",
        z=f"{z_txt:.{precision}f}{z_unit}",
    )
    label_stack.visible = True

    # Draw Lines
    if x_dist != 0:
        x_line = sc.Line([*x_start], [*x_end], color=color("#AA5555"), thickness=3)
    if y_dist != 0:
        y_line = sc.Line([*y_start], [*y_end], color=color("#71A376"), thickness=3)
    if z_dist != 0:
        z_line = sc.Line([*z_start], [*z_end], color=color("#4F7DA0"), thickness=3)
