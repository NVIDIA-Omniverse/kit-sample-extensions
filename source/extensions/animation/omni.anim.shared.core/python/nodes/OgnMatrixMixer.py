# Copyright (c) 2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

"""Module to provide OgnMatrixMixer- a Ogn node class to interpolate two matrices."""

import numpy as np
from pxr import Gf

from .utils.matrix_operations import slerp_matrices


class OgnMatrixMixer:
    """An Ogn node class to output the interpolated matrix of two matrices.

    The interpolation is computed by decomposing the two matrices into
    scale, shear, quaternion, and translation components. Scale, shear, and translation
    are interpolated linearly and the quaternion is interpolated spherically. The
    interpolated components are recomposed into the output matrix.

    The option to interpolate scale + shear, rotation, and translation can be set independently.
    Any component that is not interpolated, uses the value from the transform_a matrix.
    """

    @staticmethod
    def compute(db) -> bool:
        """
        Compute the interpolated matrix from the two input matrices.

        Decompose the two input matrices and selectively interpolate the components
        before recomposing the output matrix.

        The boolean inputs, interpolate_scale, interpolate_rotation, and
        interpolate_translation, are used to decide whether to use the transform_a component
        or the interpolated component when recomposing the matrix.

        With this the scale, rotation and translation can be constrained independently.

        Args:
            db: Database for the calling node

        Returns:
            success
        """
        matrix_c = OgnMatrixMixer.__blend(db)
        db.outputs.transform[:] = np.array(matrix_c).reshape(16)
        return True

    @staticmethod
    def __blend(db) -> Gf.Matrix4d:
        matrix_a = db.inputs.transform_a.reshape(4, 4)
        matrix_b = db.inputs.transform_b.reshape(4, 4)

        alpha = db.inputs.alpha

        s = db.inputs.interpolate_scale
        r = db.inputs.interpolate_rotation
        t = db.inputs.interpolate_translation

        matrix_c = slerp_matrices(matrix_a, matrix_b, alpha, s, r, t)

        return Gf.Matrix4d(matrix_c)
