## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

__all__ = ["flatten_matrix"]

from pxr import Gf


def flatten_matrix(matrix: Gf.Matrix4d):
    """
    Flatten a 4x4 matrix into a list of 16 floats (row-major order).

    Args:
        matrix: A Gf.Matrix4d to flatten

    Returns:
        List of 16 floats representing the matrix in row-major order
    """
    return [
        matrix[0][0],
        matrix[0][1],
        matrix[0][2],
        matrix[0][3],
        matrix[1][0],
        matrix[1][1],
        matrix[1][2],
        matrix[1][3],
        matrix[2][0],
        matrix[2][1],
        matrix[2][2],
        matrix[2][3],
        matrix[3][0],
        matrix[3][1],
        matrix[3][2],
        matrix[3][3],
    ]
