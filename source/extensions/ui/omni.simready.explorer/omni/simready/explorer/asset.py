# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import abc
import functools
import os
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

import carb
from omni.kit.browser.folder.core import BrowserFile


class AssetType(Enum):
    """SimReady asset types.

    An asset type derived from SimreadyAsset is expected to be of one of these types.
    The AssetType values are used when registering a new asset type with the AssetFactory,
    using the AssetFactory.register() decorator. The asset class should also set its _type
    attribute to the same AssetType value it registered itself with.

    Example:

    .. code-block:: python

        @AssetFactory.register(AssetType.CHARACTER)
        class CharacterAsset(SimreadyAsset):
            def __init__(self):
                self._type = AssetType.CHARACTER

    .. note::

        The SimReady Explorer API does not fully support yet asset classes created by 3rd party developers.
    """

    PROP = 1
    """A non-deformable static object."""
    VEHICLE = 2
    """A vehicle with wheels and doors."""
    CHARACTER = 3
    """A skinned bipedal character with a rig and animations."""
    SCENE = 4
    """A scene with a number of static objects and a ground plane"""
    SIGN = 5
    """Road sign"""
    ROADMARK = 6
    """Marks on the road used to direct traffic"""
    GENERIC = 7
    """Generic asset type"""
    UNKNOWN = 8
    """Non-categorized asset"""


