# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# Those tests work only when `omni.services.core` extension is enabled, otherwise skip those tests.
# Any other import error will be raised, not to skip actual errors:
try:
    from .test_local_client import *
    from .test_url_parsing import *
except ModuleNotFoundError as e:
    if e.name != "omni.services.core":
        raise e
