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

import omni.kit.test
from omni.services.collect.collectors.aws import S3Collector
from omni.services.collect.collectors.base import BaseUploadCollector


class Test_Base(omni.kit.test.AsyncTestCase):

    async def test_copy_task_creates_upload_task(self):
        collector = BaseUploadCollector(
            "omniverse://foo.usd",
            "output_path",
            usd_only=False,
            flat_collection=False,
            material_only=False,
            ignore_missing_assets=False,
        )

        async def _fake_copy(*args, **kwargs):
            return True

        async def _fake_upload_task(*args, **kwargs):
            pass

        with patch(
            "omni.services.collect.collectors.base.BaseUploadCollector.add_upload_task", wraps=_fake_upload_task
        ) as patched:
            with patch("omni.kit.usd.collect.omni_client_wrapper.OmniClientWrapper.copy", wraps=_fake_copy):
                await collector._copy("source", "target")
                patched.assert_called_once_with(source="target")

    async def test_write_task_creates_upload_task(self):
        collector = BaseUploadCollector(
            "omniverse://foo.usd",
            "output_path",
            usd_only=False,
            flat_collection=False,
            material_only=False,
            ignore_missing_assets=False,
        )

        async def _fake_write(*args, **kwargs):
            return True

        async def _fake_upload_task(*args, **kwargs):
            pass

        with patch(
            "omni.services.collect.collectors.base.BaseUploadCollector.add_upload_task", wraps=_fake_upload_task
        ) as patched:
            with patch("omni.kit.usd.collect.omni_client_wrapper.OmniClientWrapper.write", wraps=_fake_write):
                await collector._write("target", "data")
                patched.assert_called_once_with(source="target")

    async def test_add_upload_task(self):
        collector = BaseUploadCollector(
            "omniverse://foo.usd",
            "output_path",
            usd_only=False,
            flat_collection=False,
            material_only=False,
            ignore_missing_assets=False,
        )

        async def _fake_upload(*args, **kwargs):
            pass

        with patch("omni.services.collect.collectors.base.BaseUploadCollector._upload", wraps=_fake_upload) as patched:
            await collector.add_upload_task("/bar/texture.mdl")
            self.assertEqual(len(collector._current_tasks), 1)
            patched.assert_called_once_with("/bar/texture.mdl", "output_path/bar/texture.mdl")
