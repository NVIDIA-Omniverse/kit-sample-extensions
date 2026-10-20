# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from pathlib import Path
from typing import Union

import carb.settings
from omni.kit.widget.stage.singleton import Singleton


@Singleton
class CollectionIcons:
    """A singleton that scans the icon folder and returns the icon depending on the type"""

    class _Event(list):
        """
        A list of callable objects. Calling an instance of this will cause a
        call to each item in the list in ascending order by index.
        """

        def __call__(self, *args, **kwargs):
            """Called when the instance is “called” as a function"""
            # Call all the saved functions
            for f in self:
                f(*args, **kwargs)

        def __repr__(self):
            """
            Called by the repr() built-in function to compute the “official”
            string representation of an object.
            """
            return f"Event({list.__repr__(self)})"

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
            event.append(self._fn)

        def __del__(self):
            """Called by GC."""
            self._event.remove(self._fn)

    def __init__(self):
        self._on_icons_changed = self._Event()

        self._current_path = Path(__file__).parent
        self._icon_path = self._current_path.parent.parent.parent.parent.joinpath("icons")

        settings = carb.settings.get_settings()
        style = settings.get_as_string("/persistent/app/window/uiStyle")

        if not style:
            # If the style is not available, using the dark style
            style = "NvidiaDark"

        # Read all the svg files in the directory
        self._icons = {icon.stem: str(icon) for icon in self._icon_path.joinpath(style).glob("*.svg")}

        # Pull the icons from the stage widget. If we don't want this dependency, we could move the icons to the omni.kit.widget.stage_icons
        from omni.kit.widget.stage.stage_icons import StageIcons

        self._icons.update(StageIcons()._icons)

    def set(self, prim_type: str, icon_path: Union[str, Path]):
        """Set the new icon path for a specific prim type"""
        if icon_path is None:
            # Remove the icon
            if prim_type in self._icons:
                del self._icons[prim_type]
        else:
            self._icons[prim_type] = str(icon_path)

        self._on_icons_changed()

    def get(self, prim_type: str, default: Union[str, Path] = None) -> str:
        """Checks the icon cache and returns the icon if exists"""
        found = self._icons.get(prim_type)
        if not found and default:
            found = self._icons.get(default)

        if found:
            return found

        return ""

    def subscribe_icons_changed(self, fn):
        """
        Return the object that will automatically unsubscribe when destroyed.
        """
        return self._EventSubscription(self._on_icons_changed, fn)
