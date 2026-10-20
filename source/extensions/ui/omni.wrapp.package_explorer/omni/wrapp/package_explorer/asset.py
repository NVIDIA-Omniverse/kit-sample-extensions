# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import asyncio
import functools
import logging
import os
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

import carb
import omni.client
from omni.kit.browser.folder.core import BrowserFile
from semver import Version

from .style import ICON_PATH
from .utils import call_async

logger = logging.getLogger(__name__)


def semver_sort_key(s):
    """Return a sorting key that prioritizes semantic versioning if applicable."""

    def is_semver(s):
        """Check if a string is a valid semantic version."""
        try:
            Version.parse(s)
            return True
        except ValueError:
            return False

    return (1, Version.parse(s)) if is_semver(s) else (0, s)


class AssetType(Enum):
    """Enumeration of WRAPP asset types.

    Currently supports:
        GENERIC: Generic WRAPP asset type used for most assets
    """

    GENERIC = 1


class WrappAssetFactory:
    """Factory for creating WRAPP asset objects.

    Manages registration and creation of different WRAPP asset types.
    """

    registry: Dict[AssetType, "WrappAsset"] = {}
    """The registry of asset types. Maps asset types to asset classes."""

    @classmethod
    def register(cls, asset_type: AssetType) -> Callable:
        """Decorator. Registers a new asset class as asset_type with the AssetFactory.

        Example:
            Register MyAsset as AssetTypePROP with the AssetFactory

        .. code-block:: python

            @AssetFactory.register(AssetType.PROP)
            class MyMyAsset(BaseAsset):
                pass
        """

        @functools.wraps(cls)
        def inner_wrapper(wrapped_asset_class: Type["WrappAsset"]) -> Type["WrappAsset"]:
            """
            Register the wrapped asset class with the asset factory.
            Return the asset class unaltered.
            """
            if asset_type in cls.registry:
                carb.log_warn("f{asset_type} already registered; will be replaced by {wrapped_asset_class}")
            cls.registry[asset_type] = wrapped_asset_class
            return wrapped_asset_class

        return inner_wrapper

    @classmethod
    async def create_asset(cls, raw_asset_data: Dict) -> Optional["WrappAsset"]:
        """Creates an asset based on a dictionary of data with content specific to the asset type."""
        for asset_class in cls.registry.values():
            if asset_class.is_asset_data(raw_asset_data):
                return asset_class(raw_asset_data)
        return None

    @classmethod
    def num_asset_types(cls) -> int:
        """Returns the number of registered asset types"""
        return len(cls.registry)

    @classmethod
    def dump_asset_types(cls):
        """Prints the list of registered asset types"""
        for asset_type, asset_class in cls.registry.items():
            print(f"asset_type: {asset_type}, asset_class: {asset_class}")


