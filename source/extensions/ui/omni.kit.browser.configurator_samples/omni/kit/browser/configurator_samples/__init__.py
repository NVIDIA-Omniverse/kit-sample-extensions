# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""Module implementing the SampleBrowserExtension for omni.kit.browser.configurator_samples and providing functions to register and unregister sample folders with integrated UI window and menu support."""

__all__ = ["SampleBrowserExtension", "get_instance", "register_sample_folder", "unregister_sample_folder"]

from .extension import SampleBrowserExtension, get_instance, register_sample_folder, unregister_sample_folder
