# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from logging import warn
from typing import Union

import aioboto3
import carb

from .base import BaseUploadCollector


class S3Collector(BaseUploadCollector):
    """Collect stage related assets and upload to S3."""

    def __init__(
        self,
        usd_path: str,
        collect_dir: str,
        usd_only: bool,
        flat_collection: bool,
        material_only: bool,
        s3_bucket: str,
        aws_region: str = None,
        aws_profile: str = None,
        aws_verify_ssl: Union[str, bool] = None,
        ignore_missing_assets: bool = True,
    ):
        super().__init__(
            usd_path=usd_path,
            collect_dir=collect_dir,
            usd_only=usd_only,
            flat_collection=flat_collection,
            material_only=material_only,
            ignore_missing_assets=ignore_missing_assets,
        )
        self._s3_bucket = s3_bucket
        self._verify_ssl = aws_verify_ssl
        self._session = aioboto3.Session(
            profile_name=aws_profile,
            region_name=aws_region,
        )

    async def _upload(self, source, target) -> bool:
        """Upload the source to the target location.

        Args:
            source (str): source to copy.
            target (str): target the source should be copied to.
        """
        async with self._session.client("s3", verify=self._verify_ssl) as client:
            try:
                with open(source, "rb") as fd:
                    await client.upload_fileobj(fd, self._s3_bucket, target)
            except Exception as exc:
                carb.log_error(f"Unable to upload {source} to {self._s3_bucket}:{target}: {exc} ({type(exc)})")
                raise Exception from exc

        return True
