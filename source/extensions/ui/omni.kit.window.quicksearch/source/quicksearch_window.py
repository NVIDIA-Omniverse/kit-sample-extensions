# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import asyncio
from asyncio.futures import Future
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import carb.input
import omni.kit.app
import omni.ui as ui
from carb.input import KEYBOARD_MODIFIER_FLAG_ALT as ALT
from carb.input import KEYBOARD_MODIFIER_FLAG_CONTROL as CTRL
from carb.input import KEYBOARD_MODIFIER_FLAG_SHIFT as SHIFT
from omni.kit.widget.searchfield import SearchField

from .quicksearch_delegate import QuickSearchDelegate
from .quicksearch_model import QuickSearchFlatModel, QuickSearchModel
from .quicksearch_registry import QuickSearchRegistry

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("icons")

SEARCH_SIZE = 40
WINDOW_WIDTH = 350
WINDOW_HEIGHT = 500


class QuickSearchWindow(ui.Window):
    class _DelayedFocus:
        """A helper to focus a field one frame later"""

        def __init__(self):
            self.__task: Optional[Future] = None
            self.__field: Optional[ui.AbstractField] = None

        def focus(self, field: ui.AbstractField):
            self.__field = field

            # Update in the next frame. We need it because we want to accumulate the affected prims
            if self.__task is None or self.__task.done():
                self.__task = asyncio.ensure_future(self.__delayed_do())

        async def __delayed_do(self):
            # Wait one frame
            await omni.kit.app.get_app().next_update_async()

            self.__task = None

            self.__field.focus_keyboard()
            self.__field = None

    @dataclass
    class _QuickSearchItem:
        name: str
        model_tree: ui.AbstractItemModel
        delegate_tree: ui.AbstractItemDelegate
        model_list: ui.AbstractItemModel
        delegate_list: ui.AbstractItemDelegate
        accept_fn: Optional[Callable[[], bool]]
        exclusive_fn: Optional[Callable[[], bool]]
        priority: int
        style: Optional[Dict[str, Any]]

    def __init__(self):
        super().__init__(
            "Quick Search",
            flags=ui.WINDOW_FLAGS_POPUP | ui.WINDOW_FLAGS_NO_TITLE_BAR,
            auto_resize=True,
            padding_x=0,
            padding_y=0,
        )

        style = {
            # search
            "TitleBar::Background": {
                "background_color": 0xFF23211F,
                "border_radius": 5,
                "corner_flag": ui.CornerFlag.TOP,
            },
            "ScrollingFrame": {"background_color": 0xFF23211F, "secondary_color": 0xFF222222},
            # TreeView
            "TreeView": {"background_color": 0xFF111111, "background_selected_color": 0x77E3B334},
            "TreeView:selected": {"background_color": 0x77E3B334},
            "TreeView.Item": {"margin": 0},
            "TreeView.Item.Icon": {"margin": 4, "border_radius": 2},
            "TreeView.Item.Icon::Collapse": {"color": 0xFFCCCCCC},
            "TreeView.Item.Description": {"color": 0xFF707071, "font_size": 14},
            "TreeView.Item.Title": {"color": 0xFFB4B4B4, "font_size": 14},
            "TreeView.Item::Type": {"color": 0xFF8A8777, "font_size": 14},
            "TreeView.Item:selected": {"color": 0xFFEEEEEE},
            "Rectangle::section_background": {"background_color": 0xFF343434},
        }

        self.frame.style = {"Window": {"border_radius": 6, "background_color": 0xFF23211F}}

        self.__focus = self._DelayedFocus()

        # keep track of the mouse position to ensure we are clicking on the same item during mouse press and release
        def __on_mouse_pressed(x, y, button, modifier):
            if button == 0:
                self.__mouse_pressed_x = x
                self.__mouse_pressed_y = y

        def __on_mouse_released(x, y, button, modifier):
            # make sure it's not a drag
            if button == 0 and abs(x - self.__mouse_pressed_x) < 4 and abs(y - self.__mouse_pressed_y) < 4:
                # delay execution after selection being changed
                async def _execute_after_selection_changed():
                    if self.__selected_item:
                        self._execute()

                asyncio.ensure_future(_execute_after_selection_changed())

        # The window layout
        with self.frame:
            with ui.VStack(width=WINDOW_WIDTH, height=0, style=style):
                # Title Bar
                with ui.ZStack(height=25):
                    ui.Rectangle(name="Background", style_type_name_override="TitleBar")

                    with ui.HStack(height=30):
                        ui.Spacer(width=30)
                        ui.Label("Quick Search", alignment=ui.Alignment.CENTER, style={"font_size": 18})
                        ui.Spacer(width=30)

                ui.Image(f"{ICON_PATH}/shadow.png", height=15, width=WINDOW_WIDTH)

                # Area with the search filed
                self.__search_field = SearchField(
                    show_tokens=False, on_search_fn=self.__on_search, subscribe_edit_changed=True
                )

                with ui.ScrollingFrame(
                    height=WINDOW_HEIGHT,
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                ):
                    with ui.ZStack(mouse_pressed_fn=__on_mouse_pressed, mouse_released_fn=__on_mouse_released):
                        self.__search_tree_frame = ui.Frame(height=0, visible=True)
                        self.__search_tree_list = ui.Frame(height=0, visible=False)

        self.set_key_pressed_fn(self.__on_key_pressed)

        # All the models
        self.__models_delegates: List[
            Tuple[
                str,
                QuickSearchModel,
                ui.AbstractItemDelegate,
                QuickSearchModel,
                ui.AbstractItemDelegate,
                Optional[Callable[[], bool]],
                Optional[int],
            ],
        ] = []
        self.__init_models()
        self.__quick_search_changed_sub = QuickSearchRegistry().subscribe_quick_search_changed(self.__init_models)

        self.__selected_item = None
        self.__selected_model = None
        self.__focus_keyboard()

    def destroy(self):
        self.__selected_item = None
        self.__selected_model = None

        self.__quick_search_changed_sub = None
        self.__focus = None

        if self.__search_field:
            self.__search_field.destroy()
        self.__search_field = None

        self.__search_tree_frame = None
        self.__search_tree_list = None

        self.__search_trees = []
        self.__search_lists = []

        super().destroy()

    def hide(self):
        """Hide the window"""
        self.visible = False

    def show(self):
        """Show the window"""
        self.__init_search_tree()
        self.__init_search_list()
        accepted_items = self.__accepted_quicksearch_items
        self.visible = len(accepted_items) != 1 or accepted_items[0].name != "Calculator"
        for tree in self.__search_trees + self.__search_lists:
            tree.selection = []
        # clear previous search
        self.__search_field.clear()
        self.__focus_keyboard()
        # clear the selection
        self.__selected_item = None

    def search_text(self, text: str):
        self.__search_field._search_field.model.set_value(text)
        self.__on_search(text)

    def _complete(self):
        if self.__selected_item and self.__selected_model:
            current_value = self.__search_field._search_field.model.as_string
            updated_field_value = self.__selected_model.complete(current_value, self.__selected_item)
            self.__search_field._search_field.model.set_value(f"{updated_field_value}")

    def _execute(self):
        """The user wants to execute the currently selected item"""
        if self.__selected_item and self.__selected_model:
            self.__selected_model.execute(self.__selected_item)
        self.hide()

    def __init_models(self):
        """Called when the modes are changed"""
        self.__models_delegates: List[QuickSearchWindow._QuickSearchItem] = []
        for name in QuickSearchRegistry().get_names():
            # Data from the registry
            handler = QuickSearchRegistry().get_quick_search(name)
            if not handler:
                continue

            if not handler.delegate_type:
                # Delegates
                delegate_tree = QuickSearchDelegate()
                delegate_list = QuickSearchDelegate(flat=True)
            else:
                delegate_tree = QuickSearchDelegate(item_delegate=handler.delegate_type())
                delegate_list = QuickSearchDelegate(item_delegate=handler.delegate_type(flat=True), flat=True)

            # Models
            model_tree = QuickSearchModel(name, handler.model_type())
            model_list = QuickSearchFlatModel(name, handler.model_type(), flat=handler.flat_search)

            # Keep them
            self.__models_delegates.append(
                self._QuickSearchItem(
                    name,
                    model_tree,
                    delegate_tree,
                    model_list,
                    delegate_list,
                    handler.accept_fn,
                    handler.exclusive_fn,
                    handler.priority,
                    handler.style,
                )
            )

        # Sort by priority and name
        self.__models_delegates = list(sorted(self.__models_delegates, key=lambda a: f"{a.priority}z{a.name}"))

        # Recreate trees
        self.__init_search_tree()
        self.__init_search_list()
        accepted_items = self.__accepted_quicksearch_items
        if len(accepted_items) == 1 and accepted_items[0].name == "Calculator":
            self.hide()

    def _clear_search(self, x, y, b, m):
        self.__search_field._search_field.model.as_string = ""

    @property
    def __accepted_quicksearch_items(self):
        accepted_items = [item for item in self.__models_delegates if not item.accept_fn or item.accept_fn()]

        # Check if we have exclusive items
        exclusive_items = [item for item in accepted_items if item.exclusive_fn and item.exclusive_fn()]
        if exclusive_items:
            accepted_items = exclusive_items

        return accepted_items

    def __init_search_tree(self):
        """Create TreeView per model for the mode when the search field is empty"""
        items = self.__accepted_quicksearch_items
        show_roots = len(items) > 1

        self.__search_trees = []
        with self.__search_tree_frame:
            with ui.VStack():
                for item in items:
                    tree = ui.TreeView(
                        item.model_tree,
                        delegate=item.delegate_tree,
                        selection_changed_fn=partial(self.__selection_changed, item.model_tree),
                        root_expanded=not show_roots,
                        root_visible=show_roots,
                        style=item.style,
                        mouse_pressed_fn=lambda *_, model=item.model_tree: self.__on_mouse_pressed(model),
                        identifier=item.name,
                    )
                    self.__search_trees.append(tree)

    def __on_mouse_pressed(self, model):
        if isinstance(model, QuickSearchModel):
            for tree in self.__search_trees:
                if tree.model == model:
                    tree.root_expanded = not tree.root_visible or not tree.root_expanded
                    return

    def __init_search_list(self):
        """Create TreeView per model for the mode when the search field has the text"""
        items = self.__accepted_quicksearch_items
        show_roots = len(items) > 1

        self.__search_lists = []
        with self.__search_tree_list:
            with ui.VStack():
                for item in items:
                    tree = ui.TreeView(
                        item.model_list,
                        delegate=item.delegate_list,
                        selection_changed_fn=partial(self.__selection_changed, item.model_list),
                        root_visible=show_roots,
                        keep_expanded=True,
                        style=item.style,
                        identifier=item.name,
                    )
                    self.__search_lists.append(tree)

    def __on_key_pressed(self, key, mod, pressed):
        """Called when the user presses a key"""
        if not pressed:
            return

        if mod & carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL or mod & carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT:
            return

        if key == int(carb.input.KeyboardInput.ESCAPE):
            self.hide()
        elif not (mod & (SHIFT | CTRL | ALT)):
            if key == int(carb.input.KeyboardInput.ENTER):
                self._execute()
            elif key == int(carb.input.KeyboardInput.TAB):
                self._complete()
            elif key == int(carb.input.KeyboardInput.DOWN):
                self.__select_next(after=True)
            elif key == int(carb.input.KeyboardInput.UP):
                self.__select_next(after=False)

    def __on_search(self, text: Union[list, str]):
        """Called when the user changes the search field"""
        flat_list_visible = not not text
        self.__search_tree_frame.visible = not flat_list_visible
        self.__search_tree_list.visible = flat_list_visible

        if text:
            # SearchField process the input text as a list
            if isinstance(text, list):
                text = " ".join(text)
            for tree in self.__search_lists:
                tree.model.filter_by_text(text)

        self.__selected_model = None
        self.__selected_item = None
        self.__select_next()

    def __focus_keyboard(self):
        """Focus the search field"""
        # Delayed focus because when the window is not created yet, we can't focus.
        self.__focus.focus(self.__search_field._search_field)

    def __select_first_or_last(self, model=None, first=True):
        """Select the first or last available item"""
        if first:
            direction = 1
            next_index = 0
        else:
            direction = -1
            next_index = -1

        all_models = [tree.model for tree in self.__search_lists]
        if model:
            try:
                index = all_models.index(model)
            except ValueError:
                index = None

            if index is not None:
                all_models = all_models[index + direction :: direction] + all_models[: index + direction : direction]

        selected_model = next((model for model in all_models if model.get_item_children_flatten(None)), None)
        if selected_model:
            selected_item = selected_model.get_item_children_flatten(None)[next_index]
        else:
            selected_item = None

        self.__selection_changed(selected_model, selected_item)

    def __select_next(self, after=True):
        """Select the item that is located before or after the currently selected one"""
        if self.__selected_model is None or self.__selected_item is None:
            self.__select_first_or_last(first=after)
        else:
            items = self.__selected_model.get_item_children_flatten(None)
            try:
                index = items.index(self.__selected_item)
            except ValueError:
                # There is no item in the model
                self.__select_first_or_last(first=after)
                index = None

            if index is not None:
                if after and index < len(items) - 1:
                    self.__selected_item = items[index + 1]
                elif not after and index > 0:
                    self.__selected_item = items[index - 1]
                else:
                    self.__select_first_or_last(self.__selected_model, first=after)

        for tree in self.__search_lists:
            if tree.model == self.__selected_model:
                tree.selection = [self.__selected_item]
            else:
                tree.selection = []

    def __selection_changed(self, model, item):
        """Called when the user changed the selection with keyboard or with mouse"""
        if isinstance(item, list) and item:
            item = item[0]

        if isinstance(model, QuickSearchModel) and not item:
            for tree in self.__search_trees:
                if len(tree.selection) > 0:
                    tree.selection = []
            return

        if model and item:
            self.__selected_model = model
            self.__selected_item = item
