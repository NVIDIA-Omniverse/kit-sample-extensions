# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Data model for the In-App Guide system.

This module defines the data structures and model classes that represent guide steps,
actions, and the overall guide state. It includes classes for different types of guide
steps (window, widget, menu) and their associated reveal actions.
"""

import json
import os
from enum import Enum
from typing import Callable, Dict, List, Optional, Union

import omni.ui as ui


class ActionType(Enum):
    """Enumeration of valid reveal action types.

    Attributes:
        EXPAND: Action that expands a collapsible UI element.
        SCROLL: Action that scrolls to reveal a UI element.
        CLICK: Action that simulates clicking on a UI element.
    """

    EXPAND = "expand"
    SCROLL = "scroll"
    CLICK = "click"


class GuideLink:
    """Represents a link in a guide step.

    Attributes:
        label: The display text for the link.
        url: The URL the link points to.
    """

    def __init__(self, data: Dict):
        """Initialize a guide link from dictionary data.

        Args:
            data: Dictionary containing link data with 'label' and 'url' keys.
        """
        self._label: str = data["label"]
        self._url: str = data["url"]

    @property
    def label(self) -> str:
        """Get the link's display text."""
        return self._label

    @property
    def url(self) -> str:
        """Get the link's target URL."""
        return self._url


class _RevealAction:
    """Base class for actions that reveal UI elements.

    Attributes:
        action_type: The type of reveal action.
        ui_path: The path to the target UI element.
    """

    def __init__(self, data: Dict):
        """Initialize a reveal action from dictionary data.

        Args:
            data: Dictionary containing action data with 'action_type' and 'ui_path' keys.
        """
        self._action_type: ActionType = ActionType(data["action_type"])
        self._ui_path: str = data["ui_path"]

    @property
    def action_type(self) -> ActionType:
        """Get the type of reveal action."""
        return self._action_type

    @property
    def ui_path(self) -> str:
        """Get the path to the target UI element."""
        return self._ui_path


class ClickAction(_RevealAction):
    """Action that simulates clicking on a UI element."""

    def __init__(self, data: Dict):
        """Initialize a click action.

        Args:
            data: Dictionary containing action data.
        """
        super().__init__(data)


class ExpandAction(_RevealAction):
    """Action that expands a collapsible UI element."""

    def __init__(self, data: Dict):
        """Initialize an expand action.

        Args:
            data: Dictionary containing action data.
        """
        super().__init__(data)


class ScrollAction(_RevealAction):
    """Action that scrolls to reveal a UI element.

    Attributes:
        scroll_target_ui_path: The path to the UI element to scroll to.
    """

    def __init__(self, data: Dict):
        """Initialize a scroll action.

        Args:
            data: Dictionary containing action data with 'scroll_target_ui_path' key.
        """
        super().__init__(data)
        self._scroll_target_ui_path: str = data["scroll_target_ui_path"]

    @property
    def scroll_target_ui_path(self) -> str:
        """Get the path to the UI element to scroll to."""
        return self._scroll_target_ui_path


class GuideStep(ui.AbstractItem):
    """Base class for guide steps.

    Attributes:
        ui_type: The type of UI element this step targets.
        target_ui_path: The path to the target UI element.
        title: The step's title.
        description: The step's description.
        link: Optional link associated with the step.
    """

    def __init__(self, data: Dict):
        """Initialize a guide step from dictionary data.

        Args:
            data: Dictionary containing step data with required keys.
        """
        super().__init__()
        self._ui_type: str = data["ui_type"]
        self._target_ui_path: str = data["target_ui_path"]
        self._title: str = data["title"]
        self._title_model: ui.SimpleStringModel = ui.SimpleStringModel(self._title)
        self._description: str = data["description"]
        self._link: Optional[GuideLink] = None
        if "link" in data.keys():
            self._link = GuideLink(data["link"])

    def get_value_model(self, column_id: int) -> ui.SimpleStringModel:
        """Get the value model for a column in the step list.

        Args:
            column_id: The column index.

        Returns:
            The string model for the specified column.

        Raises:
            NotImplementedError: If the column is not supported.
        """
        if column_id == 0:
            return self._title_model
        raise NotImplementedError(f"GuideStep.get_value_model() does not support column {column_id}")

    @property
    def ui_type(self) -> str:
        """Get the type of UI element this step targets."""
        return self._ui_type

    @property
    def target_ui_path(self) -> str:
        """Get the path to the target UI element."""
        return self._target_ui_path

    @property
    def title(self) -> str:
        """Get the step's title."""
        return self._title

    @property
    def description(self) -> str:
        """Get the step's description."""
        return self._description

    @property
    def link(self) -> Optional[GuideLink]:
        """Get the optional link associated with the step."""
        return self._link


