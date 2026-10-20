# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# Tests the main extension registration and initialization
from .test_extension import TestCSVReaderExtension

# Tests end-to-end integration of CSV reader components
from .test_integration import TestCSVReaderIntegration

# Tests the CSV data model and parsing logic
from .test_models import TestCSVReaderModel

# Tests the CSV reader view component
from .test_views import TestCSVReaderView
