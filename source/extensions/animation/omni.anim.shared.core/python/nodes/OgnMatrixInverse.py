# Copyright (c) 2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

"""Module to provide OgnMatrixInverse- a Ogn node class to invert a matrix."""

import numpy as np


class OgnMatrixInverse:
    """An Ogn node class to output the inverse of the input matrix."""

    @staticmethod
    def compute(db) -> bool:
        """
        Take the inverse of a matrix.

        Output the inverse of the input transform matrix.

        Args:
            db: Database for the calling node

        Returns:
            success
        """
        matrix = db.inputs.transform.reshape(4, 4)
        inverse = np.linalg.inv(matrix)

        db.outputs.transform[:] = np.array(inverse).reshape(16)
        return True
