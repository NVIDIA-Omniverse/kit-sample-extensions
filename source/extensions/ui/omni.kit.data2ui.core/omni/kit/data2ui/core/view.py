# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["DDView"]
import asyncio
import inspect
from typing import Any, Dict, Optional
from weakref import WeakKeyDictionary, proxy

import carb.settings
import omni.usd
from omni import ui
from omni.kit.viewport.utility import get_active_viewport
from omni.ui import scene as sc
from pxr import Sdf, Tf, Usd, UsdUtils

from .delegate import Delegate
from .model import ChangeType, Container, Item, Model
from .omniuidelegate import ButtonManipulator


class DDView:
    __root_frame: ui.Frame
    __scene_view: sc.SceneView
    __root_stack: ui.ZStack
    __update_task: asyncio.Task | None

    def __init__(self, model: Model, delegate: Delegate, **kwargs):
        self.model = model
        self.delegate = delegate
        self.__root_stack = ui.ZStack()
        self.__viewport_model = model.create_scene_view_model()

        with self.__root_stack:
            self.__root_frame = ui.Frame(**kwargs)
            use_default = False
            if (
                kwargs.pop("opengl", False)
                or carb.settings.get_settings().get_as_string("/exts/omni.kit.data2ui.core/render_backend") == "opengl"
            ):
                try:
                    from omni.kit.scene_view.opengl import OpenGLSceneView
                except ImportError:
                    carb.log_error(
                        "omni.kit.scene_view.opengl must be loaded to use OpenGLSceneView, falling back to omni.ui.SceneView"
                    )
                    use_default = True
                else:
                    self.__scene_view = OpenGLSceneView()
            elif (
                kwargs.pop("opengl_depth", False)
                or carb.settings.get_settings().get_as_string("/exts/omni.kit.data2ui.core/render_backend")
                == "opengl_depth"
            ):
                try:
                    from omni.kit.scene_view.opengl import ViewportOpenGLSceneView
                except ImportError:
                    carb.log_error(
                        "omni.kit.scene_view.opengl must be loaded to use ViewportOpenGLSceneView, falling back to omni.ui.SceneView"
                    )
                    use_default = True
                else:
                    self.__scene_view = ViewportOpenGLSceneView(viewport_api=get_active_viewport())
            elif (
                kwargs.pop("usd", False)
                or carb.settings.get_settings().get_as_string("/exts/omni.kit.data2ui.core/render_backend") == "usd"
            ):
                try:
                    from omni.kit.scene_view.usd import UsdSceneView
                except ImportError:
                    carb.log_error(
                        "omni.kit.scene_view.usd must be loaded to use UsdSceneView, falling back to omni.ui.SceneView"
                    )
                    use_default = True
                else:
                    self.__scene_view = UsdSceneView()
            elif (
                kwargs.pop("xr", False)
                or carb.settings.get_settings().get_as_string("/exts/omni.kit.data2ui.core/render_backend") == "xr"
            ):
                try:
                    from omni.kit.xr.scene_view.core import XRSceneView
                except:
                    carb.log_error(
                        "omni.kit.xr.scene_view.core must be loaded to use XRSceneView, falling back to omni.ui.SceneView"
                    )
                    use_default = True
                else:
                    self.__scene_view = XRSceneView()
            else:
                use_default = True

            if use_default:
                self.__scene_view = sc.SceneView()

        if avw := get_active_viewport():
            avw.add_scene_view(self.__scene_view)

        self.__mapping = WeakKeyDictionary()
        self.__update_task = None
        self.__model_item_subscription = self.model.create_subscription_to_push(
            lambda item, change_type, s=proxy(self): s._on_item_changed(item, change_type), 0, "View Item"
        )
        self.rebuild_all()

    def __del__(self):
        # Temporary. Just mo make sure we don't have circular refs
        # print("DDView is Good")
        pass

    def rebuild_all(self):
        self.__mapping.clear()
        self.__scene_view.scene.clear()
        if self.model.root:
            with self.__root_frame:
                self._build_item(self.model.root)

            with self.__scene_view.scene:
                self.__button_container = ButtonManipulator(model=self.__viewport_model)
            self.__viewport_model.initialize()

    def destroy(self):
        self.__scene_view.scene.clear()

    def _adapt_style(self, style: Dict[str, Dict]):
        """
        Adapt a style dictionary by converting string values that start with '#'
        into colors.

        Args:
            style (Dict[str, Dict]): A dictionary of dictionaries representing a
                                     style.

        Returns:
            Dict[str, Dict]: A new dictionary with the modified values.

        Example usage:
        ```
        style = {
            'Button': {
                'background_color': '#000000',
                'color': '#ffffff'
            }
        }
        new_style = self._adapt_style(style)
        ```

        In the example above, `new_style` would be:
        ```
        {
            'Button': {
                'background-color': <color object>,
                'color': <color object>
            }
        }
        ```
        """
        # create a new empty dictionary to store the modified style
        new_style = {}

        # iterate over each key-value pair in the given style dictionary
        for key, value in style.items():

            if not isinstance(value, dict):
                # We can get dictionaries with no selectors,
                # so just apply the dict-case logic directly to the key/val and direct into the style
                if isinstance(value, str) and value.startswith("#"):
                    new_style[key] = ui.color(value)
                else:
                    new_style[key] = value
                continue

            inner_dict = value

            # create a new empty dictionary to store the modified inner
            # dictionary
            new_inner_dict = {}

            # iterate over each key-value pair in the inner dictionary
            for inner_key, inner_value in inner_dict.items():
                # check if the value is a string that starts with #
                if isinstance(inner_value, str) and inner_value.startswith("#"):
                    # if so, convert the string to a color using the ui.color()
                    # method and add it to the new inner dictionary
                    new_inner_dict[inner_key] = ui.color(inner_value)
                else:
                    # if not, add the original value to the new inner dictionary
                    new_inner_dict[inner_key] = inner_value

            # add the new inner dictionary to the new style dictionary with the
            # corresponding key
            new_style[key] = new_inner_dict

        # return the new style dictionary with the modified values
        return new_style

    def _sync_properties(self, item: Item, widget: Any):
        """Sync from model to delegate"""
        for property_name, value in item.get_properties().items():
            if value is None:
                # Default value
                pass
            elif property_name in ["width", "height"]:
                # It's a special case for width/height. We only set it if there
                # is a value. Otherwise it's Fraction(1)
                # TODO: It's omni.ui specific, we need to move it to the delegate
                if value < 0.0:
                    value = ui.Fraction(value)
                else:
                    value = ui.Pixel(value)
                setattr(widget, property_name, value)
            elif hasattr(widget, property_name):
                # We have several types like ui.Length that can't be set from
                # UsdAttribute. We need to explicitly do type conversion
                value_before = getattr(widget, property_name)
                if property_name == "style":
                    # Special case: style
                    if value != value_before and isinstance(value, dict):
                        setattr(widget, property_name, self._adapt_style(value))
                elif value_before is not None:
                    PropertyType = value_before.__class__
                    if isinstance(value, str) and hasattr(PropertyType, "__entries"):
                        # Special case: pybind11 enums
                        entries = getattr(PropertyType, "__entries")
                        setattr(widget, property_name, entries.get(value, [PropertyType(0)])[0])
                    else:
                        try:
                            # Some of our attributes are read only.
                            setattr(widget, property_name, PropertyType(value))
                        except AttributeError:
                            pass
                else:
                    setattr(widget, property_name, value)

        if isinstance(widget, sc.AbstractManipulatorItem):
            self.__viewport_model.item_changed(widget)

    def _build_item(self, item: Item):
        Widget = self.delegate.get_widget(item)
        if Widget.__name__ == "Label":
            widget = Widget("")  # Victor is this a bug?
        else:
            widget = Widget()

        self._sync_properties(item, widget)
        # Set style
        # Setup callbacks
        self._keep_widget(item, widget)

        if isinstance(item, Container):
            with widget:
                for child in item.children:
                    self._build_item(child)
                    child._parent = item

    def _keep_widget(self, item, widget):
        self.__mapping[item] = widget
        if carb.settings.get_settings().get_as_bool("/exts/omni.kit.data2ui.core/enable_read_only_properties"):
            widget.set_computed_content_size_changed_fn(self._update_read_only_attributes)

    def _on_widget_changed(self, item, widget):
        # Sync model to delegate
        # item.property = widget.property
        # TODO
        ...

    def _refresh_container(self, item):
        if isinstance(item, Container) and item in self.__mapping:
            self.__mapping[item].clear()
            with self.__mapping[item]:
                for child in item.children:
                    self._build_item(child)
                    child._parent = item

        elif item._parent:
            self._refresh_container(item._parent)

    def _on_item_changed(self, item, change_type):
        if change_type == ChangeType.REMOVED:
            if widget := self.__mapping.pop(item, None):
                widget.destroy()

            if isinstance(widget, sc.AbstractManipulatorItem):
                self.__viewport_model.item_changed(widget)

        elif change_type == ChangeType.ADDED:
            # If the item has a parent, we have it create the corresponding widget
            if item._parent:
                self._refresh_container(item._parent)

            # No parent, so we need to create the widget here.
            elif item not in self.__mapping:
                self.model.keep_item(item)
                self._build_item(item)

        elif item in self.__mapping:
            item.clear_cache()
            self._sync_properties(item, self.__mapping[item])

    def _update_read_only_attributes(self, *args):
        async def delay_update():
            with Sdf.ChangeBlock():
                for item, widget in self.__mapping.items():
                    if not widget.visible:
                        continue
                    for name in {
                        "screen_position_x",
                        "screen_position_y",
                        "computed_height",
                        "computed_width",
                    }:
                        if (val := getattr(widget, name)) and val != getattr(item, name):
                            setattr(item, name, val)

            self.__update_task = None

        # Currently needing to update the whole tree, primarily because we don't have a callback for screen position
        # changes, so we're relying on the content size changes of parents and/or children to trigger the update.
        # As such a single task is all we need
        if not self.__update_task or self.__update_task.done():
            self.__update_task = asyncio.ensure_future(delay_update())
