# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["Item", "Container", "Model"]

import abc
import enum
import inspect
from typing import Any, List
from weakref import proxy

from omni.ui import scene as sc

DISABLED_SENTINEL = object()
__all__ = ["DISABLED_SENTINEL"]


class ChangeType(enum.IntEnum):
    REMOVED = 0
    ADDED = 1
    PROPERTY = 2


class _Event(set):
    """
    A list of callable objects. Calling an instance of this will cause a
    call to each item in the list in ascending order by index.
    """

    def __call__(self, *args, **kwargs):
        """Called when the instance is “called” as a function"""
        # Call all the saved functions
        for f in list(self):
            f(*args, **kwargs)

    def __repr__(self):
        """
        Called by the repr() built-in function to compute the “official”
        string representation of an object.
        """
        return f"Event({set.__repr__(self)})"


class _EventSubscription:
    """
    Event subscription.

    _Event has callback while this object exists.
    """

    def __init__(self, event, fn):
        """
        Save the function, the event, and add the function to the event.
        """
        self._fn = fn
        self._event = event
        event.add(self._fn)

    def __del__(self):
        """Called by GC."""
        self._event.remove(self._fn)


class StyleContainer:
    """
    This is the style primitive placeholder
    """

    def __get__(self, instance, owner):
        # omni.ui delegate only supports a dict, so we need to return dict here
        # TODO: We need to modify omnni.ui to support None in style
        return {}


class CallbackContainer:
    """
    The user should reimplement it to set the callabcks to the widgets.
    """

    def __get__(self, instance, owner):
        # We need to return a callabe here. Self works well.
        # Here we return None to make sure the emppty container will not be
        # assigned to the delegate.
        return None


class Item(metaclass=abc.ABCMeta):
    """
    The user is responsible to add own properties.
    The model will detect them.
    Also we can use __getattr__ here.
    """

    __type_subscription: Any

    def __init__(self):
        self._parent: Container | None = None
        self._model = None
        self.__on_item_changed = _Event()
        self._cached = {}

    def _item_changed(self):
        """Called by model when the item is changed"""
        # Call callbacks from create_subscription_to_push
        self.__on_item_changed()

    def create_subscription_to_push(self, callable, event, info):
        """Callable will be called immediatley on item changed"""
        return _EventSubscription(self.__on_item_changed, callable)

    def clear_cache(self):
        self._cached.clear()

    def get_properties(self):
        if not self._cached:
            self._cached.update(
                {
                    name: value
                    for name, value in inspect.getmembers(self)
                    if not name.startswith("_") and value is not DISABLED_SENTINEL
                }
            )
        return self._cached


class Widget(Item):
    width = 0
    height = 0
    tooltip: str = ""
    tooltip_offset_x = 0
    tooltip_offset_y = 0
    style_type_name_override: str = ""
    visible: bool = True
    enabled: bool = True
    checked: bool = False
    style = StyleContainer()
    name = ""
    identifier = ""
    selected: bool = False
    skip_draw_when_clipped: bool = False
    screen_position_x: float = 0
    screen_position_y: float = 0
    computed_height: float = 0
    computed_width: float = 0


class Container(Widget):
    """
    Container is an item with children
    """

    _children_dirty: bool

    @property
    @abc.abstractmethod
    def children(self) -> List[Item]:
        """Returns the list of the children"""
        ...


class SceneViewModel(sc.AbstractManipulatorModel):
    def __init__(self, model: "Model"):
        super().__init__()
        self._model = proxy(model)

    def item_changed(self, item):
        self._item_changed(item)

    def initialize(self):
        pass


