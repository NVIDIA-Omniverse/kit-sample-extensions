# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from enum import Enum
from pathlib import Path

_ICON_PATH = Path(__file__).parents[4].joinpath("data/icons")


class Icons(str, Enum):
    """
    Asset Validator icon.
    """

    CONTEXT_MENU = f"{_ICON_PATH.joinpath('assetValidatorDark.18x18.png')}"
    """
    Asset Validator icon used in context menu.
    """
    ANALYZE = f"{_ICON_PATH.joinpath('Analyze.svg')}"
    """
    Asset Validator icon for Analyze button.
    """
    FIX = f"{_ICON_PATH.joinpath('FixErrors.svg')}"
    """
    Asset Validator icon for Fix button.
    """
    OPEN_USD = f"{_ICON_PATH.joinpath('USDLogoUnsized.svg')}"
    """
    Asset Validator icon for Open USD.
    """
    WAITING = f"{_ICON_PATH.joinpath('assetValidatorDark.18x18.png')}"
    """
    Asset Validator icon for waiting status.
    """
    SUCCESS = f"{_ICON_PATH.joinpath('assetValidatorActive.18x18.png')}"
    """
    Asset Validator icon for success status.
    """
    WARNING = "resources/glyphs/Warning_Log.svg"
    """
    Omniverse icon for warning status.
    """
    ERROR = "resources/glyphs/Error_Log.svg"
    """
    Omniverse icon for error status.
    """
    INFO = "resources/glyphs/Info_Log.svg"
    """
    Omniverse icon for info status.
    """
    HYPERLINK = "resources/glyphs/link.svg"
    """
    Omniverse icon for hyperlink.
    """
    SETTINGS = "resources/glyphs/settings.svg"
    """
    Omniverse icon for settings.
    """
    FOLDER = "resources/icons/folder_gray.png"
    """
    Omniverse icon for folder.
    """
    ARROW_DOWN = "resources/glyphs/arrow_down.svg"
    """
    Omniverse icon for a dropdown arrow.
    """
    SELECT_PRIM = "resources/glyphs/toolbar_select_prim.svg"
    """
    Omniverse icon for selecting a prim in stage.
    """
