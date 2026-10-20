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


class BrowserDelegate:
    @property
    def current_directory(self) -> str:
        pass

    @current_directory.setter
    def current_directory(self, path: str):
        pass


class ContentBrowserDelegate(BrowserDelegate):
    @property
    def current_directory(self) -> str:
        try:
            from omni.kit.window.content_browser import get_content_window

            return get_content_window().get_current_directory()
        except ImportError:
            carb.log_warn("Unable to get content window.")
            return None

    @current_directory.setter
    def current_directory(self, path: str):
        try:
            from omni.kit.window.content_browser import get_content_window

            get_content_window().navigate_to(path)
        except ImportError:
            carb.log_warn("Unable to get content window.")
