# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# =================================== NOTE ====================================
# The APIs in this file are unfinished and may change in future releases
# Using these is at your own risk, and forward-compatability is not supported

# Python imports
import logging
import socket

# Omniverse imports
import carb
import carb.settings
import omni.ext
import psutil
import zeroconf
from omni.services.core import main

logger = logging.getLogger(__name__)
services = {}


class ZeroConf(omni.ext.IExt):

    def __init__(self) -> None:
        super().__init__()
        self.enabled = False

    def on_startup(self):
        self._settings = carb.settings.get_settings()
        self.enabled = self._settings.get_as_bool("exts/omni.services.transport.server.zeroconf/zeroconf/enabled")
        if self.enabled:
            main.register_endpoint("put", "/zeroconf/{service}/{port}", zeroAdd, tags=["ZeroConf"])
            main.register_endpoint("delete", "/zeroconf/{service}/{port}", zeroRemove, tags=["ZeroConf"])

    def on_shutdown(self):
        if self.enabled:
            main.deregister_endpoint("put", "/zeroconf")
            main.deregister_endpoint("delete", "/zeroconf")

    def add(self, service: str, port: int):
        zeroAdd(service, port)

    def remove(self, service: str, port: int):
        zeroRemove(service, port)

    """
    Return the primary IPv4 IP addresses of this machine
        
    Future: add UI and saved options to select network interface to use
    """

    @classmethod
    def ipAddresses(cls) -> list[str]:
        def validIp(ip) -> bool:
            return not (ip == "" or ip.startswith("127.") or ip.startswith("169.254") or ip == "::1")

        list = []
        interfaces = psutil.net_if_addrs()
        for name, addresses in interfaces.items():
            for addr in addresses:
                if addr.family == socket.AF_INET and validIp(addr.address):
                    list.append(addr.address)
        # keep in canonical order
        list.sort()
        return list


def zeroAdd(service: str, port: int):
    """
    Start advertising the given service name and port number via ZeroConf

    Uses the Python zeroconf module.

    Future: should verify that the service name conforms to requirements such as max length
    and required ".local" suffix. For now call will silently fail if these requirements are not met.
    """
    ipList = ZeroConf.ipAddresses()
    serviceKey = f"{service}/{port}"
    info = zeroInfo(service, port, ipList)
    alreadyRegistered = (
        f'Service "{info.name}" already registered [host={info.server}, ips={info.addresses}, service={info.type}]'
    )
    if serviceKey in services:
        logger.warning(alreadyRegistered)
        return
    zc = zeroconf.Zeroconf(interfaces=ipList)
    try:
        zc.register_service(info)
        logger.info(f'Added service "{info.name}" [host={info.server}, ips={info.addresses}, service={info.type}]')
        services.update({serviceKey: zc})
    except zeroconf.NonUniqueNameException as notUniqueErr:
        logger.info(alreadyRegistered)


def zeroInfo(service: str, port: int, ipList: list[str]) -> zeroconf.ServiceInfo:
    """
    Build a ServiceInfo to be used in the above call to `register_service`, which
    includes the seemingly unused `description` structure.
    """
    "Service description structure - not really used, but required nonetheless"
    description = {"name": "Omniverse ZeroConf %s Server" % service, "vendor": "Nvidia", "version": "0.0.1-alpha.1"}
    if not service.startswith("_"):
        service = "_" + service
    if not service.endswith(".local."):
        service = service + ".local."
    hostname = socket.gethostname()
    serviceType = "%s.%s" % (hostname, service)
    info = zeroconf.ServiceInfo(
        service,
        serviceType,
        # port number - might want to support > 1 server on same machine at some point though..
        port,
        0,
        0,
        description,
    )
    info.addresses = ipList
    logger.info(f'Referenced service "{serviceType}" [host={hostname}, ips={ipList}, service={service}]')
    return info


def zeroRemove(service: str, port: int):
    """
    Stop advertising the given service name and port number via ZeroConf

    Uses the Python zeroconf module
    """
    serviceKey = f"{service}/{port}"
    ipList = ZeroConf.ipAddresses()
    try:
        zc = services[serviceKey]
        info = zeroInfo(service, port, ipList)
        zc.unregister_service(info)
        logger.info(f'Removed service "{info.name}" [host={info.server}, ips={info.addresses}, service={info.type}]')
        del services[serviceKey]
    except:
        logger.warning(f"Attempt to remove unregistered service: {service} on port {port}")
