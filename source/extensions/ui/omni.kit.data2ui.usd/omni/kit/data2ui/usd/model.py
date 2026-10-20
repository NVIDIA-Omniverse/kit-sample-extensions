# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["Model"]


import abc
import re
import traceback
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Set, Union

import carb
import carb.events
import omni.kit.actions.core
import omni.kit.app
import omni.kit.commands
import omni.usd
from omni.ui import color
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdUtils

from ..core import (
    Button,
    CallbackContainer,
    ChangeType,
    Circle,
    CollapsableFrame,
    Container,
    Delegate,
    Frame,
    HStack,
    Image,
    Label,
    Line,
)
from ..core import Model as CoreModel
from ..core import (
    Placer,
    Rectangle,
    ScrollingFrame,
    Spacer,
    Stack,
    StyleContainer,
    Triangle,
    ViewportButton,
    ViewportCircle,
    VStack,
    Widget,
    ZStack,
)
from ..core.model import DISABLED_SENTINEL, SceneViewModel
from .prims import PRIM_NS
from .properties.prim_properties import ATTR_NS, DISABLED_PROPERTY
from .properties.property_enums import (
    get_default_enum_property_value,
    get_style_property_enum_class,
    get_style_property_type,
)


@dataclass
class Event:
    name: str


@dataclass
class Action:
    ext: str
    name: str


@dataclass
class _Command:
    cmd: str


@dataclass
class Command(_Command):
    kwargs: dict = field(default_factory=dict, init=False, repr=False)

    def __init__(self, cmd, **kwargs):
        super().__init__(cmd)
        self.kwargs = kwargs.copy()

    def __repr__(self):
        return super().__repr__()[:-1] + ", " + ", ".join(f"{k}={v!r}" for k, v in self.kwargs.items()) + ")"


def get_message_bus():
    app = omni.kit.app.get_app()
    message_bus = app.get_message_bus_event_stream()
    return message_bus


