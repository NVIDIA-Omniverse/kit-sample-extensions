# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.ext
from omni.metrics.assembler.core.bindings._metricsAssembler import (
    release_metrics_assembler_interface,
    release_metrics_assembler_interface_scripting,
)

from .. import get_metrics_assembler_interface


class OmniUsdMetricsAssembler(omni.ext.IExt):
    def __init__(self):
        super().__init__()
        pass

    def on_startup(self):
        # getting plugin to be alive
        self._iface = get_metrics_assembler_interface()

    def on_shutdown(self):
        release_metrics_assembler_interface(self._iface)
        release_metrics_assembler_interface_scripting(self._iface)  # OM-60917
        self._iface = None
