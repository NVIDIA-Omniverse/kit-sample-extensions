# Copyright (c) 2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

"""Module to provide OgnMatrixMultiply- a Ogn node class to multiply two matrices."""

import numpy as np


class OgnMatrixMultiply:
    """An Ogn node class to output the product of two input matrices."""

    @staticmethod
    def compute(db) -> bool:
        """
        Multiply two matrices together.

        Multiply transform_a and transform_b using np.matmul.

        Args:
            db: Database for the calling node

        Returns:
            success
        """
        matrix_a = db.inputs.transform_a.reshape(4, 4)
        matrix_b = db.inputs.transform_b.reshape(4, 4)
        matrix_c = np.matmul(matrix_a, matrix_b)

        db.outputs.transform[:] = np.array(matrix_c).reshape(16)
        return True
