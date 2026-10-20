# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.ext
from omni.kit.widget.stage import StageColumnDelegateRegistry

from .variant_column_delegate import VariantColumnDelegate


class StageVariantWidgetExtension(omni.ext.IExt):
    """The entry point for Stage Window"""

    def on_startup(self):
        # Register column delegates
        self._variant_column_sub = StageColumnDelegateRegistry().register_column_delegate(
            "Variant", VariantColumnDelegate
        )

    def on_shutdown(self):
        self._variant_column_sub = None
