# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""Module omni.kit.thumbnails.mdl provides MDL and USD thumbnail generators, a thumbnail manager for serial processing and retries, and an extension for integrating thumbnail generation preferences into the user interface."""

from .extension import ThunbnailGenerationExtension
from .mdl_thumbnail_generator import MdlThumbnailGenerator
from .thumbnail_manager import ThumbnailManager
from .usd_thumbnail_generator import UsdThumbnailGenerator

__all__ = ["MdlThumbnailGenerator", "ThumbnailManager", "UsdThumbnailGenerator"]
