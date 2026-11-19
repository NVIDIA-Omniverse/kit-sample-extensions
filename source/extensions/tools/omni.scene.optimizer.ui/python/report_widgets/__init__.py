# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


# Add imports here so that report.py can find them when attempting to
# dynamically instantiate based on the operation name.
from .coinciding import CoincidingWidget
from .deduplicate import DeduplicateWidget
from .generic import GenericWidget
from .merge import MergeWidget
from .stats import StatsWidget
