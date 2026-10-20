# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.


import json
from typing import Dict, List, Optional

import carb
import carb.tokens
import omni.client
from omni.kit.browser.folder.core import FileSystemFolder

from .asset import AssetFactory, SimreadyAsset

ASSET_LIST_FILE = "asset_info.json"


class AssetFolder(FileSystemFolder):
    """
    Represent folder to traverse to find SimReady assets.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._asset_by_tags: Optional[Dict[str, List[SimreadyAsset]]] = None
        self._asset_by_labels: Optional[Dict[str, List[SimreadyAsset]]] = None

    @property
    def asset_by_tags(self) -> Dict[str, List[SimreadyAsset]]:
        """
        All assets grouped by tag in this folder, comes from all SimReady assets
        """
        if self._asset_by_tags is None:
            self._asset_by_tags = {}
            for asset in self.files:
                for tag in asset.tags:
                    if tag not in self._asset_by_tags:
                        self._asset_by_tags[tag] = []
                    self._asset_by_tags[tag].append(asset)
            for sub_folder in self.sub_folders:
                asset_by_tags = sub_folder.asset_by_tags
                for tag in asset_by_tags:
                    if tag not in self._asset_by_tags:
                        self._asset_by_tags[tag] = []
                    for asset in asset_by_tags[tag]:
                        if asset not in self._asset_by_tags[tag]:
                            self._asset_by_tags[tag].append(asset)

        return self._asset_by_tags

    @property
    def asset_by_labels(self) -> Dict[str, List[SimreadyAsset]]:
        """
        All assets grouped by label in this folder, comes from all SimReady assets
        """
        if self._asset_by_labels is None:
            self._asset_by_labels = {}
            for asset in self.files:
                for label in asset.labels:
                    if label not in self._asset_by_labels:
                        self._asset_by_labels[label] = []
                    self._asset_by_labels[label].append(asset)

        return self._asset_by_labels

    async def _traverse_folder_async(self, url: str, recurse: bool = True):
        # There will be a json file to list all assets in the folder
        # Here just read the json file to get assets instead of traverse folder
        self._asset_by_tags = None
        self._asset_by_labels = None

        asset_json = await self._load_json()
        if asset_json:
            for asset_data in asset_json:
                asset_data["Root Path"] = self.url
                asset: SimreadyAsset = AssetFactory.create_asset(asset_data)
                if asset:
                    self.files.append(asset)
                else:
                    carb.log_warn(f"Couldn't create asset for url {url}.")

        self._on_traverse_async_done()

    async def _load_json(self) -> Optional[List[Dict]]:
        # Load json file to get assets list
        json_file = self.url + "/" + ASSET_LIST_FILE
        result, _ = await omni.client.stat_async(json_file)
        if result != omni.client.Result.OK:
            carb.log_error(f"Cannot find {json_file}, error: {result}")
            return None
        try:
            result, _, content = await omni.client.read_file_async(json_file)
            if result != omni.client.Result.OK:
                carb.log_error(f"Cannot read {json_file}, error: {result}")
                return None
            return json.loads(memoryview(content).tobytes().decode("utf-8"))
        except FileNotFoundError:
            carb.log_info(f"Failed to open {json_file}!")
        except PermissionError:
            carb.log_error(f"Cannot read {json_file}: permission denied!")
        except Exception as exc:
            carb.log_error(f"Unknown failure to read {json_file}: {exc}")

        return None
