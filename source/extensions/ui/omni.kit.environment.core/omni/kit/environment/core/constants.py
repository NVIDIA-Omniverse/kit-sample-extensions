# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
ENVIRONMENT_PRIM_ROOT = "/Environment"
ENVIRONMENT_MATERIALS_ROOT = ENVIRONMENT_PRIM_ROOT + "/Looks"
SKY_PRIM_PATH = ENVIRONMENT_PRIM_ROOT + "/sky"
GROUND_PRIM_PATH = ENVIRONMENT_PRIM_ROOT + "/ground"
GROUND_DEFAULT_SIZE = 5000


class SkyType:
    """A collection of constants that specify available sky types in the omni.kit.environment.core extension.

    It provides identifier values for selecting a sky representation mode for environment rendering.
    """

    HDRI = "HDRI"
    """str: Constant representing the HDRI sky type."""
    DYNAMIC = "Sky"
    """str: Constant representing a dynamic sky type."""
    SCENE = "Scene"
    """str: Constant representing a scene sky type."""


class EnvironmentProperties:
    """
    Date, time, location and ground properties path in environment prim.
    """

    LATITUDE = ENVIRONMENT_PRIM_ROOT + ".location:latitude"
    """str: Environment geographic latitude property path."""
    LONGITUDE = ENVIRONMENT_PRIM_ROOT + ".location:longitude"
    """str: Environment geographic longitude property path."""
    NORTH_ORIENTATION = ENVIRONMENT_PRIM_ROOT + ".location:north_orientation"
    """str: Path for environment north orientation value."""

    CUMULUS_ENABLED = ENVIRONMENT_PRIM_ROOT + ".weather:cumulus_enabled"
    """str: Path controlling cumulus effect enable state."""
    CLOUD_COVERAGE = ENVIRONMENT_PRIM_ROOT + ".weather:cloud_coverage"
    """str: Path to property controlling cloud coverage."""
    HAZE = ENVIRONMENT_PRIM_ROOT + ".weather:haze"
    """str: Path for environment haze settings."""

    TIME_START = ENVIRONMENT_PRIM_ROOT + ".time:start"
    """str: Path indicating the start time property."""
    TIME_END = ENVIRONMENT_PRIM_ROOT + ".time:end"
    """str: Path indicating the end time property."""
    TIME_CURRENT = ENVIRONMENT_PRIM_ROOT + ".time:current"
    """str: Path specifying the current time property."""

    DATE = ENVIRONMENT_PRIM_ROOT + ".date"
    """str: Path for environment date property."""

    GROUND_SIZE = ENVIRONMENT_PRIM_ROOT + ".ground:size"
    """str: Path defining the ground size property."""
    GROUND_TYPE = ENVIRONMENT_PRIM_ROOT + ".ground:type"
    """str: Path for ground type classification."""
    GROUND_MATERIAL_PATH = ENVIRONMENT_PRIM_ROOT + ".ground:material:path"
    """str: Path to the ground material asset."""
    GROUND_MATERIAL_STRENGTH = ENVIRONMENT_PRIM_ROOT + ".ground:material:strength"
    """str: Path for ground material strength property."""

    SCENE_TEMPLATE = ENVIRONMENT_PRIM_ROOT + ".sceneTemplate"
    """str: Path for the scene template property."""


class EnvironmentSettings:
    """
    Settings used in pereference page.
    """

    ROOT = "/persistent/exts/omni.kit.environment.core/rtx/"
    """ROOT (str): Base persistent path for environment settings."""

    ENV_ROOT = ROOT + "env/"
    """ENV_ROOT (str): Directory for environment settings configuration."""
    ENV_AUTO = ENV_ROOT + "auto"
    """ENV_AUTO (str): Automatic configuration path for environment settings."""
    ENV_DEFAULT = ENV_ROOT + "defaultUrl"
    """ENV_DEFAULT (str): Default URL path for environment settings."""

    GROUND_ROOT = ROOT + "ground/"
    """GROUND_ROOT (str): Base directory for ground settings."""
    GROUND_ENABLE = GROUND_ROOT + "enable"
    """GROUND_ENABLE (str): Configuration path to enable ground settings."""
    GROUND_MATERIAL = GROUND_ROOT + "material"
    """GROUND_MATERIAL (str): Path for ground material selection."""
    GROUND_SUB_MATERIAL = GROUND_ROOT + "subId"
    """GROUND_SUB_MATERIAL (str): Identifier for ground sub-material setting."""

    SHOW_LIGHT_WARNING = ROOT + "light/warning"
    """SHOW_LIGHT_WARNING (str): Path for light warning display configuration."""


class PlaySettings:
    """Settings for sunstudy play control."""

    ROOT = "/app/sunstudy/"
    """str: Base path for sunstudy play control."""

    ENABLE = ROOT + "enable"
    """str: Path to enable sunstudy play control."""

    PLAYING = ROOT + "playing"
    """str: Path indicating whether sunstudy is playing."""
    RATE = ROOT + "rate"
    """str: Path for controlling play rate."""
    LOOP = ROOT + "loop"
    """str: Path to set play looping."""

    CURRENT_SKY_PATH = ROOT + "currentSkyPath"
    """str: Path for current sky asset."""
    CURRENT_SKY_TYPE = ROOT + "currentSkyType"
    """str: Path for current sky type."""


class GroundSettings:
    """Settings for ground."""

    ROOT = "/exts/omni.kit.environment.core/ground/"
    """str: Root directory for ground settings."""

    PATH = ROOT + "path"
    """str: Ground path relative to ROOT."""
