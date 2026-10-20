# SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Callable

import carb
from fastapi import Request, Response
from fastapi.routing import APIRoute

from . import _encoding


class _CompressedRequest(Request):
    async def body(self) -> bytes:
        if not hasattr(self, "_body"):
            body = await super().body()

            # `Content-Encoding` is a list of encodings applied to the body,
            # listed outermost first. Every encoding must be undone, in
            # order, otherwise we hand the caller bytes that still carry
            # one or more undecoded layers.
            #
            # NOTE: the previous implementation broke out of this loop after
            # the first successful decompress, which (a) left trailing
            # encodings in place and (b) made the `except KeyError` handler
            # unreachable for any encoder past index 0. An unknown encoder
            # past the first slot would therefore be silently ignored.
            # See OMPE-91964 / NVBug 6118403.
            for encoder_name in self.headers.getlist("Content-Encoding"):
                try:
                    encoder = _encoding.get_encoder(encoder_name)
                except KeyError:
                    carb.log_error(f"{encoder_name} is not a registered decoder")
                    # Do not silently return partially-decoded bytes; let
                    # the caller see the failure.
                    raise
                body = encoder.decompress(body)

            self._body = body
        return self._body


class CompressedRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            request = _CompressedRequest(request.scope, request.receive)
            return await original_route_handler(request)

        return custom_route_handler
