# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

__all__ = ["BrowserPropertyDelegate"]

import abc
import weakref
from typing import List, Optional

import omni.ui as ui

from .browser_model import AssetDetailItem

# Same settings in omni.kit.window.property.templates
LABEL_WIDTH = 160
LABEL_HEIGHT = 18
HORIZONTAL_SPACING = 4


class BrowserPropertyDelegate(abc.ABC):
    """Base class for item property delegates and registry of these same delegate instances.
    Whenever an instance of this class is created, it is automatically registered.
    The BrowserPropertyView will show the Property widget, and will display into it
    all the registered delegates that accept the current item.
    This class is not meant to be instantiated directly, but rather to be subclassed.
    """

    # Use a list to track drag-drop order so that it's deterministic in the event of clashes or cancelation.
    __g_registered = []

    @classmethod
    def get_instances(cls) -> List["BrowserPropertyDelegate"]:
        remove = []
        for wref in BrowserPropertyDelegate.__g_registered:
            obj = wref()
            if obj:
                yield obj
            else:
                remove.append(wref)
        for wref in remove:
            BrowserPropertyDelegate.__g_registered.remove(wref)

    def __init__(self):
        self.__g_registered.append(weakref.ref(self, lambda r: BrowserPropertyDelegate.__g_registered.remove(r)))

    def __del__(self):
        self.destroy()

    def destroy(self):
        for wref in BrowserPropertyDelegate.__g_registered:
            if wref() == self:
                BrowserPropertyDelegate.__g_registered.remove(wref)
                break

    @abc.abstractmethod
    def accepted(self, detail_item: Optional[AssetDetailItem]) -> bool:
        """
        Check if detail item could be shown by this delegate.
        Args:
            detail_item (AssetDetailItem): Detail item to be shown.
        """
        return False

    @abc.abstractmethod
    def show(self, detail_item: Optional[AssetDetailItem], frame: ui.Frame) -> None:
        """
        Show detail item with this delegate.
        Args:
            detail_item (AssetDetailItem): Detail item to be shown.
            frame (ui.Frame): Parent frame to put widgets.
        """
        pass

    @abc.abstractmethod
    def accepted_multiple(self, detail_items: List[AssetDetailItem]) -> bool:
        """
        Check if details of multiple items could be shown by this delegate.
        Args:
            detail_items (List[AssetDetailItem]): Detail items to be shown.
        """
        return False

    @abc.abstractmethod
    def show_multiple(self, detail_items: List[AssetDetailItem], frame: ui.Frame) -> None:
        """
        Show details of multiple items with this delegate.
        The delegate may choose to show common properties of all items.
        Args:
            detail_items (List[AssetDetailItem]): Detail items to be shown.
            frame (ui.Frame): Parent frame to put widgets.
        """
        pass

    def _build_label(
        self, text: str, width: Optional[ui.Length] = LABEL_WIDTH, alignment=ui.Alignment.LEFT_CENTER
    ) -> ui.Label:
        return ui.Label(
            text,
            name="label",
            word_wrap=True,
            width=width if width is not None else LABEL_WIDTH,
            height=LABEL_HEIGHT,
            alignment=alignment,
        )

    def _build_combobox(self, text: str, *args, **kwargs) -> ui.ComboBox:
        with ui.HStack(spacing=HORIZONTAL_SPACING, padding=10):
            ui.Label(text, style_type_name_override="Asset.Label", width=100)

            return ui.ComboBox(*args, name="choices", **kwargs)

    def _build_checkbox(self, model: Optional[ui.AbstractValueModel] = None) -> ui.CheckBox:
        # Copy from UsdPropertiesWidgetBuilder._bool_builder
        with ui.VStack(width=10):
            ui.Spacer()
            widget_kwargs = {"width": 10, "height": 0, "name": "greenCheck", "model": model}
            with ui.ZStack():
                with ui.Placer(offset_x=0, offset_y=-2):
                    checkbox = ui.CheckBox(**widget_kwargs)
                with ui.Placer(offset_x=1, offset_y=-1):
                    ui.Rectangle(height=8, width=8, name="mixed_overlay", alignment=ui.Alignment.CENTER, visible=False)
            ui.Spacer()

        return checkbox  # noqa: R504

    def _build_string_field(self, model: Optional[ui.SimpleStringModel] = None, text: str = "") -> ui.StringField:
        if text:
            with ui.HStack(spacing=HORIZONTAL_SPACING):
                self._build_label(text)
                field = ui.StringField(model, name="models")
            return field
        else:
            return ui.StringField(model, name="models")

    def _build_float_field(self, model: Optional[ui.SimpleFloatModel] = None) -> ui.FloatField:
        return ui.FloatField(model, name="models")

    def _build_float_drag(self, model: Optional[ui.AbstractValueModel] = None, name="models") -> ui.FloatDrag:
        drag = ui.FloatDrag(model, name=name, min=model.min, max=model.max)
        drag.step = max(0.1, (model.max - model.min) / 1000.0)
        return drag

    def _build_int_drag(self, model: Optional[ui.AbstractValueModel] = None, name="models") -> ui.IntDrag:
        kwargs = {}
        if model.min is not None:
            kwargs["min"] = model.min
        if model.max is not None:
            kwargs["max"] = model.max
        drag = ui.IntDrag(model, name="models", **kwargs)
        if model.min is not None and model.max is not None:
            drag.step = max(0.1, (model.max - model.min) / 1000.0)
        return drag

    def _build_float_slider(self, model: Optional[ui.AbstractValueModel] = None, name="models") -> ui.FloatSlider:
        slider = ui.FloatSlider(model, name=name, min=model.min, max=model.max)
        slider.step = max(0.1, (model.max - model.min) / 1000.0)
        return slider
