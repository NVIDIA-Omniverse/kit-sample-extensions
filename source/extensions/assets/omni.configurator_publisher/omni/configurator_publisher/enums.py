# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from enum import Enum


class StringEnum(Enum):
    @classmethod
    def values(cls):
        return list(map(lambda c: c.value, cls))


class CollectorSwitches(StringEnum):
    ASCII_TO_BINARY = "collector/ascii_to_binary"
    DEFAULT_PRIM_ONLY = "collector/default_prim_only"
    FLAT_COLLECTION = "collector/flat_collection"


class Phases(StringEnum):
    COLLECT = "collect"
    VALIDATE = "validate"
    OPTIMIZE = "optimize"
    CACHE = "cache"
    PACKAGE = "package"
    # UPLOAD = 'upload'


class ProgressStage(Enum):
    COLLECTING = 0
    BAKING_SBSAR = 1
    OPTIMIZE_SCENE = 2
    GENERATING_UJITSO_CACHE = 3
    PACKAGING = 4
    VALIDATING = 5
    DONE = 1000
