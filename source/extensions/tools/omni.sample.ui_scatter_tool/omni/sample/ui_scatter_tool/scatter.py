# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""
Core scatter algorithm for generating object positions.

This module provides the scatter function that generates transformation matrices
for arranging objects in a 3D grid pattern with optional randomization.
"""

import random
from typing import List, Optional

from pxr import Gf


def scatter(
    count: List[int], distance: List[float], randomization: List[float], id_count: int = 1, seed: Optional[int] = None
):
    """
    Returns generator with pairs containing transform matrices and ids to
    arrange multiple objects.

    ### Arguments:

        `count: List[int]`
            Number of matrices to generate per axis

        `distance: List[float]`
            The distance between objects per axis

        `randomization: List[float]`
            Random distance per axis

        `id_count: int`
            Count of different id

        `seed: int`
            If seed is omitted or None, the current system time is used. If seed
            is an int, it is used directly.

    """
    # Initialize the random number generator.
    random.seed(seed)

    for i in range(count[0]):
        x = (i - 0.5 * (count[0] - 1)) * distance[0]

        for j in range(count[1]):
            y = (j - 0.5 * (count[1] - 1)) * distance[1]

            for k in range(count[2]):
                z = (k - 0.5 * (count[2] - 1)) * distance[2]

                # Create a matrix with position randomization
                result = Gf.Matrix4d(1)
                result.SetTranslate(
                    Gf.Vec3d(
                        x + random.random() * randomization[0],
                        y + random.random() * randomization[1],
                        z + random.random() * randomization[2],
                    )
                )

                id = int(random.random() * id_count)

                yield (result, id)