class WindowGuideStep(GuideStep):
    """Guide step that targets a window UI element."""

    def __init__(self, data: Dict):
        """Initialize a window guide step.

        Args:
            data: Dictionary containing step data.
        """
        super().__init__(data)


class WidgetGuideStep(GuideStep):
    """Guide step that targets a widget UI element.

    Attributes:
        parent_window_ui_path: The path to the parent window.
        reveal_actions: List of actions to reveal the widget.
    """

    def __init__(self, data: Dict):
        """Initialize a widget guide step.

        Args:
            data: Dictionary containing step data with 'parent_window_ui_path' and
                  optional 'reveal_actions' keys.
        """
        super().__init__(data)
        self._parent_window_ui_path: str = data["parent_window_ui_path"]
        self._reveal_actions: List[Union[ExpandAction, ScrollAction, ClickAction]] = []
        if "reveal_actions" in data.keys():
            for reveal_action in data["reveal_actions"]:
                action_type = ActionType(reveal_action["action_type"])
                if action_type == ActionType.EXPAND:
                    self._reveal_actions.append(ExpandAction(reveal_action))
                    continue
                if action_type == ActionType.SCROLL:
                    self._reveal_actions.append(ScrollAction(reveal_action))
                    continue
                if action_type == ActionType.CLICK:
                    self._reveal_actions.append(ClickAction(reveal_action))
                    continue
                raise NotImplementedError(f"Action type not implemented: {action_type.value}")

    @property
    def parent_window_ui_path(self) -> str:
        """Get the path to the parent window."""
        return self._parent_window_ui_path

    @property
    def reveal_actions(self) -> List[Union[ExpandAction, ScrollAction, ClickAction]]:
        """Get the list of actions to reveal the widget."""
        return self._reveal_actions


class MenuGuideStep(GuideStep):
    """Guide step that targets a menu UI element."""

    def __init__(self, data: Dict):
        """Initialize a menu guide step.

        Args:
            data: Dictionary containing step data.
        """
        super().__init__(data)
        self._menu_item_text: str = data["menu_item_text"]

    @property
    def menu_item_text(self) -> str:
        """Get the text of the menu item."""
        return self._menu_item_text


