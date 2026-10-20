# SPDX-FileCopyrightText: Copyright (c) 2021-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


__all__ = [
    "_PublicExtension",
    "SceneOptimizerCore",
    "SOPluginVersion",
    "ExecutionContext",
    "ISceneOptimizer",
    "acquire_interface",
    "release_interface",
]


import omni.ext
from usd_optimize.impl.core import *
from usd_optimize.impl.core import UsdOptimizeCore, UsdOptimizePluginVersion

# Compatibility aliases: the core library exposes UsdOptimizeCore / UsdOptimizePluginVersion; export
# the SceneOptimizerCore / SOPluginVersion names too so the UI, analysis extension and other callers
# can use either.
SceneOptimizerCore = UsdOptimizeCore
SOPluginVersion = UsdOptimizePluginVersion

from ..bindings._omni_scene_optimizer_core import *
from .commands import Commands


class _PublicExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._interface = acquire_interface()
        self.commands = Commands(self._interface)

    def on_shutdown(self):  # pragma: no cover
        self.commands.shutdown()
        self.commands = None
        release_interface(self._interface)
