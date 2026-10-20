# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb

try:
    from omni.kit.widget.examples import register_page

    from .search_field_page import ExtendedSearchFieldPage

    register_page(ExtendedSearchFieldPage())
except Exception as e:
    carb.log_info(f"Failed to add example for search field: {str(e)}")
    pass
