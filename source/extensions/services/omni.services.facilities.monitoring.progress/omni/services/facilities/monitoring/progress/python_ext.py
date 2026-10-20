# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.ext
from omni.services.core import main

from .services.progress import router
from .store import ProgressStore


class ProgressExtension(omni.ext.IExt):
    """Progress monitoring Extension."""

    def on_startup(self, ext_id):
        progress_store = ProgressStore()
        router.register_facility("progress_store", progress_store)

        main.register_router(router, prefix="/progress", tags=["progress"])

    def on_shutdown(self):
        main.deregister_router(router, prefix="/progress")