@WrappAssetFactory.register(AssetType.GENERIC)
class WrappAsset(BrowserFile):
    """Base class representing a WRAPP asset.

    Provides core functionality for managing WRAPP asset properties including:
    - Asset metadata (name, type, URL)
    - Asset hierarchy and categorization
    - Version information
    - Variants
    """

    _cached_thumbnail_paths: dict = {}
    _cached_interface_urls: dict = {}

    def __init__(self, raw_asset_data: Dict):
        """Initialize a WRAPP asset.

        WrappAsset instances are created by the WrappAssetFactory. Developers don't need to instantiate
        this and derived classes directly.

        Args:
            raw_asset_data (Dict): Dictionary with data used to initialize the WrappAsset instance.
        """
        self._type = AssetType.GENERIC
        self._name = raw_asset_data.get("asset_name", "")
        self._interface_usd_name = raw_asset_data.get("interface_usd_name")
        self._root_url = omni.client.normalize_url(raw_asset_data.get("root_url", "").rstrip("/"))

        label_dict: Dict[str, Any] = raw_asset_data.get("labels", {})
        self._hierarchy: List[str] = label_dict.get("hierarchy", "").split("/")
        self._tags: List[str] = [tag.strip() for tag in raw_asset_data.get("tags", [])]
        self._extent: List[float] = raw_asset_data.get("extent", [])
        self._qcode: str = label_dict.get("qcode", "").strip()
        self._versions: List[str] = raw_asset_data.get("versions", [])
        self._version: str = raw_asset_data.get("version", self.versions[0] if self._versions else "")

        self._relative_destination: str = raw_asset_data.get("relative_destination", "")
        self._destination_wrapp: str = raw_asset_data.get("destination_wrapp", "")
        self._wrapp_repo_url: str = raw_asset_data.get("wrapp_repo_url", "")

        self._thumbnail_path = raw_asset_data.get("thumbnail_path")
        # Use prepared to check status of file in folder
        # False means this file in cache and not found in last traverse
        # True means this file was found in last traverse
        self.prepared = True
        self._thumbnail_not_found_fn = None
        self._on_interface_usd_url_found_fn = None

    def __hash__(self):
        return hash((self.url, "".join(self.tags)))

    def __repr__(self) -> str:
        return f"[WRAPP Asset]{self.url}"

    def equals(self, other: "BrowserFile") -> bool:
        """
        Check if two file objects are same.
        Returns True means same otherwise False.
        """
        return self.url == other.url and self.tags == other.tags

    @classmethod
    def is_asset_data(cls, raw_asset_data: Dict) -> bool:
        """Returns true if the raw asset data is determined to represent a PROP type asset."""

        asset_type: str = raw_asset_data.get("Asset Type", AssetType.GENERIC.name)
        return asset_type.upper() == AssetType.GENERIC.name

    @property
    def name(self) -> str:
        """The user readable name of this asset."""
        return self._name

    @property
    def asset_type(self) -> AssetType:
        """The type of this asset.

        Must be one of the values in the AssetType enum.
        """
        return self._type

    @property
    def extent_as_str(self) -> str:
        """The extent of this asset in 3D space.

        Example: "20x10.5x0.25"
        """
        return "x".join([str(x) for x in self._extent])

    @property
    def qcode(self) -> str:
        """The Wiki Data QCode of this asset.

        Every asset is identified by a QCode.
        The QCode is used to retrieve the labels from Wiki Data,
        which in effect, act as a classification of the asset.

        Example: "Q11285759"
        """
        return self._qcode

    @property
    def url(self) -> str:
        """The full path to the main file representing the asset.

        This file represents the top-level USD composition arc for a WRAPP package.
        It may take other USD layers and combine them together into one USD file.
        """
        return WrappAsset._cached_interface_urls.get(f"{self._root_url}/{self.version}") or self.get_interface_usd_url()

    @url.setter
    def url(self, value: str):
        raise NotImplementedError("Setting url is not supported for WRAPP assets")

    @property
    def thumbnail(self) -> str:
        full_thumbnail_path = WrappAsset._cached_thumbnail_paths.get(self.url)
        if not full_thumbnail_path:
            full_thumbnail_path = self._get_default_thumbnail_path(self.url)

            # This will check if the thumbnail exists and set the _cached_thumbnail_paths if it does,
            # otherwise it will use the default thumbnail path - No thumbnail icon will be shown
            # Note: this is a future that will run in the background and notify the UI when it's done
            self.populate_thumbnail_url_future()
        return full_thumbnail_path

    @thumbnail.setter
    def thumbnail(self, value: str):
        raise NotImplementedError("Setting thumbnail is not supported for WRAPP assets")

    @property
    def hierarchy(self) -> str:
        """The label hierarchy of this asset.

        This is the same as the "labels" property.
        Examples: ['furniture', 'seat', 'chair', 'armchair']
        """
        hierarchy_list = self._hierarchy[:]  # Make a copy
        if self._versions and self.version != self.versions[0]:
            hierarchy_list.append("Out of Date")
        if self._name not in hierarchy_list:
            hierarchy_list.append(self._name)
        hierarchy = "/".join([segment for segment in hierarchy_list if segment])

        return hierarchy

    @property
    def hierarchy_as_str(self) -> str:
        """The Wiki Data label hierarchy of this asset formatted as a '>' delimited string
        Example: "furniture > seat > chair > armchair"
        """
        reform = " > ".join(self.hierarchy.split("/"))
        return reform

    @property
    def versions(self) -> List[str]:
        """The versions of this asset."""
        return sorted(self._versions, key=semver_sort_key, reverse=True)

    @property
    def version(self) -> str:
        """The version of this asset."""
        return self._version

    @version.setter
    def version(self, value) -> None:
        """Set the version of this asset."""
        self._version = value

    @property
    def tags(self) -> List[str]:
        """The list of tags of this asset.
        Each tag can be a multi-word space delimited string.
        Examples: "car", "three wheeled car", etc
        """
        return self._tags + self.hierarchy.split("/")

    @property
    def tags_as_str(self) -> str:
        """List of comma delimited tag words.

        Note that tags, labels and the QCode are all part of the list of tags
        in order to make searching more effective.

        Example: "residential,furniture,seat,chair,armchair,Q11285759"
        """
        return ",".join(self.tags)

    @property
    def labels(self) -> List[str]:
        """The labels of this asset as a list.

        Labels are hierarchical and can be used to group assets in a tree structure.
        The label hierarchy is determined by a Wiki Data QCode (see https://www.wikidata.org)
        Examples: ['furniture/seat/chair/armchair'], QCode: Q11285759
        """
        return [self.hierarchy]

    @property
    def labels_as_str(self) -> str:
        """The labels of this asset as a comma delimited string.

        Example: "furniture/seat/chair/armchair"
        """
        return ",".join(self.labels)

    @property
    def relative_destination(self) -> str:
        """The relative install destination of this asset."""
        return self._relative_destination

    @property
    def destination_wrapp(self) -> str:
        """The install destination wrapp path. The .wrapp file that records the installation dependencies."""
        return self._destination_wrapp

    @property
    def wrapp_repo_url(self) -> str:
        """The URL of the wrapp repository for this asset source."""
        return self._wrapp_repo_url

    @property
    def installed(self) -> bool:
        """Whether the asset is installed."""
        return "Installed" in self.tags

    def get_url(self, version: str = None, name: str = None, ext: str = "usd") -> str:
        """Get the URL of the asset for a specific version, name and extension.

        Args:
            version (str, optional): The version of the asset to get the URL for. Defaults to the current version.

        Returns:
            str: The URL of the asset for the specified version.
        """
        if version is None:
            version = self.version
        if name is None:
            name = self.name
        return f"{self._root_url}/{version}/{name}.{ext}"

    def set_interface_usd_url_found_fn(self, fn: callable):
        self._on_interface_usd_url_found_fn = fn

    def _on_interface_usd_url_found(self):
        # We updated the url, so we need to update the thumbnail url
        if not WrappAsset._cached_thumbnail_paths.get(self.url):
            self.populate_thumbnail_url_future()
        if self._on_interface_usd_url_found_fn:
            self._on_interface_usd_url_found_fn()

    def populate_interface_usd_url_future(self, url, version_url) -> asyncio.Future:
        """Get the full USD URL of the given package version."""

        url = omni.client.normalize_url(url)
        version_url = omni.client.normalize_url(version_url)

        def _get_first_usd_file_as_interface_usd(future, version_url):
            try:
                _, entries = future.result()
            except asyncio.CancelledError:
                logger.warning("_get_first_usd_file_as_interface_usd cancelled")
                return
            except Exception:
                logger.error("_get_first_usd_file_as_interface_usd raised exception", exc_info=True)
                return

            for entry in entries:
                if entry.relative_path.split(".")[-1] in ["usd", "usda", "usdc", "usdz"]:
                    self._interface_usd_name = entry.relative_path
                    url = f"{version_url}/{self._interface_usd_name}"
                    WrappAsset._cached_interface_urls[f"{version_url}"] = url
                    carb.log_info(
                        f"No default interface USD Found. Use the first USD in the package as the default USD URL: {url}"
                    )
                    self._on_interface_usd_url_found()
                    return
            carb.log_warn(f"No top level usd file found for Wrapp package {version_url}")

        def _ensure_url_exists(future, version_url):
            try:
                result, _ = future.result()
            except asyncio.CancelledError:
                logger.warning("_ensure_url_exists cancelled")
                return
            except Exception:
                logger.error("_ensure_url_exists raised exception", exc_info=True)
                return

            if result == omni.client.Result.OK:
                self._interface_usd_name = url.split("/")[-1]
            else:
                call_async(
                    omni.client.list_async(f"{version_url}/"),
                    lambda f: _get_first_usd_file_as_interface_usd(f, version_url),
                )

        future = call_async(omni.client.stat_async(url), lambda f: _ensure_url_exists(f, version_url))
        return future

    def get_interface_usd_url(self, version: str = None) -> str:
        """Get the full USD URL of the given package version."""
        version = version or self.version
        version_url = f"{self._root_url}/{version}"

        if self._interface_usd_name:
            url = f"{version_url}/{self._interface_usd_name}"
            WrappAsset._cached_interface_urls[version_url] = url
            return url

        # Set default interface USD name first
        url = f"{version_url}/{self.name}.usd"
        WrappAsset._cached_interface_urls[f"{version_url}"] = url

        # This will check if the url exists and set the interface usd name if it does,
        # otherwise it will use the first USD under the version folder as the default USD URL
        # Note: this is a future that will update in the background and notify the UI when it's done
        self.populate_interface_usd_url_future(url, version_url)
        return url

    def set_thumbnail_not_found_fn(self, fn: callable):
        self._thumbnail_not_found_fn = fn

    def _get_default_thumbnail_path(self, url: str):
        url = url or self.url
        url = omni.client.normalize_url(url)
        thumbnail_path = self._thumbnail_path or f".thumbs/256x256/{url.split('/')[-1]}.png"
        return f"{os.path.dirname(url)}/{thumbnail_path}"

    def populate_thumbnail_url_future(self, url: str = None) -> asyncio.Future:
        """Get the thumbnail URL of the given url in a Future object."""
        url = url or self.url
        url = omni.client.normalize_url(url)
        default_thumbnail_path = self._get_default_thumbnail_path(url)

        def _on_stat_thumbnail_url_done(future, url):
            try:
                result, _ = future.result()
            except asyncio.CancelledError:
                logger.warning("_on_stat_thumbnail_url_done cancelled")
                return
            except Exception:
                logger.error("_on_stat_thumbnail_url_done raised exception", exc_info=True)
                return

            if result != omni.client.Result.OK:
                WrappAsset._cached_thumbnail_paths[url] = str(ICON_PATH / "no_preview.png")
                if self._thumbnail_not_found_fn:
                    self._thumbnail_not_found_fn()
            else:
                WrappAsset._cached_thumbnail_paths[url] = default_thumbnail_path

        future = call_async(
            omni.client.stat_async(default_thumbnail_path), lambda f: _on_stat_thumbnail_url_done(f, url)
        )
        return future

    def get_thumbnail_url(self, url: str = None) -> str:
        """Get the thumbnail URL of the given url."""
        url = url or self.url
        url = omni.client.normalize_url(url)
        full_thumbnail_path = WrappAsset._cached_thumbnail_paths.get(url)
        if full_thumbnail_path:
            return full_thumbnail_path
        else:
            self.populate_thumbnail_url_future(url)

        return self._get_default_thumbnail_path(url)
