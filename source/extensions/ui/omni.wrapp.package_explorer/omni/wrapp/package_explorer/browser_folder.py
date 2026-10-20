# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple

import carb
import omni.client as omni_client
from omni.kit.browser.folder.core import FileSystemFolder

from .asset import WrappAsset, WrappAssetFactory
from .utils import (
    load_asset_repos_from_wrapp_config,
    load_wrapp_dependencies_json,
    load_wrapp_repo_config_json,
    wrapp_list_repo,
)


class WrappAssetFolder(FileSystemFolder):
    """A folder that contains WRAPP assets.

    Handles traversal and management of WRAPP asset folders including:
    - Asset discovery and loading
    - Version management
    - Package dependency resolution
    """

    _interface_usd_name_mapping: List[Dict[str, str]] = carb.settings.get_settings().get(
        "/exts/omni.wrapp.package_explorer/interface_usd_name_mapping"
    )

    # WRAPP url caches
    _wrapp_url_caches: Dict[str, List[Tuple[str, List[str]]]] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._asset_by_tags: Optional[Dict[str, List[WrappAsset]]] = None
        self._asset_by_labels: Optional[Dict[str, List[WrappAsset]]] = None
        # Store the asset data for wrapp assets - key is the asset url, value is the asset data
        self._wrapp_asset_data: Dict[str, Dict] = {}

    @property
    def asset_by_tags(self) -> Dict[str, List[WrappAsset]]:
        """
        All assets grouped by tag in this folder, comes from all WRAPP assets
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
    def asset_by_labels(self) -> Dict[str, List[WrappAsset]]:
        """
        All assets grouped by label in this folder, comes from all WRAPP assets
        """
        if self._asset_by_labels is None:
            self._asset_by_labels = {}
            for asset in self.files:
                for label in asset.labels:
                    if label not in self._asset_by_labels:
                        self._asset_by_labels[label] = []
                    self._asset_by_labels[label].append(asset)

        return self._asset_by_labels

    @classmethod
    def _get_hierarchy_from_url(cls, url: str) -> str:
        """Get the hierarchy of the given url.

        Args:
            url (str): The URL to parse the hierarchy from

        Returns:
            str: The hierarchy of the given url
        """
        # If there are drive/host/query/port parts in the path - we need to remove it.
        hierarchy = omni_client.break_url(url).path.split(":")[-1]

        # Remove any hidden folders (folder name starting with ".")
        hierarchy = "/".join([segment for segment in hierarchy.split("/") if segment and not segment.startswith(".")])
        return hierarchy

    @classmethod
    def _get_interface_usd_name_from_url(cls, url: str) -> Optional[str]:
        """Get the interface USD name from the given url.

        Args:
            url (str): The URL to get the interface USD name from

        Returns:
            Optional[str]: The interface USD name if found, None otherwise
        """
        interface_usd_name = None
        if cls._interface_usd_name_mapping:
            for item in cls._interface_usd_name_mapping:
                if item["path"] in url:
                    interface_usd_name = item["interface_usd_name"]
                    break
        return interface_usd_name

    @staticmethod
    def _construct_asset_data(url, versions):
        url = omni_client.normalize_url(url)
        segments = url.rstrip("/").split("/")
        name = segments[-1]
        hierarchy = WrappAssetFolder._get_hierarchy_from_url(url)

        asset_data = {
            "asset_name": name,
            "interface_usd_name": WrappAssetFolder._get_interface_usd_name_from_url(url),
            "thumbnail_path": f".thumbs/256x256/{name}.usd.png",
            "root_url": url,
            "Asset Type": "Generic",
            "versions": versions,
            "tags": [],
            "labels": {"Class": f"{name}", "hierarchy": hierarchy},
            "relative_destination": "/".join(["wrapp_assets", hierarchy, name]),
        }
        return asset_data

    @classmethod
    async def wrapp_list_repo(cls, wrapp_repo_url: str) -> AsyncGenerator[Tuple[str, List[str]], None]:
        """List the assets in a WRAPP repository.

        Args:
            wrapp_repo_url (str): URL of the WRAPP repository

        Returns:
            AsyncGenerator[Tuple[str, List[str]], None]: Generator of asset URLs and versions
        """
        if wrapp_repo_url in cls._wrapp_url_caches:
            for asset_root_path, versions in cls._wrapp_url_caches[wrapp_repo_url]:
                yield asset_root_path, versions
        else:
            cls._wrapp_url_caches[wrapp_repo_url] = []
            async for asset_root_path, versions in wrapp_list_repo(wrapp_repo_url):
                cls._wrapp_url_caches[wrapp_repo_url].append((asset_root_path, versions))
                yield asset_root_path, versions

    @classmethod
    def clear_wrapp_url_caches(cls):
        cls._wrapp_url_caches = {}

    async def _get_asset_data_from_wrapp_asset_url(self, wrapp_asset_url: str) -> Optional[Dict[str, Any]]:
        """Retrieve asset data for a given WRAPP asset URL.

        Args:
            wrapp_asset_url (str): URL of the WRAPP asset

        Returns:
            Optional[Dict[str, Any]]: Asset metadata if found, None otherwise
        """
        wrapp_asset_url = omni_client.normalize_url(wrapp_asset_url)
        # First check if we already have the data cached
        if wrapp_asset_url in self._wrapp_asset_data:
            return self._wrapp_asset_data[wrapp_asset_url]

        # If not cached, get the repo URL and cache all assets
        wrapp_repo_url = "/".join(wrapp_asset_url.rstrip("/").split("/")[:-2])
        async for _ in self._create_assets_from_wrapp_repo_url(wrapp_repo_url):
            # Iterate through all assets so they are cached
            pass

        return self._wrapp_asset_data.get(wrapp_asset_url)

    async def _create_assets_from_wrapp_repo_url(self, wrapp_repo_url: str) -> AsyncGenerator[WrappAsset, None]:
        """Create WRAPP assets from a repository URL.

        Args:
            wrapp_repo_url (str): URL of the WRAPP repository

        Yields:
            WrappAsset: Created WRAPP asset objects
        """
        wrapp_repo_url = omni_client.normalize_url(wrapp_repo_url)
        async for asset_root_path, versions in self.wrapp_list_repo(wrapp_repo_url):
            if asset_root_path in self._wrapp_asset_data:
                asset_data = self._wrapp_asset_data[asset_root_path]
            else:
                asset_data = self._construct_asset_data(asset_root_path, versions)
                asset_data["wrapp_repo_url"] = wrapp_repo_url.rstrip("/")
                self._wrapp_asset_data[asset_root_path] = asset_data
            asset: WrappAsset = await WrappAssetFactory.create_asset(asset_data)
            yield asset

    @staticmethod
    async def _load_wrapp_dependencies_json(wrapp_url: str) -> Optional[List[Dict[str, Any]]]:
        """Load dependencies from a .wrapp file.

        Args:
            url (str): URL of the .wrapp file

        Returns:
            List[Dict]: List of dependencies if found, None otherwise
        """
        return await load_wrapp_dependencies_json(wrapp_url)

    @staticmethod
    async def _load_wrapp_repo_config_json(wrapp_config_url: str) -> Optional[List[Dict[str, Any]]]:
        """Load asset_repos from a .wrapp_repo.config file.

        Args:
            url (str): URL of the .wrapp_repo.config file

        Returns:
            List[Dict]: List of repository tuples if found, None otherwise
        """
        return await load_wrapp_repo_config_json(wrapp_config_url)

    async def _traverse_wrapp_dependencies(self, wrapp_url: str):
        wrapp_url = omni_client.normalize_url(wrapp_url)
        if not (wrapp_dependencies_json := await self._load_wrapp_dependencies_json(wrapp_url)):
            carb.log_warn(f"No dependencies found for {wrapp_url}")
            return

        for dependency in wrapp_dependencies_json:
            wrapp_repo_url = dependency.get("repository")
            name = dependency.get("package")
            version = dependency.get("version")
            asset_url = "/".join((wrapp_repo_url, ".packages", name))

            asset_data = await self._get_asset_data_from_wrapp_asset_url(asset_url)
            if not asset_data:
                carb.log_warn(f"No asset data found for {asset_url}")
                continue

            labels = asset_data.get("labels", {})
            labels["hierarchy"] = "Installed"
            asset_data["labels"] = labels
            asset_data["version"] = version
            asset_data["tags"] = asset_data.get("tags", [])
            asset_data["relative_destination"] = dependency.get("relative_destination", "")
            asset_data["destination_wrapp"] = wrapp_url
            asset: WrappAsset = await WrappAssetFactory.create_asset(asset_data)
            if asset:
                self.files.append(asset)
            else:
                carb.log_warn(f"Couldn't create asset for url {asset_url}.")

    async def _traverse_wrapp_repo_config(self, url: str):
        """Read the .wrapp_repo.config or the .wrapp_project.config file to get the asset repos."""
        url = omni_client.normalize_url(url)
        async for repo_name, asset_repo in load_asset_repos_from_wrapp_config(url):
            # Loading source repos
            async for asset_root_path, versions in self.wrapp_list_repo(asset_repo.publish_uri):
                # Retrieve the asset data from the cache
                if asset_root_path in self._wrapp_asset_data:
                    asset_data = self._wrapp_asset_data[asset_root_path]
                else:
                    asset_data = self._construct_asset_data(asset_root_path, versions)
                # We update the hierarchy and the relative destination (install path) that are set in the config file.
                name = asset_data["asset_name"]

                labels = asset_data.get("labels", {})
                display_name = asset_repo.display_name or repo_name
                hierarchy = f"{display_name.strip('/')}/{name.strip('/')}"
                labels["hierarchy"] = hierarchy
                asset_data["labels"] = labels

                asset_data["relative_destination"] = "/".join((asset_repo.install_path, name))
                asset_data["wrapp_repo_url"] = asset_repo.publish_uri

                asset: WrappAsset = await WrappAssetFactory.create_asset(asset_data)
                if asset:
                    self.files.append(asset)
                else:
                    carb.log_warn(f"Couldn't create asset for url {asset_repo.publish_uri}.")

    async def _traverse_wrapp_repo(self, url: str):
        url = omni_client.normalize_url(url)
        # Make sure the url is a wrapp repo - contains a .packages folder
        result, _ = await omni_client.stat_async(f"{url}/.packages")
        if result != omni_client.Result.OK:
            carb.log_warn(f"{url} is not a wrapp repo.")
            return

        async for asset in self._create_assets_from_wrapp_repo_url(url):
            if asset:
                self.files.append(asset)
            else:
                carb.log_warn(f"Couldn't create asset for url {url}.")

    async def _traverse_folder_async(self, url: str) -> None:
        """Traverse a url asynchronously to discover WRAPP assets.

        Args:
            url (str): The URL to traverse. It can be a WRAPP managed folder or a .wrapp file containing the dependencies
        """
        self._asset_by_tags = None
        self._asset_by_labels = None
        if not url:
            return

        # Load wrapp dependencies json - if the url is a .wrapp file
        if url.endswith(".wrapp"):
            await self._traverse_wrapp_dependencies(url)
        # Load wrapp package assets from wrapp repo config.
        elif url.endswith((".wrapp_repo.config", ".wrapp_project.config")):
            await self._traverse_wrapp_repo_config(url)
        # Load wrapp package assets from wrapp directory.
        else:
            await self._traverse_wrapp_repo(url)

        self._on_traverse_async_done()


class WrappAssetLabelFolder(WrappAssetFolder):
    """A folder that contains WRAPP assets with the same label.

    Handles traversal and management of WRAPP asset folders including:
    - Asset discovery and loading
    - Version management
    - Package dependency resolution
    """

    def __init__(self, name, source_folder: WrappAssetFolder, *args, **kwargs):
        super().__init__(name, source_folder.url, *args, **kwargs)
        self._source_folders = [source_folder]
        self._reload_fn = None

    @property
    def source_folders(self) -> List[WrappAssetFolder]:
        return self._source_folders

    def add_source_folder(self, folder: WrappAssetFolder):
        if not isinstance(folder, WrappAssetLabelFolder) and folder not in self._source_folders:
            self._source_folders.append(folder)

    def set_reload_fn(self, reload_fn: Callable[[], None]):
        self._reload_fn = reload_fn

    def reload(self):
        if self._reload_fn:
            self._reload_fn()
