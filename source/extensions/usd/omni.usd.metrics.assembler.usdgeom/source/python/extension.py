# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.ext

from .metricsAssemblerUsdGeom import CameraRuleRegistry


class OmniUsdMetricsAssemblerUsdGeom(omni.ext.IExt):
    """Extension entry point that registers UsdGeom camera unit-conversion
    rules with the core Metrics Assembler on startup and unregisters them on
    shutdown."""

    def __init__(self):
        super().__init__()
        self._registry: CameraRuleRegistry = None

    def on_startup(self, ext_id):
        self._registry = CameraRuleRegistry()
        self._registry.register()

    def on_shutdown(self):
        if self._registry is not None:
            self._registry.unregister()
            self._registry = None
