# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited
import platform
from unittest import skipUnless
from unittest.mock import patch

import omni.kit.test
from omni.services.transport.server.base.utils import validate_port


class TestPortValidation(omni.kit.test.AsyncTestCase):

    @skipUnless(platform.system().lower() == "linux", "Testing linux specific functionality")
    async def test_validate_port_unix(self):
        self._test_validate_port("omni.services.transport.server.base.utils._check_for_unix")

    @skipUnless(platform.system().lower() == "windows", "Testing windows specific functionality")
    async def test_validate_port_windows(self):
        self._test_validate_port("omni.services.transport.server.base.utils._check_for_windows")

    def _test_validate_port(self, func: str):
        def mock_check(*args, **kwargs):
            return True

        with patch(func, wraps=mock_check) as mock:
            validate_port(1234, allow_range=False)
            mock.assert_called_once_with("localhost", 1234)

    async def test_raises_no_range_allowed(self):
        with self.assertRaises(Exception):
            validate_port(0, allow_range=False)

    async def test_port_in_range(self):
        def mock_check(*args, **kwargs):
            return True

        with patch("omni.services.transport.server.base.utils._check_for_unix", wraps=mock_check):
            with patch("omni.services.transport.server.base.utils._check_for_windows", wraps=mock_check):
                port = validate_port(0, allow_range=True, socket_range=(8000, 8010))
                self.assertIn(port, range(8000, 8011))

    async def test_no_port_available(self):

        def mock_check(*args, **kwargs):
            raise Exception("Port unavailable")

        with patch("omni.services.transport.server.base.utils._check_for_unix", wraps=mock_check):
            with patch("omni.services.transport.server.base.utils._check_for_windows", wraps=mock_check):
                with self.assertRaises(Exception):
                    validate_port(1234, allow_range=True, socket_range=(8000, 8010))