class GuideModel(ui.AbstractItemModel):
    """Model class for managing the guide's data and state.

    Attributes:
        current_step: The currently active step.
        current_step_index: The index of the current step.
        has_previous: Whether there is a previous step.
        has_next: Whether there is a next step.
        active: Whether the guide is currently active.
    """

    def __init__(self, json_path: str):
        """Initialize the guide model.

        Args:
            json_path: Path to the JSON file containing guide data.
        """
        super().__init__()
        self._title = ""
        self._description = ""
        self._steps: List[GuideStep] = []
        self._current_step_index: int = 0
        self._active: bool = False
        self._load_data(json_path)
        self._on_current_step_changed_functions: List[Callable[[Optional[GuideStep]], None]] = []
        self._on_active_changed_functions: List[Callable[[bool], None]] = []

    def _load_data(self, json_path: str):
        """Load guide data from a JSON file.

        Args:
            json_path: Path to the JSON file.

        Raises:
            FileNotFoundError: If the JSON file does not exist.
        """
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Guide data file not found: {json_path}")

        with open(json_path, "r") as f:
            data = json.load(f)

        self._steps = []

        for step_data in data["steps"]:
            if step_data["ui_type"] == "window":
                self._steps.append(WindowGuideStep(step_data))
                continue
            if step_data["ui_type"] == "widget":
                self._steps.append(WidgetGuideStep(step_data))
                continue
            if step_data["ui_type"] == "menu":
                self._steps.append(MenuGuideStep(step_data))
                continue

    def add_current_step_changed_function(self, subscriber: Callable[[Optional[GuideStep]], None]) -> None:
        """Add a callback for when the current step changes.

        Args:
            subscriber: Function to call when the current step changes.
        """
        self._on_current_step_changed_functions.append(subscriber)

    def remove_current_step_changed_function(self, subscriber: Callable[[Optional[GuideStep]], None]) -> None:
        """Remove a current step change callback.

        Args:
            subscriber: Function to remove from the callback list.
        """
        if subscriber in self._on_current_step_changed_functions:
            self._on_current_step_changed_functions.remove(subscriber)

    def add_active_changed_function(self, subscriber: Callable[[bool], None]) -> None:
        """Add a callback for when the active state changes.

        Args:
            subscriber: Function to call when the active state changes.
        """
        self._on_active_changed_functions.append(subscriber)

    def remove_active_changed_function(self, subscriber: Callable[[bool], None]) -> None:
        """Remove an active state change callback.

        Args:
            subscriber: Function to remove from the callback list.
        """
        if subscriber in self._on_active_changed_functions:
            self._on_active_changed_functions.remove(subscriber)

    def next(self):
        """Move to the next step in the guide."""
        if self.has_next:
            self._current_step_index += 1
            for subscriber in self._on_current_step_changed_functions:
                subscriber(self.current_step)

    def previous(self):
        """Move to the previous step in the guide."""
        if self.has_previous:
            self._current_step_index -= 1
            for subscriber in self._on_current_step_changed_functions:
                subscriber(self.current_step)

    def get_item_children(self, item=None) -> List[GuideStep]:
        """Get the list of guide steps.

        Args:
            item: Not used, present for interface compatibility.

        Returns:
            List of guide steps.
        """
        if item is not None:
            return []

        return self._steps

    def get_item_value_model_count(self, item=None):
        """Get the number of columns in the step list.

        Args:
            item: Not used, present for interface compatibility.

        Returns:
            Number of columns (1).
        """
        return 1

    def get_item_value_model(self, item=None, column_id=0):
        """Get the value model for a column in the step list.

        Args:
            item: The guide step to get the model for.
            column_id: The column index.

        Returns:
            The string model for the specified column.
        """
        if item is None:
            return None
        return item.get_value_model(column_id)

    @property
    def current_step(self) -> Optional[GuideStep]:
        """Get the currently active step."""
        if 0 <= self._current_step_index < len(self._steps):
            return self._steps[self._current_step_index]
        return None

    @current_step.setter
    def current_step(self, value: GuideStep):
        """Set the currently active step.

        Args:
            value: The step to make active.

        Raises:
            Exception: If the step is not managed by this model.
        """
        if value is None:
            return
        if value not in self._steps:
            raise Exception(f"Data not managed by model: {value}")
        self.current_step_index = self._steps.index(value)

    @property
    def current_step_index(self) -> int:
        """Get the index of the current step."""
        return self._current_step_index

    @current_step_index.setter
    def current_step_index(self, value: int):
        """Set the index of the current step.

        Args:
            value: The new step index.

        Raises:
            Exception: If the index is invalid.
        """
        if self._current_step_index == value:
            return
        if value < 0 or value >= len(self._steps):
            raise Exception("Invalid index")
        self._current_step_index = value
        for subscriber in self._on_current_step_changed_functions:
            subscriber(self.current_step)

    @property
    def has_previous(self) -> bool:
        """Check if there is a previous step."""
        return self._current_step_index > 0

    @property
    def has_next(self) -> bool:
        """Check if there is a next step."""
        return self._current_step_index < len(self._steps) - 1

    @property
    def active(self) -> bool:
        """Check if the guide is active."""
        return self._active

    @active.setter
    def active(self, value: bool):
        """Set whether the guide is active.

        Args:
            value: Whether the guide should be active.
        """
        if self._active == value:
            return
        self._active = value
        for subscriber in self._on_active_changed_functions:
            subscriber(self._active)
