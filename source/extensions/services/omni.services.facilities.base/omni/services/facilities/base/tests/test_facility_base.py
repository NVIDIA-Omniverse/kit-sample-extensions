# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from unittest.mock import patch

from omni.kit.test import AsyncTestCase
from omni.services.facilities.base import Facility


class TestFacility(Facility):
    """Service Facility to use in the context of test cases."""

    pass


class BaseFacilityTestCase(AsyncTestCase):
    """Test cases for the base class for Service Facilities."""

    def test_base_class_can_be_stopped(self) -> None:
        """Validate that Service Facilities can be stopped."""
        test_facility = TestFacility()

        with patch.object(target=Facility, attribute="stop") as mock_base_facility_stop:
            test_facility.stop()

        mock_base_facility_stop.assert_called_once()
