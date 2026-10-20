# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["QuickSearchRegistry"]

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type

import omni.ui as ui

from .singleton import Singleton


@Singleton
class QuickSearchRegistry:
    """
    Singleton that keeps all the search engines. It's used to put custom
    search engine to the content browser.
    """

    @dataclass
    class QuickSearchModelHandler:
        """Holds the model, delegate and callbacks"""

        name: str
        model_type: Type[ui.AbstractItemModel]
        delegate_type: Type[ui.AbstractItemDelegate]
        accept_fn: Optional[Callable[[], bool]]
        exclusive_fn: Optional[Callable[[], bool]]
        priority: int
        flat_search: bool
        style: Optional[Dict[str, Any]]

    class _Event(set):
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

    class _QuickSearchSubscription:
        """
        Event subscription.

        _Event has callback while this object exists.
        """

        def __init__(self, handler: "QuickSearchRegistry.QuickSearchModelHandler"):
            """
            Save name and type to the list.
            """
            self._name = handler.name
            QuickSearchRegistry()._models_delegates[self._name] = handler
            QuickSearchRegistry()._on_engines_changed()

        def __del__(self):
            """Called by GC."""
            del QuickSearchRegistry()._models_delegates[self._name]
            QuickSearchRegistry()._on_engines_changed()

    def __init__(self):
        self._models_delegates: Dict[str, QuickSearchRegistry.QuickSearchModelHandler] = {}
        self._on_engines_changed = self._Event()

    def register_quick_search_model(
        self,
        name: str,
        model_type: Type[ui.AbstractItemModel],
        delegate_type: Type[ui.AbstractItemDelegate],
        accept_fn: Callable[[], bool] = None,
        exclusive_fn: Callable[[], bool] = None,
        priority: int = 100,
        flat_search: bool = True,
        style: Optional[Dict[str, Any]] = {},
    ) -> Optional["QuickSearchRegistry._QuickSearchSubscription"]:
        """
        Add a new engine to the registry.

        ### Requirements to the model

        The model should be the same as the regular model for TreeView and
        based on `ui.AbstractItemModel`.

        The model should contain three columns:
         - 0 - Name
         - 1 - Description
         - 2 - Icon

        If the model wants to execute the items when the user press ENTER, it
        should contain the optional method `def execute(self, item)`.

        ### Requirements to the delegate

        A delegate is the same as a regular delegate for TreeView.

        When the model creates a delegate for flat list, it passes the
        keyword argument `flat=True`.

        ### Arguments:
            `name`
                the name of the engine as it appears in the menu.

            `model_type`
                Quick Search will create an object of this type when it needs
                a new search.

            `delegate_type`
                Quick Search will create an object of this type when it needs
                to draw the model.

            `accept_fn`
                Called before the QuickSearch window is shown to determine if
                the model should be shown currently. It's handy to use it for
                additional content for specific windows only.

            `exclusive_fn`
                Called before the QuickSearch window is shown to determine if
                the models that are not exclusive should be hidden. It's handy
                to show the only model for specific windows.

            `flat_search`
                When True, the search results are flattened, so the leaves are
                visible and all the groups are hidden.

            `style`
                Tree delegate style, so that user can define customized quick
                search tree style.

        """
        if name in self._models_delegates:
            # TODO: Warning
            return

        return self._QuickSearchSubscription(
            self.QuickSearchModelHandler(
                name, model_type, delegate_type, accept_fn, exclusive_fn, priority, flat_search, style
            )
        )

    def get_names(self) -> List[str]:
        """Returns all the Quick Search names"""
        return list(sorted(self._models_delegates.keys()))

    def get_quick_search(self, name: str) -> Optional["QuickSearchRegistry.QuickSearchModelHandler"]:
        """Returns the type of derived from AbstractSearchModel for the given name"""
        return self._models_delegates.get(name, None)

    def subscribe_quick_search_changed(self, fn):
        """
        Return the object that will automatically unsubscribe when destroyed.
        """
        return self._EventSubscription(self._on_engines_changed, fn)
