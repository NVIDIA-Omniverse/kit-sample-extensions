# Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["SliderRegistry"]

from typing import Any, Dict, Optional

from .slider_manipulator import SliderManipulator
from .slider_model import SliderModel


class SliderChangedGesture(SliderManipulator.SliderChangedGesture):
    """User part. Called when slider is changed."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_changed(self):
        """Called when the user moved the slider"""
        if not hasattr(self.gesture_payload, "slider_value"):
            return
        # The current slider value is in the payload.
        slider_value = self.gesture_payload.slider_value
        # Change the model. Slider watches it and it will update the mesh.
        self.sender.model.set_floats(self.sender.model.get_item("value"), [slider_value])


class SliderRegistry:
    """
    Created by omni.kit.viewport.registry per viewport. Keeps the manipulator
    and some properties that are needed by the viewport.
    """

    def __init__(self, description: Optional[Dict[str, Any]] = None):
        self.__slider_manipulator = SliderManipulator(model=SliderModel(), gesture=SliderChangedGesture())

    def destroy(self):
        if self.__slider_manipulator:
            self.__slider_manipulator.destroy()
            self.__slider_manipulator = None

    # PrimTransformManipulator & TransformManipulator don't have their own visibility
    @property
    def visible(self):
        return True

    @visible.setter
    def visible(self, value):
        pass

    @property
    def categories(self):
        return ("manipulator",)

    @property
    def name(self):
        return "Example Slider Manipulator"
