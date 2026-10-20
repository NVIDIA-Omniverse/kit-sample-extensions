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

import carb.settings
import omni.kit.test
from omni.services.core import main
from omni.services.transport.server.base import utils
from omni.services.transport.server.http.server import HTTPServerExtension, SSLConfigurationError


class TestHTTPServer(omni.kit.test.AsyncTestCase):

    async def setUp(self) -> None:
        self._server_extension = HTTPServerExtension()
        self._server_extension.on_startup()

    async def tearDown(self) -> None:
        self._server_extension.on_shutdown()
        self._server_extension = None

        settings = carb.settings.get_settings_interface()
        settings.destroy_item("exts/omni.services.transport.server.http/ssl/ssl_keyfile")
        settings.destroy_item("exts/omni.services.transport.server.http/ssl/ssl_certfile")
        settings.destroy_item("exts/omni.services.transport.server.http/cors/enabled")

    async def test_server_creation(self):
        server = self._server_extension._configure_server(
            "http", "123.456.890.10", 1234, log_level="info", enable_access_logs=True, ssl_config={}
        )
        config = server.config

        self.assertEqual(config.host, "123.456.890.10")
        self.assertEqual(config.port, 1234)
        self.assertEqual(config.log_level, "info")
        self.assertEqual(config.access_log, True)
        self.assertEqual(config.ssl_keyfile, None)

    async def test_http_server_creation(self):
        settings = carb.settings.get_settings_interface()
        settings.set("exts/omni.services.transport.server.http/port", 1234)
        settings.set("exts/omni.services.transport.server.http/host", "1.2.3.4")

        with patch("omni.services.transport.server.base.utils.validate_port", return_value=1234):
            server = self._server_extension._setup_http_server()
            config = server.config
            self.assertEqual(config.host, "1.2.3.4")
            self.assertEqual(config.port, 1234)
            self.assertEqual(config.log_level, "error")
            self.assertEqual(config.access_log, False)
            self.assertEqual(config.ssl_keyfile, None)

    async def test_http_server_creation_port_change_because_busy(self):
        settings = carb.settings.get_settings_interface()
        settings.set("exts/omni.services.transport.server.http/port", 1234)
        settings.set("exts/omni.services.transport.server.http/host", "1.2.3.4")

        with patch("omni.services.transport.server.base.utils.validate_port", return_value=4321):
            self._server_extension._setup_http_server()
            new_port = settings.get_as_int("exts/omni.services.transport.server.http/port")
            self.assertEqual(new_port, 4321)

    async def test_https_server_no_ssl_keyfile(self):
        with self.assertRaises(SSLConfigurationError):
            self._server_extension._setup_https_server()

    async def test_https_server_creation(self):
        settings = carb.settings.get_settings_interface()
        settings.set("exts/omni.services.transport.server.http/https/port", 1234)
        settings.set("exts/omni.services.transport.server.http/https/host", "1.2.3.4")

        settings.set("exts/omni.services.transport.server.http/ssl/ssl_keyfile", "foo")
        settings.set("exts/omni.services.transport.server.http/ssl/ssl_certfile", "bar")

        with patch("omni.services.transport.server.base.utils.validate_port", return_value=1234):
            server = self._server_extension._setup_https_server()
            config = server.config
            self.assertEqual(config.host, "1.2.3.4")
            self.assertEqual(config.port, 1234)
            self.assertEqual(config.log_level, "error")
            self.assertEqual(config.access_log, False)
            self.assertEqual(config.ssl_keyfile, "foo")
            self.assertEqual(config.ssl_certfile, "bar")

    async def test_server_creation_with_cors(self):
        settings = carb.settings.get_settings_interface()
        settings.set("exts/omni.services.transport.server.http/cors/enabled", True)
        self._server_extension._configure_server(
            "http", "123.456.890.10", 1234, log_level="info", enable_access_logs=True, ssl_config={}
        )

        middleware = main.get_app().user_middleware[0]
        # backward compat access for options (kwargs in latest FastAPI)
        if hasattr(middleware, "options"):
            args = middleware.options
        else:
            args = middleware.kwargs
        self.assertEqual(
            args, {"allow_origins": [], "allow_credentials": False, "allow_methods": [], "allow_headers": []}
        )

    async def test_add_cors_middleware(self):
        self._server_extension._enable_cors_middleware(["foo"], ["POST", "GET"], ["X-HEADER"], True)
        middleware = main.get_app().user_middleware[0]
        if hasattr(middleware, "options"):
            args = middleware.options
        else:
            args = middleware.kwargs
        self.assertEqual(
            args,
            {
                "allow_origins": ["foo"],
                "allow_credentials": True,
                "allow_methods": ["POST", "GET"],
                "allow_headers": ["X-HEADER"],
            },
        )
