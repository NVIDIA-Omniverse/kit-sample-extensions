# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio

from .extension import get_publisher_instance


class PublisherTestHelper:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def wait_process_complete(self):
        publisher_instance = get_publisher_instance()
        if not publisher_instance:
            return

        publish_task = publisher_instance.publish_task
        if not publish_task:
            return

        await asyncio.wait_for(publish_task, None)
