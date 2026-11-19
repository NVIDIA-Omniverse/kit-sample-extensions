# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.ext

# The Scene Optimizer rule checkers are provided by the external usd_optimize package
# (usd_optimize.validators). This Kit extension is the integration layer: it registers those rules
# with Asset Validator and stands down the built-in AV checkers that the Scene Optimizer versions
# supersede. usd_optimize is placed on sys.path by the omni.scene.optimizer.core extension, which is
# a dependency of this one, so it is importable here.
import usd_optimize.validators as so_validators
from omni.asset_validator.core import IndexedPrimvarChecker as OldPrimvarChecker
from omni.asset_validator.core import ManifoldChecker as OldManifoldChecker
from omni.asset_validator.core import NormalsValidChecker as OldNormalsValidChecker
from omni.asset_validator.core import ValidationRulesRegistry
from omni.asset_validator.core import WeldChecker as OldWeldChecker
from omni.asset_validator.core import ZeroAreaFaceChecker as OldFaceChecker

# On extension startup, deregister the asset validator checkers that are replaced by the
# scene optimizer versions, and restore them on shutdown.
OLD_RULES = (
    OldPrimvarChecker,
    OldFaceChecker,
    OldManifoldChecker,
    OldNormalsValidChecker,
    OldWeldChecker,
)


class _PublicExtension(omni.ext.IExt):

    def on_startup(self, ext_id):
        """Register the Scene Optimizer validators and stand down the AV checkers they replace."""

        # Iterate over old rules to remove.
        for rule in OLD_RULES:
            ValidationRulesRegistry.deregisterRule(rule)

        # Register the Scene Optimizer rule checkers shipped by the usd_optimize package.
        so_validators.register_all()

    def on_shutdown(self):  # pragma: no cover
        """Tidy up on shutdown"""

        # Unregister the Scene Optimizer rule checkers shipped by the usd_optimize package.
        so_validators.unregister_all()

        # Reregister the asset validator rules that were replaced with scene optimizer rules.
        for rule in OLD_RULES:
            category = ValidationRulesRegistry.category(rule)
            ValidationRulesRegistry.registerRule(rule, category)
