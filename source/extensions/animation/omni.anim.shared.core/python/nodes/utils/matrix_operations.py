# Copyright (c) 2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

"""Module to provide functions for composing and decomposing matrices."""

from typing import Tuple

import numpy as np


def decompose(matrix: np.array) -> Tuple[np.array, np.array, np.array, np.array]:
    """
    Decompose the matrix into scale, shear, quaternion, and translate.

    Args:
        matrix

    Returns:
        scale, shear, quaternion, translate
    """
    matrix = matrix.copy()

    __normalize_matrix(matrix)
    __remove_perspective(matrix)

    # Test for non-degenerate
    det = np.linalg.det(matrix)
    if not __near_zero(det):
        translate = __get_translate(matrix)
        scale, shear = __get_scale_and_shear_and_orthonormalize(matrix)
        quaternion = __make_quaternion(matrix)
    else:
        translate = __translate()
        scale = __scale()
        shear = __shear()
        quaternion = __quaternion()

    return scale, shear, quaternion, translate


def compose(scale: np.array, shear: np.array, quaternion: np.array, translate: np.array) -> np.array:
    """
    Compose a matrix from the input scale, shear, quaternion, translate.

    Args:
        scale:
        shear:
        quaternion:
        translate:

    Returns:
        matrix (4x4)
    """
    m = __make_scale_matrix(scale)
    m = np.matmul(m, __make_shear_matrix(shear))
    m = np.matmul(m, __make_quaternion_matrix(quaternion))
    m = np.matmul(m, __make_translate_matrix(translate))
    return m


def slerp_matrices(
    matrix_0: np.array, matrix_1: np.array, alpha: float, s: bool = True, r: bool = True, t: bool = True
) -> np.array:
    """
    Interpolate the two matrices with the value alpha.

    Interpolate with alpha [0, 1] to [matrix_0, matrix_1].

    The interpolation of scale, rotation, and translate components are enabled with s, r, and t.
    When a value is False, the component from matrix_0 is used. When it is True, the interpolated
    component is used. The resulting components are recomposed into the output matrix.
    Args:
        matrix_0:
        matrix_1:
        alpha:
        s:
        r:
        t:

    Returns:
        matrix
    """
    matrix_local = np.matmul(matrix_1, np.linalg.inv(matrix_0))

    scale_1, shear_1, quaternion_1, translate_1 = decompose(matrix_local)
    quaternion_0 = __quaternion()
    quaternion_2 = __slerp_quat(quaternion_0, quaternion_1, alpha) if r else quaternion_0

    scale_0 = np.ones(3)
    scale_2 = alpha * scale_1 + (1.0 - alpha) if s else scale_0

    shear_0 = np.zeros(3)
    shear_2 = alpha * shear_1 if s else shear_0

    translate_0 = np.zeros(3)
    translate_2 = alpha * translate_1 if t else translate_0

    matrix_slerp = compose(scale_2, shear_2, quaternion_2, translate_2)
    matrix_2 = np.matmul(matrix_slerp, matrix_0)
    return matrix_2


def __near_zero(x: float or np.array) -> bool:
    # The type np.array is added for typing purposes and will not be used.
    return np.finfo(dtype=float).min >= x >= -np.finfo(dtype=float).min


def __quaternion() -> np.array:
    return np.array([1.0, 0.0, 0.0, 0.0])


def __scale() -> np.array:
    return np.ones(3)


def __shear() -> np.array:
    return np.zeros(3)


def __translate() -> np.array:
    return np.zeros(3)


def __get_scale_and_shear_and_orthonormalize(matrix: np.array) -> Tuple[np.array, np.array]:
    scale = np.ones(3)
    shear = np.zeros(3)

    # Get X scale and normalize first row.
    scale[0] = np.linalg.norm(matrix[0])
    if not __near_zero(scale[0]):
        matrix[0] /= scale[0]

    # Get XY Shear and make row 2 orthogonal to row 1
    shear[0] = np.dot(matrix[0], matrix[1])
    matrix[1] -= matrix[0] * shear[0]

    # Compute Y scale and normalize row 2.
    scale[1] = np.linalg.norm(matrix[1])
    if not __near_zero(scale[1]):
        matrix[1] /= scale[1]
    shear[0] /= scale[1]

    # Compute XZ and YZ shears, orthogonalize row 3.
    shear[1] = np.dot(matrix[0], matrix[2])
    matrix[2] -= matrix[0] * shear[1]
    shear[2] = np.dot(matrix[1], matrix[2])
    matrix[2] -= matrix[1] * shear[2]

    # Next, get Z scale and normalize row 3.
    scale[2] = np.linalg.norm(matrix[2])
    if not __near_zero(scale[2]):
        matrix[2] /= scale[2]
    shear[1] /= scale[2]
    shear[2] /= scale[2]

    # At this point, the upper 3x3 is orthonormal.
    # If the determinant is -1, the coordinates have flipped.
    # Negate the upper 3x3 and the scale.
    if np.linalg.det(matrix) < 0:
        scale *= -1.0
        matrix[0:3, 0:3] *= -1.0

    return scale, shear


