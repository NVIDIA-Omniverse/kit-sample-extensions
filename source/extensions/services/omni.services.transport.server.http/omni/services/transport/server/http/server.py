# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import asyncio
import ssl
from typing import Dict, List

import carb
import carb.settings
import omni.ext
from fastapi.middleware.cors import CORSMiddleware
from omni.services.core import main
from omni.services.transport.server.base import utils


class SSLConfigurationError(Exception):
    """Raised when an https server has been enabled but no ssl configuration has been specified."""


class HTTPServerExtension(omni.ext.IExt):
    """HTTP(s) server.

    Uses the services registered with the kit controlport and exposes them over HTTP(S)

    When the extension is enabled the API documentation is available on the following url:
    http://<hostname>:<port>/docs or https://<hostname>:<port>/docs
    """

    def __init__(self):
        super().__init__()
        self._http_server = None
        self._https_server = None

    def on_startup(self):
        self._settings = carb.settings.get_settings()
        if self._settings.get_as_bool("exts/omni.services.transport.server.http/http/enabled"):
            self._http_server = self._setup_http_server()
            asyncio.ensure_future(self._http_server.serve())

        if self._settings.get_as_bool("exts/omni.services.transport.server.http/https/enabled"):
            self._https_server = self._setup_https_server()
            asyncio.ensure_future(self._https_server.serve())

    def _setup_http_server(self):
        host = self._settings.get("exts/omni.services.transport.server.http/host")
        port = self._settings.get_as_int("exts/omni.services.transport.server.http/port")
        log_level = self._settings.get("exts/omni.services.transport.server.http/log_level")
        enable_access_logs = self._settings.get_as_bool("/exts/omni.services.transport.server.http/enable_access_logs")

        allow_range = self._settings.get_as_bool("exts/omni.services.transport.server.http/allow_port_range")
        validated_port = utils.validate_port(port, allow_range=allow_range)
        if validated_port != port:
            carb.log_warn(
                f"http server was meant to start on {port} but port is taken, starting on port {validated_port} instead"
            )
            self._settings.set("exts/omni.services.transport.server.http/port", validated_port)
            port = validated_port

        return self._configure_server("http", host, port, log_level=log_level, enable_access_logs=enable_access_logs)

    def _setup_https_server(self):
        https_config: Dict = self._settings.get("exts/omni.services.transport.server.http/https")
        https_config.pop("enabled")

        ssl_config: Dict = self._settings.get("exts/omni.services.transport.server.http/ssl")
        ssl_config = self._validate_ssl_config(ssl_config)

        https_config["ssl_config"] = ssl_config
        return self._configure_server("https", **https_config)

    def _enable_cors_middleware(
        self, allow_origins: List[str], allow_methods: List[str], allow_headers: List[str], allow_credentials: bool
    ) -> None:
        main.register_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=allow_credentials,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
        )

    def _validate_ssl_config(self, ssl_config: Dict):

        if "ssl_keyfile" not in ssl_config or not ssl_config["ssl_keyfile"]:
            raise SSLConfigurationError(
                "No ssl_keyfile was specified in the settings. An https server cannot be started."
            )

        if "ssl_certfile" not in ssl_config or not ssl_config["ssl_certfile"]:
            raise SSLConfigurationError(
                "No ssl_certfile was specified in the settings. An https server cannot be started."
            )

        ssl_config["ssl_ca_certs"] = ssl_config["ssl_ca_certs"] or None

        ssl_version = ssl_config["ssl_version"]

        # Local import for speed
        from uvicorn import config as _uv_config

        ssl_config["ssl_version"] = ssl_version if ssl_version != -1 else _uv_config.SSL_PROTOCOL_VERSION

        ssl_cert_reqs = ssl_config["ssl_cert_reqs"]
        ssl_config["ssl_cert_reqs"] = ssl_cert_reqs if ssl_cert_reqs != -1 else ssl.CERT_NONE

        return ssl_config

    def _configure_server(
        self, scheme, host, port, log_level="error", loop="asyncio", enable_access_logs=False, ssl_config: Dict = None
    ):
        # local imports for performance
        import uvicorn

        from ._server import _Server

        ssl_config = ssl_config or {}
        config = uvicorn.Config(
            main.get_app(),
            host=host,
            port=port,
            log_level=log_level,
            loop="asyncio",
            access_log=enable_access_logs,
            **ssl_config,
        )

        if self._settings.get_as_bool("exts/omni.services.transport.server.http/cors/enabled"):
            allow_origins = self._settings.get("exts/omni.services.transport.server.http/cors/allow_origins") or []
            allow_credentials = self._settings.get_as_bool(
                "exts/omni.services.transport.server.http/cors/allow_credentials"
            )
            allow_methods = self._settings.get("exts/omni.services.transport.server.http/cors/allow_methods") or []
            allow_headers = self._settings.get("exts/omni.services.transport.server.http/cors/allow_headers") or []
            self._enable_cors_middleware(
                allow_origins=allow_origins,
                allow_methods=allow_methods,
                allow_headers=allow_headers,
                allow_credentials=allow_credentials,
            )

        carb.log_info(f"Server will attempt to start on {scheme}://{host}:{port}")
        return _Server(config=config)

    def on_shutdown(self):
        if self._http_server:
            self._http_server.should_exit = True
            asyncio.get_event_loop().run_until_complete(self._http_server.shutdown())
            self._http_server = None

        if self._https_server:
            self._https_server.should_exit = True
            asyncio.get_event_loop().run_until_complete(self._https_server.shutdown())
            self._https_server = None
