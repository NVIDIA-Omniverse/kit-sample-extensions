# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import abc
from typing import Optional

import omni.ui as ui

from .asset import SimreadyAsset
from .browser_model import AssetDetailItem
from .browser_property_delegate import BrowserPropertyDelegate


class AssetPropertyDelegate(BrowserPropertyDelegate):
    """Base class for all asset property delegates."""

    @abc.abstractmethod
    def asset_accepted(self, asset: Optional[SimreadyAsset]) -> bool:
        return False

    @abc.abstractmethod
    def show_asset(self, asset: Optional[SimreadyAsset], frame: ui.Frame) -> None:
        pass

    def accepted(self, detail_item: Optional[AssetDetailItem]) -> bool:
        """
        Check if detail item could be shown by this delegate.
        Args:
            detail_item (AssetDetailItem): Detail item to be shown.
        """
        return self.asset_accepted(detail_item.asset if detail_item else None)

    def show(self, detail_item: Optional[AssetDetailItem], frame: ui.Frame) -> None:
        """
        Show detail item with this delegate.
        Args:
            detail_item (AssetDetailItem): Detail item to be shown.
            frame (ui.Frame): Parent frame to put widgets.
        """
        self.show_asset(detail_item.asset if detail_item else None, frame)