def __make_quaternion(matrix: np.array) -> np.array:
    trace = np.trace(matrix)
    threshold = 1e-6
    if trace > threshold:
        s = np.sqrt(trace) * 2.0
        quaternion = [
            0.25 * s,
            (matrix[2][1] - matrix[1][2]) / s,
            (matrix[0][2] - matrix[2][0]) / s,
            (matrix[1][0] - matrix[0][1]) / s,
        ]
    elif matrix[0][0] > matrix[1][1] and matrix[0][0] > matrix[2][2]:
        # X dominant
        s = np.sqrt(1.0 + matrix[0][0] - matrix[1][1] - matrix[2][2]) * 2.0
        quaternion = [
            (matrix[2][1] - matrix[1][2]) / s,
            0.25 * s,
            (matrix[1][0] + matrix[0][1]) / s,
            (matrix[0][2] + matrix[2][0]) / s,
        ]
    elif matrix[1][1] > matrix[2][2]:
        # Y dominant
        s = np.sqrt(1.0 + matrix[1][1] - matrix[0][0] - matrix[2][2]) * 2.0
        quaternion = [
            (matrix[0][2] - matrix[2][0]) / s,
            (matrix[1][0] + matrix[0][1]) / s,
            0.25 * s,
            (matrix[2][1] + matrix[1][2]) / s,
        ]
    else:
        # Z dominant
        s = np.sqrt(1.0 + matrix[2][2] - matrix[0][0] - matrix[1][1]) * 2.0
        quaternion = [
            (matrix[1][0] - matrix[0][1]) / s,
            (matrix[0][2] + matrix[2][0]) / s,
            (matrix[2][1] + matrix[1][2]) / s,
            0.25 * s,
        ]
    return np.array(quaternion)


def __get_translate(matrix: np.array) -> np.array:
    translate = matrix[3, 0:3]
    return translate


def __remove_perspective(matrix: np.array) -> None:
    matrix[:, 3] = [0.0, 0.0, 0.0, 1.0]


def __normalize_matrix(matrix: np.array) -> None:
    if matrix[3][3] != 0 and matrix[3][3] != 1:
        matrix[:] /= matrix[3][3]


def __make_scale_matrix(scale: np.array) -> np.array:
    matrix = np.identity(4)
    matrix[[0, 1, 2], [0, 1, 2]] = scale
    return matrix


def __make_translate_matrix(translate: np.array) -> np.array:
    matrix = np.identity(4)
    matrix[3, 0:3] = translate
    return matrix


def __make_shear_matrix(shear: np.array) -> np.array:
    matrix = np.identity(4)
    matrix[[1, 2, 2], [0, 0, 1]] = shear
    return matrix


def __make_skew_symmetric_matrix(a: np.array) -> np.array:
    a1, a2, a3 = a
    return np.array([(0.0, +a3, -a2), (-a3, 0.0, +a1), (+a2, -a1, 0.0)])


def __make_quaternion_matrix(quaternion: np.array) -> np.array:
    matrix = np.identity(4)

    length = np.dot(quaternion, quaternion)
    if __near_zero(length):
        return matrix

    # https://en.wikipedia.org/wiki/Quaternions_and_spatial_rotation
    qr = quaternion[0]
    v = quaternion[1:] / length

    vx = __make_skew_symmetric_matrix(v)
    vx2 = np.matmul(vx, vx)
    identity = np.identity(3)
    r_matrix = identity - 2 * qr * vx + 2 * vx2
    matrix = np.identity(4)
    matrix[:3, :3] = r_matrix
    return matrix


def __slerp_quat(quaternion_0: np.array, quaternion_1: np.array, alpha: float) -> np.array:
    quaternion_1 = quaternion_1.copy()
    threshold = 1e-6

    cos_omega = np.dot(quaternion_0, quaternion_1)

    if cos_omega < 0.0:
        quaternion_1 = -1.0 * quaternion_1
        cos_omega = -cos_omega

    if (1.0 - cos_omega) > threshold:
        # spherical linear interpolation
        omega = np.arccos(cos_omega)
        sin_omega = np.sin(omega)

        scale0 = np.sin((1.0 - alpha) * omega) / sin_omega
        scale1 = np.sin(alpha * omega) / sin_omega
    else:
        # When the quaternions are very close, use linear interpolation
        scale0 = 1.0 - alpha
        scale1 = alpha

    # calculate final values
    output = scale0 * quaternion_0 + scale1 * quaternion_1

    return output
