# SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

__all__ = ["ServiceAPIRouter"]


from typing import Any, Callable, List, Optional, Sequence, Type

import fastapi
from fastapi import Response, routing
from fastapi.datastructures import Default
from starlette import routing as starlette_routing
from starlette import types
from starlette.responses import JSONResponse

from . import _route
from .exceptions import ServiceUnavailableError


class ServiceAPIRouter(fastapi.APIRouter):
    """Extended fastapi.APIRouter to support the storing and getting of facilities at runtime.
    Overrides the basic route_class with a class that supports compressed data (like gzip)
    """

    def __init__(
        self,
        routes: Optional[List[starlette_routing.BaseRoute]] = None,
        redirect_slashes: bool = True,
        default: Optional[types.ASGIApp] = None,
        dependency_overrides_provider: Optional[Any] = None,
        route_class: Type[routing.APIRoute] = _route.CompressedRoute,
        default_response_class: Type[Response] = Default(JSONResponse),
        on_startup: Optional[Sequence[Callable]] = None,
        on_shutdown: Optional[Sequence[Callable]] = None,
        prefix: Optional[str] = "",
        tags: Optional[List[str]] = None,
        **kwargs,
    ) -> None:

        if prefix:
            prefix = prefix.replace(".", "/")
            if not prefix.startswith("/"):
                prefix = f"/{prefix}"

        super().__init__(
            routes=routes,
            redirect_slashes=redirect_slashes,
            default=default,
            dependency_overrides_provider=dependency_overrides_provider,
            route_class=route_class,
            default_response_class=default_response_class,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            prefix=prefix,
            tags=tags,
            **kwargs,
        )
        self.route_class = route_class
        self._facilities = {}

    def register_facility(self, name, facility_inst):
        self._facilities[name] = facility_inst

    def get_facility(self, name):
        """Returns a callable for the given name.

        The Facility is injected like Query and Depends are for fastapi:
        https://fastapi.tiangolo.com/tutorial/dependencies/
        https://fastapi.tiangolo.com/tutorial/sql-databases/#create-the-database-tables

        """

        # Returning a callable to follow the fastapi pattern with Query and Depends etc.
        def Facility():
            try:
                return self._facilities[name]
            except KeyError:
                raise ServiceUnavailableError(f"Facility '{name}' not found, have you registered it in the router ?")

        return fastapi.Depends(Facility)


__all__ = ["ServiceAPIRouter"]