class SimreadyAsset(BrowserFile, abc.ABC):
    """Base class for SimReady assets.

    SimreadyAsset is an abstract type that implements the common behavior of all SimReady assets.
    Derived classes can further refine and customize the semantics of a Simready asset.

    A SimReady asset is a collection of sublayers and other data files usually grouped in a folder.
    The SimReady Specification <todo: add link> defines the structure of a SimReady asset in detail.
    At a high level, a SimReady asset is comprised of:

    * Main file : {asset_name}.usd
    * Sublayers : {asset_name}_{description}.usd
    * Materials: all mdl or usd material data
    * Textures: all image data pertaining to materials
    * Thumbnails: thumbnail images of the asset

    SimReady assets expose a number of behaviors such as physics, appearance, etc.
    Assets can also have behaviors that are specific to their type. For example, vehicles
    may have the number of wheels and doors as part of their behavior.

    SimReady assets can be tagged. Tags are space delimited groups of words used in
    filtering assets in an asset library.

    SimReady assets can be labeled. Hierarchical labels can come from the Wiki Data database (https://www.wikidata.org)
    and are backed by a QCode. The SimReady Explorer displays the labels in the `Category Tree Window`.
    Labels, just like tags can be multi-word, and can be used to search for assets.

    .. note::

        The SimReady Explorer API does not fully support yet asset classes created by 3rd party developers.
    """

    def __init__(self, raw_asset_data: Dict):
        """Initialize a SimReady asset.

        SimReadyAsset instances are created by the AssetFactory. Developers don't need to instantiate
        this and derived classes directly.

        Args:
            raw_asset_data (Dict): Dictionary with data used to initialize the SimreadyAsset instance.
        """
        self._type = AssetType.UNKNOWN
        self._name = raw_asset_data.get("Simple Name", "")
        rel_url = raw_asset_data.get("Relative Path")
        root_url = raw_asset_data.get("Root Path")
        if rel_url.startswith("/") or root_url.endswith("/"):
            url = root_url + rel_url
        else:
            url = root_url + "/" + rel_url
        path = os.path.dirname(url)
        thumbnail_path = raw_asset_data.get("Thumbnail Path", None)
        thumbnail = f"{path}/{thumbnail_path}" if thumbnail_path else None
        label_dict: Dict[str, Any] = raw_asset_data.get("Labels", {})
        self._labels: List[str] = [label_dict.get("Hierarchy", "").strip()]
        self._hierarchy: List[str] = label_dict.get("Hierarchy", "").split("/")
        self._tags: List[str] = [tag.strip() for tag in raw_asset_data.get("Tags", [])]
        self._extent: List[float] = raw_asset_data.get("Extent", [])
        self._qcode: str = label_dict.get("QCode", "").strip()
        self._behaviors: List[Dict] = raw_asset_data.get("Behaviors", [])
        for behavior in self._behaviors:
            if "Value" in behavior:
                behavior["Value"] = behavior["Value"].strip()

        super().__init__(url, thumbnail=thumbnail)

    @classmethod
    @abc.abstractmethod
    def is_asset_data(cls, raw_asset_data: Dict) -> bool:
        """Returns true if the provided raw asset data is determined to represent this asset type.
        To be implemented by derived classes.
        """
        return False

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
    def main_url(self) -> str:
        """The full path to the main file representing the asset.

        This file represents the top-level USD composition arc for a SimReady asset.
        It may take other USD layers and combine them together into one USD file.
        The path is set by the AssetFactory when creating the asset based on the provided raw asset data.
        """
        return self.url

    @property
    def thumbnail_url(self) -> Optional[str]:
        """The full path to the asset's thumbnail image file.

        The thumbnail path is set by the AssetFactory when creating the asset based on the provided raw asset data.
        """
        return self.thumbnail

    @property
    def tags(self) -> List[str]:
        """The list of tags of this asset.

        Each tag can be a multi-word space delimited string.
        Examples: "car", "three wheeled car", etc
        """
        return self._tags

    @property
    def labels(self) -> List[str]:
        """The labels of this asset as a list.

        Labels are hierarchical and can be used to group assets in a tree structure.
        The label hierarchy is determined by a Wiki Data QCode (see https://www.wikidata.org)
        Examples: ['furniture/seat/chair/armchair'], QCode: Q11285759
        """
        return self._labels

    @property
    def labels_as_str(self) -> List[str]:
        """The labels of this asset as a comma delimited string.

        Example: "furniture/seat/chair/armchair"
        """
        return ",".join(self._labels)

    @property
    def tags_as_str(self) -> str:
        """List of comma delimited tag words.

        Note that tags, labels and the QCode are all part of the list of tags
        in order to make searching more effective.

        Example: "residential,furniture,seat,chair,armchair,Q11285759"
        """
        return ",".join(self.tags)

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
    def hierarchy(self) -> str:
        """The Wiki Data label hierarchy of this asset.

        This is the same as the "labels" property.
        Examples: ['furniture', 'seat', 'chair', 'armchair']
        """
        return self._hierarchy

    @property
    def hierarchy_as_str(self):
        """The Wiki Data label hierarchy of this asset formatted as a '>' delimited string
        Example: "furniture > seat > chair > armchair"
        """
        reform = " > ".join(self.hierarchy)
        return reform

    @property
    def physics_variant(self) -> Optional[Dict]:
        """The physics variant set for this asset.

        This dictionary has the following structure:
        {'Prim Path': <prim_path>, 'Values': ['None', 'RigidBody']}
        where <prim_path> is a string representing the path to the prim that contains the physics variant set.
        The name of the Physics variant set is always "PhysicsVariant".
        """
        for behavior in self._behaviors:
            if "PhysicsVariant" in behavior:
                return behavior["PhysicsVariant"]
        return None

    @property
    def behaviors(self) -> Dict[str, List[str]]:
        """The behaviors of this asset.

        The behaviors of this asset is represented as a dictionary of
        variant set names as keys and lists of variant names as values.

        Example: {'PhysicsVariant': ['None', 'RigidBody']}

        """
        behaviors: Dict[str, List[str]] = {}
        for behavior in self._behaviors:
            for variant_set, variant_data in behavior.items():
                if variant_set not in behaviors:
                    behaviors[variant_set] = variant_data["Values"]
        return behaviors

    def __repr__(self) -> str:
        return f"[SimReady Asset]{self.url}"


class AssetFactory:
    """A factory of SimReady asset objects.

    Allows to register asset classes and create instances of them.

    .. note::

        Currently only one asset class can be registered per asset type.
        The last registered asset class of a given type will be used.

        Asset classes created and registered by 3rd party developers are not fully supported yet.
    """

    registry: Dict[AssetType, SimreadyAsset] = {}
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
        def inner_wrapper(wrapped_asset_class: Type[SimreadyAsset]) -> Type[SimreadyAsset]:
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
    def create_asset(cls, raw_asset_data: Dict) -> Optional[SimreadyAsset]:
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


@AssetFactory.register(AssetType.PROP)
class PropAsset(SimreadyAsset):
    """A SimReady prop asset.

    Props are physically based static objects that do not deform and don't have kinematic behavior.
    Examples include chairs, tools, equipment, containers, etc.
    """

    def __init__(self, raw_asset_data: Dict):
        super().__init__(raw_asset_data)
        self._type = AssetType.PROP

    @classmethod
    def is_asset_data(cls, raw_asset_data: Dict) -> bool:
        """Returns true if the raw asset data is determined to represent a PROP type asset."""

        asset_type: str = raw_asset_data.get("Asset Type", AssetType.UNKNOWN.name)
        return asset_type.upper() == AssetType.PROP.name
