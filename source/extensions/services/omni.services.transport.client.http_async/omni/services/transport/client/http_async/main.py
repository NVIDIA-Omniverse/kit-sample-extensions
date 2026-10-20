# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

__all__ = []

import omni.ext
import omni.services.client as _client

from . import consumer


class HTTPAsyncClient(omni.ext.IExt):
    """HTTP asynchronous Client Consumer."""

    def on_startup(self):
        _client.register("http", consumer.HttpAsyncConsumer, is_async=True)
        _client.register("https", consumer.HttpsAsyncConsumer, is_async=True)

    def on_shutdown(self):
        try:
            _client.unregister("http", is_async=True)
        except KeyError:
            pass

        try:
            _client.unregister("https", is_async=True)
        except KeyError:
            pass