def _rgb_to_hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def _deep_merge(dict1: Dict[str, Dict[str, Any]], dict2: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Deep merge two dictionaries of dictionaries, returning a new dictionary.

    Args:
        dict1 (Dict[str, Dict[str, Any]]): The first dictionary to merge.
        dict2 (Dict[str, Dict[str, Any]]): The second dictionary to merge.

    Returns:
        Dict[str, Dict[str, Any]]: A new dictionary containing the merged
        values.

    Example usage:
    ```
    dict1 = {
        'key1': {
            'inner_key1': 'value1',
            'inner_key2': 'value2'
        }
    }
    dict2 = {
        'key1': {
            'inner_key2': 'new_value2',
            'inner_key3': 'value3'
        },
        'key2': {
            'inner_key4': 'value4'
        }
    }
    merged_dict = deep_merge_dicts(dict1, dict2)
    ```

    In the example above, `merged_dict` would be:
    ```
    {
        'key1': {
            'inner_key1': 'value1',
            'inner_key2': 'new_value2',
            'inner_key3': 'value3'
        },
        'key2': {
            'inner_key4': 'value4'
        }
    }
    ```
    """
    # create a deep copy of the first dictionary to avoid modifying it
    merged_dict = deepcopy(dict1)

    # iterate over each key-value pair in the second dictionary
    for key, inner_dict in dict2.items():
        # if the key already exists in the merged dictionary, merge the inner
        # dictionary
        if key in merged_dict:
            merged_dict[key].update(inner_dict)
        # otherwise, add the key-value pair to the merged dictionary
        else:
            merged_dict[key] = deepcopy(inner_dict)

    return merged_dict


class USDAttribute:
    """
    A descriptor for USD attributes.

    Args:
        name (str): The name of the attribute.
        owner_name (str): The name of the owner class.
        default_value (Any): The default value of the attribute.

    Returns:
        USDAttribute: A descriptor for USD attributes.
    """

    def __init__(self, name: str, owner_name: str, default_value: Any):
        self._name = name
        self._owner_name = owner_name
        self._default_value = default_value

    def __get__(self, instance, owner):
        """
        Gets the value of the attribute.

        Args:
            instance (Any): The instance of the class.
            owner (Any): The owner of the attribute.

        Returns:
            Any: The value of the attribute.
        """

        attr_name = f"{ATTR_NS}:{self._owner_name}:{self._name}"
        if instance and instance._prim and instance._prim.HasAttribute(attr_name):
            attr = instance._prim.GetAttribute(attr_name)
            if data := (attr.GetMetadata("customData") or {}):
                if data.get(DISABLED_PROPERTY):
                    return DISABLED_SENTINEL

            type_name = attr.GetTypeName()
            value = attr.Get()
            if type_name == Sdf.ValueTypeNames.Asset:
                if value is None:
                    value = ""
                else:
                    value = str(value.resolvedPath)  # Sdf.AssetPath will not be interpreted in style dict correctly
            result = value
            if result is not None:
                return result
            return value
        # TODO: Deal with multiple relationships.
        elif instance and instance._prim and instance._prim.HasRelationship(attr_name):
            if rel := instance._prim.GetRelationship(attr_name):
                for target in rel.GetTargets():
                    if target:
                        return target
                return ""

    def __set__(self, instance, value):
        """
        Write values back to the USD attribute.
        Primarily used for serializing read only values from the UI.

        """
        if value in {self.__get__(instance, None), self._default_value}:
            return
        attr_name = f"{ATTR_NS}:{self._owner_name}:{self._name}"
        if instance and instance._prim and instance._prim.HasAttribute(attr_name):
            attr = instance._prim.GetAttribute(attr_name)
            attr.Set(value)


class USDStyleContainer(StyleContainer):
    """
    This is the style primitive. It should return a dict.
    """

    def __get__(self, instance, owner):
        style: dict[str, Any] = {}

        prim_containers = list(self.get_attached_style_container_prim(instance))
        for prim_container in prim_containers:
            style_prims = set()
            for style_prim in self.get_style_prim(prim_container):
                try:
                    style = _deep_merge(style, self.get_style_dict(style_prim))
                    style_prims.add(style_prim.GetPath())
                except Exception as e:
                    carb.log_error("Exception when creating style")
                    carb.log_error(f"{e}")
                    carb.log_error(f"{traceback.format_exc()}")

            instance._model._cache_style_connection(instance, prim_container.GetPath(), style_prims)

        # if we did not receive style from a bound style container, fall back to prim level style properties
        if not style:
            style_attr_base = f"{ATTR_NS}:Style:"

            if not instance._prim:
                # TODO: We need to modify omni.ui to support None in style
                return {}

            for attr in instance._prim.GetAttributes():
                attr_name = attr.GetName()
                if (
                    attr_name == f"{ATTR_NS}:Style:custom"
                ):  # This is a temporary hack to allow a custom dict to be merged in
                    continue
                if not attr_name.startswith(style_attr_base):
                    continue
                short_attr_name = attr_name.replace(style_attr_base, "")
                style_fragment = attr.Get()
                style_property_type = get_style_property_type(short_attr_name)
                if style_property_type.name == "COLOR":
                    if not style_fragment:
                        style_fragment = attr.GetCustomDataByKey("default")
                    if not style_fragment:
                        style_fragment = color(1.0, 1.0, 1.0, 1.0)
                    else:
                        components = []
                        for _float in style_fragment:
                            components.append(float(_float))
                        components = tuple(components)
                        style_fragment = color(*components)
                elif style_property_type.name == "FLOAT":
                    if style_fragment:
                        style_fragment = float(style_fragment)
                elif style_property_type.name == "ASSET":
                    if style_fragment is None:
                        style_fragment = ""
                    else:
                        style_fragment = str(
                            style_fragment.resolvedPath
                        )  # Sdf.AssetPath will not be interpreted in style dict correctly
                elif style_property_type.name == "ENUM":
                    enum_cls = get_style_property_enum_class(short_attr_name)
                    if style_fragment is None:
                        style_fragment = get_default_enum_property_value(enum_cls)
                    else:
                        style_fragment = getattr(enum_cls, style_fragment)

                if style_fragment:
                    style[short_attr_name] = style_fragment

            if instance._prim.HasAttribute(f"{ATTR_NS}:Style:custom"):
                style_str = instance._prim.GetAttribute(f"{ATTR_NS}:Style:custom").Get()
                if not style_str:
                    style_str = ""
                style_str = style_str.strip()
                if not style_str.startswith("{"):
                    style_str = "{" + style_str + "}"

                try:
                    import omni.ui as ui
                    from omni.ui import color as cl

                    custom_style = eval(style_str)
                    # TODO: check style is correct
                    style.update(custom_style)
                except SyntaxError:
                    pass

        return style

    @staticmethod
    def get_attached_style_container_prim(prim):
        rel_name = f"{ATTR_NS}:Style:binding"
        if not prim._prim or not prim._prim.HasRelationship(rel_name):
            return

        rel: Usd.Relationship = prim._prim.GetRelationship(rel_name)
        if not rel or not rel.HasAuthoredTargets():
            return

        stage = prim._prim.GetStage()
        target: Usd.Relationship
        for target in rel.GetTargets():  # type: ignore
            prim_container = stage.GetPrimAtPath(target)
            if prim_container and prim_container.GetTypeName() == f"{PRIM_NS}StyleContainer":
                yield prim_container

    @staticmethod
    def get_style_prim(prim_container):
        for style_prim in Usd.PrimRange(prim_container):  # type: ignore
            if style_prim and style_prim.GetTypeName() == f"{PRIM_NS}Style":
                yield style_prim

    def get_style_dict(self, prim):
        style = {}

        for attribute in prim.GetAttributes():
            name = attribute.GetBaseName()
            if name not in ["type_name", "name", "state"]:
                type_name = attribute.GetTypeName()
                style_fragment = attribute.Get()
                if type_name == Sdf.ValueTypeNames.Float:
                    style[name] = style_fragment
                elif type_name == Sdf.ValueTypeNames.String:
                    style[name] = style_fragment
                elif type_name == Sdf.ValueTypeNames.Color3f or type_name == Sdf.ValueTypeNames.Color4f:
                    if not style_fragment:
                        style_fragment = attribute.GetCustomDataByKey("default")
                    if not style_fragment:
                        style_fragment = color(1.0, 1.0, 1.0, 1.0)
                    else:
                        components = []
                        for _float in style_fragment:
                            components.append(float(_float))
                        components = tuple(components)
                        style_fragment = color(*components)
                    style[name] = style_fragment
                elif type_name == Sdf.ValueTypeNames.Asset:
                    if style_fragment is None:
                        style_fragment = ""
                    else:
                        style_fragment = str(
                            style_fragment.resolvedPath
                        )  # Sdf.AssetPath will not be interpreted in style dict correctly
                    style[name] = style_fragment

        if style:
            style_key = ""
            if prim.HasAttribute(f"{ATTR_NS}:StyleSelector:type_name"):
                attr_value = prim.GetAttribute(f"{ATTR_NS}:StyleSelector:type_name").Get()
                if attr_value:
                    style_key = attr_value

            if prim.HasAttribute(f"{ATTR_NS}:StyleSelector:name"):
                attr_value = prim.GetAttribute(f"{ATTR_NS}:StyleSelector:name").Get()
                if attr_value:
                    style_key += "::" + attr_value

            if prim.HasAttribute(f"{ATTR_NS}:StyleSelector:state"):
                attr_value = prim.GetAttribute(f"{ATTR_NS}:StyleSelector:state").Get()
                if attr_value:
                    style_key += ":" + attr_value

            style = {style_key: style}

        return style


class USDCallbackContainer(CallbackContainer):
    """
    A simple default callback. It's a callable, so it's possible to save data we
    need to read USD.
    """

    def __call__(self, *args: Any, **kwds: Any):
        # Just for demonstration:
        # print("USDCallbackContainer from usdmodel.py is called", *args, **kwds)
        pass

    def _command_to_lambda(self, _callable: str):
        command = re.match(r"^[Cc]ommand\((.+)\)", _callable)
        if command:
            command_string = command.groups()[0]
            command_segments = [seg.strip() for seg in command_string.split(",")]
            kit_command = command_segments[0]
            remainder = command_segments[1:]
            args = []
            kwargs = {}
            for segment in remainder:
                if "=" in segment:
                    kwarg, value = segment.split("=")
                    kwargs[kwarg] = value
                else:
                    args.append(segment)
            import omni.kit.commands

            return lambda kc=kit_command, args=args, kwargs=kwargs: omni.kit.commands.execute(kc, *args, **kwargs)
        return None

    def _action_to_lambda(self, _callable: str):
        command = re.match(r"^[Aa]ction\((.+)\)", _callable)
        if command:
            command_string = command.groups()[0]
            command_segments = [seg.strip() for seg in command_string.split(",")]
            if len(command_segments) == 2:
                extension_id, action_name = command_segments
                import omni.kit.actions.core

                action_registry = omni.kit.actions.core.get_action_registry()
                action = action_registry.get_action(extension_id, action_name)
                return lambda action=action: action.execute()
        return None

    def _event_to_lambda(self, _callable: str, prim_path: Sdf.Path):
        command = re.match(r"^[Ee]vent\((.+)\)", _callable)
        if command:
            command_string = command.groups()[0]
            command_segments = [seg.strip() for seg in command_string.split(",")]
            event_type = command_segments[0]
            reg_event_name = carb.events.type_from_string(f"{event_type}")
            return lambda event=reg_event_name, prim_path=str(prim_path): get_message_bus().push(
                event, payload={"!path": prim_path}
            )
        return None

    def _fn_str_to_lambda(self, _callable: str, prim_path: Sdf.Path):
        # Leaving the older parsing code in place, mostly as a bridge to keeping older scenes working.
        try:
            callable_object = eval(_callable)
        except Exception as e:
            if _callable.lower().startswith("command(") and _callable.endswith(")"):
                _lambda = self._command_to_lambda(_callable)
                if _lambda:
                    return _lambda
            elif _callable.lower().startswith("action(") and _callable.endswith(")"):
                _lambda = self._action_to_lambda(_callable)
                if _lambda:
                    return _lambda
            elif _callable.lower().startswith("event(") and _callable.endswith(")"):
                _lambda = self._event_to_lambda(_callable, prim_path)
                if _lambda:
                    return _lambda
        else:
            match callable_object:
                case Action(ext, name):
                    action_registry = omni.kit.actions.core.get_action_registry()
                    action = action_registry.get_action(ext, name)
                    return action.execute

                case Event(name):
                    event = carb.events.type_from_string(f"{name}")
                    return lambda: get_message_bus().push(event, payload={"!path": str(prim_path)})

                case Command(cmd) as c:
                    return lambda: omni.kit.commands.execute(cmd, **c.kwargs)

    def __get__(self, instance, owner):
        # Any callable will be called by UI. Normally we need to read USD and
        # return something like a callable that activates omni.graph
        # It's just an example of how to read USD attribute and make a callable
        # based on the result

        if instance._prim:
            type_name = instance._prim.GetTypeName()
            _allow_widgets = [
                (f"{PRIM_NS}Button", "Button:clicked_fn"),
                (f"{PRIM_NS}Image", "Image:pressed_fn"),
                (f"{PRIM_NS}ViewportButton", f"ViewportButton:clicked_fn"),
                (f"{PRIM_NS}ViewportCircle", f"ViewportCircle:clicked_fn"),
            ]
            for widget_type, _attr in _allow_widgets:
                if type_name == widget_type and instance._prim.HasAttribute(f"{ATTR_NS}:{_attr}"):
                    attr = instance._prim.GetAttribute(f"{ATTR_NS}:{_attr}")
                    _callable = attr.Get().strip()
                    _lambda = self._fn_str_to_lambda(_callable, instance._prim.GetPrimPath())
                    if _lambda:
                        return _lambda

        attr_name = f"{ATTR_NS}:Widget:identifier"
        if instance._prim and instance._prim.HasAttribute(attr_name):
            # We can use attributes to create callables
            identifier = instance._prim.GetAttribute(attr_name).Get()
            if identifier:
                return lambda *_, identifier=identifier: print(f"usdmodel.py: The button {identifier} is clicked")

        # Return self means USDCallbackContainer.__call__ will be called
        # It's possible to return None to ignore the callback
        return self


class Usdfier(abc.ABCMeta):
    """
    A metaclass that automatically wraps class attributes with USDAttribute.

    Args:
        type (type): The metaclass type.

    Returns:
        class: A new class with attributes wrapped with USDAttribute.
    """

    @staticmethod
    def _usdfy_property(name: str, value: Any, base_name: str, new_attrs: Dict, already_usdfied: Set):
        """
        Helper method to wrap class attributes with USDAttribute.

        Args:
            name (str): The name of the attribute.
            value (Any): The value of the attribute.
            base_name (str): The name of the base class.
            new_attrs (Dict): The dictionary of new attributes.
            already_usdfied (Set): The set of attributes already wrapped with USDAttribute.
        """
        if name.startswith("_"):
            return

        if isinstance(value, (USDAttribute, USDStyleContainer, USDCallbackContainer, property)) or callable(value):
            already_usdfied.add(name)
            return

        if name in already_usdfied:
            return

        already_usdfied.add(name)

        if isinstance(value, StyleContainer):
            new_attrs[name] = USDStyleContainer()
        elif isinstance(value, CallbackContainer):
            new_attrs[name] = USDCallbackContainer()
        else:
            new_attrs[name] = USDAttribute(name, base_name, value)

    def __new__(cls, name, bases, attrs):
        """
        Creates a new class with attributes wrapped with USDAttribute.

        Args:
            cls (Usdfier): The metaclass instance.
            name (str): The name of the class.
            bases (Tuple): The tuple of base classes.
            attrs (Dict): The dictionary of class attributes.

        Returns:
            class: A new class with attributes wrapped with USDAttribute.
        """
        new_attrs = attrs.copy()
        already_usdfied = set()

        for key, value in new_attrs.items():
            cls._usdfy_property(key, value, name, new_attrs, already_usdfied)

        for base in bases:
            for parent in base.mro():
                for key, value in vars(parent).items():
                    cls._usdfy_property(key, value, parent.__name__, new_attrs, already_usdfied)

        return super().__new__(cls, name, bases, new_attrs)


class UsdWidget(Widget, metaclass=Usdfier):
    def __init__(self, prim: Usd.Prim):
        super().__init__()
        self._prim: Usd.Prim = prim

    def _item_changed(self):
        """Called by model when the item is changed"""
        if self._parent:
            self._parent._children_dirty = True
        super()._item_changed()


class UsdContainer(UsdWidget, Container):
    def __init__(self, prim: Usd.Prim):
        super().__init__(prim)
        self._children_dirty = True
        self._children = []

    @property
    def children(self) -> List[UsdWidget]:
        if self._children_dirty:
            # Lazy
            self._build_children()

        return self._children

    def _build_children(self):
        # Iterate children
        self._children.clear()
        if not self._prim or not self._model:
            return
        for child_prim in self._prim.GetChildren():  # type: ignore
            if not child_prim.GetTypeName().startswith(PRIM_NS):
                continue

            if (item := self._model.get_model_item_from_prim_path(child_prim.GetPrimPath())) is None:
                if (item := self._model.create_model_item_from_prim(child_prim)) is None:
                    continue

            # Track changes in TfNotice
            self._model.keep_item(item)
            self._children.append(item)
        self._children_dirty = False

    def _item_changed(self):
        self._children_dirty = True
        super()._item_changed()


class UsdSceneViewModel(SceneViewModel):
    def initialize(self):
        self.prepopulate_viewport_items()
        return super().initialize()

    def prepopulate_viewport_items(self):
        path: Sdf.Path
        if stage := omni.usd.get_context().get_stage():  # type: ignore
            # Kit 111's usdrt stage has no Fabric query API: find the viewport UI prims on the USD stage.
            names_by_type = {"OmniUI" + name: name for name in ("ViewportButton", "ViewportCircle")}
            for prim in stage.Traverse():
                name = names_by_type.get(str(prim.GetTypeName()))
                if name is None or prim.GetPath() in self._model._items:
                    continue
                if (ItemType := Model.get_type_from_data(name)) is not None:
                    if item := ItemType(prim):
                        self._model.keep_item(item)
                        self._model._item_changed(item, ChangeType.ADDED)


class Model(CoreModel):
    """
    The superclass of the data2ui core model, specialized for USD.

    Caches style connection bindings and reacts to USD item changes.
    """

    def __init__(self, root_prim: Usd.Prim):
        """
        Constructor.

        Args:
            root_prim (Usd.Prim): The root frame prim to use as the container of UI prims.
        """
        super().__init__()

        # TfNotice cache
        # Path to item
        self._items: dict[Sdf.Path, UsdWidget] = {}
        # Styles
        self._container_to_item: defaultdict[UsdWidget, set[Sdf.Path]] = defaultdict(set)
        self._style_to_container: defaultdict[Sdf.Path, set[UsdWidget]] = defaultdict(set)
        self._container_to_style: defaultdict[UsdWidget, set[Sdf.Path]] = defaultdict(set)
        self._target_to_items: dict[Sdf.Path, set[Sdf.Path]] = defaultdict(set)
        # create a root UsdFrame and add it to the model
        self.root = self.get_type_from_data(root_prim.GetTypeName().split(PRIM_NS)[1])(root_prim)  # type: ignore
        self.keep_item(self.root)

        # register a stage listener for changes to the stage
        self._stage_listener = Tf.Notice.Register(
            Usd.Notice.ObjectsChanged, self._on_objects_changed, root_prim.GetStage()
        )

    def __del__(self):
        # Temporary. Just mo make sure we don't have circular refs
        # print("Model is Good")
        pass

    def keep_item(self, item: UsdWidget):
        # keep track of the given UsdWidget item and its path in the _items
        # dictionary
        super().keep_item(item)
        # For TfNotice
        path: Sdf.Path = item._prim.GetPath()  # type: ignore
        self._items[path] = item
        # We also need to track targeted primitives, specifically to sync the target's transform
        # so that viewport drawn widgets update accordingly.
        for targets in item._prim.GetRelationships():
            if targets.GetName().endswith("target_path"):
                for target in targets.GetTargets():
                    self._target_to_items[target].add(path)

    def _style_changed(self, item_path: Sdf.Path, change_type: ChangeType):
        item = self.get_model_item_from_prim_path(item_path)
        if item:
            self._uncache_style_connection(item_path)
            self._item_changed(item, change_type)

    def _cache_style_connection(self, item: Sdf.Path, container: Sdf.Path, styles: Set[Sdf.Path]):
        self._container_to_item[container].add(item._prim.GetPath())
        for style in styles:
            self._container_to_style[container].add(style)
            self._style_to_container[style].add(container)

    def _uncache_style_connection(self, item_path: Sdf.Path):
        containers = [key for key, value in self._container_to_item.items() if item_path in value]
        for container in containers:
            for style in self._container_to_style.get(container, []):
                # Clean up self._style_to_container
                if style in self._style_to_container:
                    value = self._style_to_container[style]
                    if container in value:
                        value.remove(container)
                    if not value:
                        self._style_to_container.pop(style)

            # Clean self._container_to_style
            if container in self._container_to_style:
                self._container_to_style.pop(container)

            # Clean self._container_to_item
            if container in self._container_to_item:
                value = self._container_to_item[container]
                if item_path in value:
                    value.remove(item_path)
                if not value:
                    self._container_to_item.pop(container)

    def _check_style_changed(self, path: Sdf.Path, changed_styles: dict[Sdf.Path, set[Sdf.Path]]):
        # Checking if it's a style
        containers: Iterable[UsdWidget] = self._style_to_container.get(path, [])
        if not containers:
            # Check if a parent is a container
            # TODO: Only check if just created
            for container, items in self._container_to_item.items():
                if path.HasPrefix(container):
                    containers = [container]
                    changed_styles[path] = items
            return

        for container in containers:
            if not container:
                continue

            for item in self._container_to_item.get(container, []):
                if not item:
                    continue

                changed_styles[path].add(item)

    def create_model_item_from_prim(self, prim: Usd.Prim) -> UsdWidget | None:
        if ItemType := self.get_type_from_data(prim.GetTypeName().replace(PRIM_NS, "")):
            return ItemType(prim)

    def get_model_item_from_prim_path(self, prim_path: Sdf.Path) -> UsdWidget | None:
        return self._items.get(prim_path)

    def _on_objects_changed(self, notice: Usd.Notice.ObjectsChanged, sender: Usd.Stage):
        # create a dictionary of items that have changed in the scene
        changed_items: dict[Sdf.Path, UsdWidget] = {}
        changed_properties: dict[Sdf.Path, UsdWidget] = {}
        changed_styles: defaultdict[Sdf.Path, set[Sdf.Path]] = defaultdict(set)
        # process paths that have been resynced (added, removed, or modified)
        for path in notice.GetResyncedPaths():  # type: ignore
            changes = changed_properties if path.IsPropertyPath() else changed_items
            if not (prim := sender.GetPrimAtPath(path)):
                for pth in sorted(self._items):
                    if pth.HasPrefix(path):
                        changes[pth] = self._items.pop(pth)

            elif prim.HasVariantSets() and Sdf.PrimSpec.VariantSelectionKey in notice.GetChangedFields(path):  # type: ignore
                for pth in sorted(self._items):
                    if pth.HasPrefix(path):
                        changed_properties[pth] = self._items[pth]

            for pth, targets in sorted(self._target_to_items.items()):
                if pth.HasPrefix(path):
                    for target in targets:
                        if t := self.get_model_item_from_prim_path(target):
                            changed_properties[target] = t

            if item := self.get_model_item_from_prim_path(path):
                changes[path] = item
            elif parent_path := path.GetParentPath():
                if item := self.get_model_item_from_prim_path(parent_path):
                    changes[parent_path] = item
                elif prim := sender.GetPrimAtPath(path):
                    # Primitive exists, and maps to a UsdWidget, but isn't currently being tracked by the model.
                    # So we create the item, and let the view know it has been added, in which case it can create the
                    # proper widget, and ensure that the item is registered/kept.
                    if item := self.create_model_item_from_prim(prim):
                        changed_items[path] = item

            if not item:
                # TODO: It seems it could be slow. We need to use our regular
                self._check_style_changed(path, changed_styles)

        # process paths that have changed attributes or relationships
        for path in notice.GetChangedInfoOnlyPaths():  # type: ignore
            prim_path = path.GetPrimPath()
            if targets := sender.GetRelationshipAtPath(path):
                for target in targets.GetTargets():
                    self._target_to_items[target].add(prim_path)

            for target_path, targets in self._target_to_items.items():
                if target_path.HasPrefix(prim_path):
                    for target in targets:
                        if target_item := self.get_model_item_from_prim_path(target):
                            changed_properties[target] = target_item

            if item := self.get_model_item_from_prim_path(prim_path):
                changed_properties[prim_path] = item
            else:
                # TODO: It seems it could be slow. We need to use our regular
                self._check_style_changed(prim_path, changed_styles)

        # notify each item in the changed_items dictionary that it has changed
        for path, item in sorted(changed_items.items(), reverse=True):
            p = self.get_model_item_from_prim_path(path.GetParentPath())  # type: ignore
            if isinstance(p, Container):
                path._parent = p
            else:
                path._parent = None

            if sender.GetObjectAtPath(path):
                self._item_changed(item, ChangeType.ADDED)
            else:
                self._item_changed(item, ChangeType.REMOVED)

        for path, item in changed_properties.items():
            self._item_changed(item, ChangeType.PROPERTY)

        for path, items in changed_styles.items():
            for item in items.copy():
                if sender.GetObjectAtPath(path):
                    self._style_changed(item, ChangeType.PROPERTY)
                else:
                    self._style_changed(item, ChangeType.REMOVED)

        # Make sure that UsdSceneView and/or XRSceneView primitives are not pickable.
        omni.usd.get_context().set_pickable("/ui", False)

    def create_scene_view_model(self) -> UsdSceneViewModel:
        return UsdSceneViewModel(self)


class UsdFrame(UsdContainer, Frame):
    def __init__(self, prim: Usd.Prim):
        super().__init__(prim)

    def _build_children(self):
        super()._build_children()
        # It's a feature of Frame, it only has one child
        self._children[:] = self._children[-1:]


class UsdScrollingFrame(UsdFrame, ScrollingFrame):
    pass


class UsdCollapsableFrame(UsdFrame, CollapsableFrame):
    pass


class UsdStack(UsdContainer, Stack):
    pass


class UsdHStack(UsdContainer, HStack):
    pass


class UsdVStack(UsdContainer, VStack):
    pass


class UsdZStack(UsdContainer, ZStack):
    pass


class UsdPlacer(UsdContainer, Placer):
    pass


class UsdLabel(UsdWidget, Label):
    pass


class UsdButton(UsdWidget, Button):
    pass


# Read side of `ui.ImageWithProvider` support, ensures that the current style value aligns with the delegates.
class USDImageWithProviderStyleContainer(USDStyleContainer):
    def __get__(self, inst, owner):
        if inst.source_url:
            return {**super().__get__(inst, owner), "image_url": inst.source_url}
        return super().__get__(inst, owner)


class UsdImage(UsdWidget, Image):
    style = USDImageWithProviderStyleContainer()


class UsdSpacer(UsdWidget, Spacer):
    pass


class UsdRectangle(UsdWidget, Rectangle):
    pass


class UsdTriangle(UsdWidget, Triangle):
    pass


class UsdCircle(UsdWidget, Circle):
    pass


class UsdLine(UsdWidget, Line):
    pass


class UsdViewportButton(ViewportButton, metaclass=Usdfier):
    def __init__(self, prim: Usd.Prim):
        super().__init__()
        self._prim: Usd.Prim = prim

    @property
    def prim_path(self):
        return self._prim.GetPrimPath()


class UsdViewportCircle(ViewportCircle, metaclass=Usdfier):
    def __init__(self, prim: Usd.Prim):
        super().__init__()
        self._prim: Usd.Prim = prim

    @property
    def prim_path(self):
        return self._prim.GetPrimPath()


UsdFrame.__type_subscription = Model.register_type(UsdFrame, "Frame")
UsdScrollingFrame.__type_subscription = Model.register_type(UsdScrollingFrame, "ScrollingFrame")
UsdCollapsableFrame.__type_subscription = Model.register_type(UsdCollapsableFrame, "CollapsableFrame")
UsdStack.__type_subscription = Model.register_type(UsdStack, "Stack")
UsdHStack.__type_subscription = Model.register_type(UsdHStack, "HStack")
UsdVStack.__type_subscription = Model.register_type(UsdVStack, "VStack")
UsdZStack.__type_subscription = Model.register_type(UsdZStack, "ZStack")
UsdPlacer.__type_subscription = Model.register_type(UsdPlacer, "Placer")
UsdLabel.__type_subscription = Model.register_type(UsdLabel, "Label")
UsdButton.__type_subscription = Model.register_type(UsdButton, "Button")
UsdImage.__type_subscription = Model.register_type(UsdImage, "Image")
UsdSpacer.__type_subscription = Model.register_type(UsdSpacer, "Spacer")
UsdRectangle.__type_subscription = Model.register_type(UsdRectangle, "Rectangle")
UsdLine.__type_subscription = Model.register_type(UsdLine, "Line")
UsdCircle.__type_subscription = Model.register_type(UsdCircle, "Circle")
UsdTriangle.__type_subscription = Model.register_type(UsdTriangle, "Triangle")
UsdViewportButton.__type_subscription = Model.register_type(UsdViewportButton, "ViewportButton")
UsdViewportCircle.__type_subscription = Model.register_type(UsdViewportCircle, "ViewportCircle")
