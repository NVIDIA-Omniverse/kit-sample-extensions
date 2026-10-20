# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from typing import List, Optional

import omni.ui as ui

from .browser_model import WrappAssetDetailItem
from .browser_property_delegate import BrowserPropertyDelegate


class MultiPropertyDelegate(BrowserPropertyDelegate):
    """
    A delegate to show when multiple items are selected.
    """

    def accepted(self, asset: Optional[WrappAssetDetailItem]) -> bool:
        """BrowserPropertyDelegate method override"""
        return False

    def show(self, asset: Optional[WrappAssetDetailItem], frame: ui.Frame) -> None:
        """BrowserPropertyDelegate method override"""
        pass

    def accepted_multiple(self, detail_items: List[WrappAssetDetailItem]) -> bool:
        """BrowserPropertyDelegate method override"""
        return True

    def show_multiple(self, detail_items: List[WrappAssetDetailItem], frame: ui.Frame) -> None:
        """BrowserPropertyDelegate method override"""
        label_text = f"Multiple WRAPP Assets Selected [{len(detail_items)}]"
        if hasattr(self, "_container"):
            self._label.text = label_text
            self._container.visible = True
        else:
            with frame:
                self._container = ui.VStack()
                with self._container:
                    self._label = ui.Label(label_text, alignment=ui.Alignment.CENTER)
