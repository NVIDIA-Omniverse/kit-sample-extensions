# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
import omni.client
import omni.kit

# NOTE: These classes are mostly unused. However, removing them would be more potentially disruptive, so we are ignoring coverage.


class ServerManager:  # pragma: no cover
    def __init__(self, server):
        self._update_sub = None
        self._server = server
        self._status = omni.client.ConnectionStatus.DISCONNECTED

    def __del__(self):
        self._update_sub = None

    @property
    def url(self):
        return self._server

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value


class OmniConnectionManager:  # pragma: no cover
    _instance = None

    @staticmethod
    def get_instance():
        if OmniConnectionManager._instance is None:
            OmniConnectionManager._instance = OmniConnectionManager()
        return OmniConnectionManager._instance

    def __init__(self):
        # All server status
        self._servers = {}
        # server url from startup panel
        self._startup_server_url = None

        self._accept_all_connections = False

        self._subscription = omni.client.register_connection_status_callback(self._server_status_changed)

    def __del__(self):  # pragma: no cover
        self._subscription = None

    @property
    def accept_all_connections(self):
        return self._accept_all_connections

    @accept_all_connections.setter
    def accept_all_connections(self, value):
        self._accept_all_connections = value

    def _get_server_url(self, url):
        if not url.startswith("omniverse://"):
            url = "omniverse://" + url.split(":")[0]
        return url

    def get_current_server(self):
        return self._startup_server_url

    def get_current_user(self):
        result, info = omni.client.get_server_info(self.get_current_server())
        if result == omni.client.Result.OK:
            return info.username
        else:
            return ""

    def _get_server(self, url):
        if url is None:
            return None

        if url not in self._servers:
            self._servers[url] = ServerManager(url)

        return self._servers[url]

    def _server_status_changed(self, url, status):
        print(f"server {url}: {status}")
        carb.log_info(f"server {url}: {status}")
        server = self._get_server(url)
        server.status = status

        if self._accept_all_connections:
            self._startup_server_url = url
