# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["ConfiguratorPublisherExtension"]
import asyncio

import omni.client
import omni.ext
import omni.kit.menu.utils
import omni.kit.pipapi
import omni.usd

# from boto3.exceptions import S3UploadFailedError
# from botocore.exceptions import ClientError
from omni.kit.menu.utils import MenuItemDescription

from .asset_publish_options import AssetPublishOptions
from .package_utils import collect_and_package
from .publisher_window import PublisherWindow

# try:
#     import aioshutil
# except ImportError:
#     omni.kit.pipapi.install("aioshutil", module="aioshutil")
#     import aioshutil
# try:
#     import aioboto3
# except ImportError:
#     omni.kit.pipapi.install("aioboto3", module="aioboto3")
#     import aioboto3
# try:
#     from boto3.session import Session
#     from boto3.s3.transfer import TransferConfig, S3Transfer
#     from boto3.exceptions import  S3UploadFailedError
#     from botocore.exceptions import ClientError
#     from botocore.config import Config
# except ImportError:
#     omni.kit.pipapi.install("boto3", module="boto3")
#     from boto3.session import Session
#     from boto3.s3.transfer import TransferConfig, S3Transfer
#     from boto3.exceptions import  S3UploadFailedError
#     from botocore.exceptions import ClientError
#     from botocore.config import Config
# try:
#     import requests
# except ImportError:
#     omni.kit.pipapi.install("requests", module="requests")
#     import requests
# try:
#     from tqdm import tqdm
# except ImportError:
#     omni.kit.pipapi.install("tqdm", module="tqdm")
#     from tqdm import tqdm

publisher_instance = None


def get_publisher_instance():
    global publisher_instance
    return publisher_instance


class ConfiguratorPublisherExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id):
        global publisher_instance
        publisher_instance = self
        self.__window = PublisherWindow()
        self.__window.visible = False
        self.__window.set_publish_clicked_fn(collect_and_package)

        utilities_items = []
        utilities_items.append(MenuItemDescription(name="Configurator Publisher", onclick_fn=self._menu_on_click))
        self._top_menu = [MenuItemDescription(name="Product Configurator", sub_menu=utilities_items)]
        omni.kit.menu.utils.add_menu_items(self._top_menu, "Tools")

        self.__publish_task = None

    def _menu_on_click(self) -> None:
        """Toggle UI on/off via the Windows menu (Window->Product Configurator->Publish To GDN)."""
        if self.__window:
            self.__window.visible = not self.__window.visible
        else:
            self.__window = PublisherWindow()
            self.__window.visible = True
            self.__window.set_publish_clicked_fn(self.__on_publish)

    # def __on_publish(self, asset_publish_options: AssetPublishOptions, progress_callback=None, **kwargs):
    #     async def __task():
    #         await collect_and_package(asset_publish_options, progress_callback=progress_callback, **kwargs)

    #     self.__publish_task = asyncio.create_task(__task())

    def on_shutdown(self):
        global publisher_instance
        publisher_instance = None
        omni.kit.menu.utils.remove_menu_items(self._top_menu, "Tools")
        self._top_menu = None

        if self.__window:
            self.__window.set_publish_clicked_fn(None)
            self.__window.destroy()
            self.__window = None

    @property
    def publish_task(self):
        return self.__window.publish_task