class Model:
    all_types = {}

    def __init__(self):
        self.root: Item | None = None
        self.__on_item_changed = _Event()

    @classmethod
    def register_type(cls, ItemType, Data):
        """
        Register the custom model item.
        Registered item will go to the model namespace.
        """

        class TypeRegistry:
            def __init__(self):
                cls.all_types[ItemType] = Data

            def __del__(self):
                del cls.all_types[ItemType]

        return TypeRegistry()

    @classmethod
    def get_item_data(cls, ItemType) -> Any:
        """
        Finds the registered data using item type.
        """
        return cls.all_types[ItemType]

    @classmethod
    def get_type_from_data(cls, Data) -> Any:
        """
        Finds the registered item type using data.
        """
        for key, value in cls.all_types.items():
            if value == Data:
                return key

    def keep_item(self, item: Item):
        item._model = proxy(self)

    def _item_changed(self, item: Item, change_type: ChangeType):
        """Called by model when the item is changed"""
        item._item_changed()
        self.__on_item_changed(item, change_type)

    def create_subscription_to_push(self, callable, event, info):
        """Callable will be called immediatley on item changed"""
        return _EventSubscription(self.__on_item_changed, callable)

    def create_scene_view_model(self) -> SceneViewModel:
        return SceneViewModel(self)


### Predefined types


class Stack(Container):
    spacing = 0
    content_clipping = False
    send_mouse_events_to_back = True
    direction = 0


class VStack(Stack):
    pass


class HStack(Stack):
    pass


class ZStack(Stack):
    pass


class Frame(Container):
    separate_window = False


class CollapsableFrame(Frame):
    title = ""
    collapsed = False


class ScrollingFrame(Frame):
    scroll_x = 0
    scroll_x_max = 100
    scroll_y = 0
    scroll_y_max = 100
    horizontal_scrollbar_policy = 0
    vertical_scrollbar_policy = 0


class Placer(Container):
    offset_x = 0
    offset_y = 0
    drag_axis: bool = False
    draggable: bool = False
    stable_size: bool = False


class Label(Widget):
    text = ""
    alignment = 0
    word_wrap = True
    elided_text = False


class Button(Widget):
    text = ""
    spacing = 0
    image_width = 0
    image_height = 0
    image_url = ""
    clicked_fn = CallbackContainer()


class Image(Widget):
    source_url = ""
    alignment = 0
    fill_policy = 0
    pixel_aligned = False


class Spacer(Widget):
    pass


class Rectangle(Widget):
    pass


class Circle(Widget):
    radius = 0
    arc = 0
    alignment = 0
    size_policy = 0


class Triangle(Widget):
    alignment = 0


class Line(Widget):
    alignment = 0


class ViewportButton(Item):
    visible = True
    enabled = True
    selected = False
    checked = False
    shape = 0
    target_path = None
    height = 20.0
    width = 20.0
    style = StyleContainer()
    image_url = ""
    clicked_fn = CallbackContainer()


class ViewportCircle(Item):
    visible = True
    enabled = True
    selected = False
    checked = False
    shape = 0
    target_path = None
    radius = 20.0
    style = StyleContainer()
    clicked_fn = CallbackContainer()


Stack.__type_subscription = Model.register_type(Stack, None)
VStack.__type_subscription = Model.register_type(VStack, None)
HStack.__type_subscription = Model.register_type(HStack, None)
ZStack.__type_subscription = Model.register_type(ZStack, None)
Frame.__type_subscription = Model.register_type(Frame, None)
ScrollingFrame.__type_subscription = Model.register_type(ScrollingFrame, None)
CollapsableFrame.__type_subscription = Model.register_type(CollapsableFrame, None)
Placer.__type_subscription = Model.register_type(Placer, None)
Label.__type_subscription = Model.register_type(Label, None)
Button.__type_subscription = Model.register_type(Button, None)
Image.__type_subscription = Model.register_type(Image, None)
Rectangle.__type_subscription = Model.register_type(Rectangle, None)
Circle.__type_subscription = Model.register_type(Circle, None)
Triangle.__type_subscription = Model.register_type(Triangle, None)
Line.__type_subscription = Model.register_type(Line, None)
ViewportButton.__type_subscription = Model.register_type(ViewportButton, None)
ViewportCircle.__type_subscription = Model.register_type(ViewportCircle, None)
