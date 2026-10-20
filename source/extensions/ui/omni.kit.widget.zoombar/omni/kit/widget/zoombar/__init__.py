# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""This module defines the ZoomBar widget with a customizable slider and button to toggle view modes, and the FileZoomBar subclass for file system integration replacing omni.kit.window.filepicker.ZoomBar."""

from .file_zoom_bar import FileZoomBar
from .zoom_bar import ZoomBar

__all__ = ["ZoomBar", "FileZoomBar"]
