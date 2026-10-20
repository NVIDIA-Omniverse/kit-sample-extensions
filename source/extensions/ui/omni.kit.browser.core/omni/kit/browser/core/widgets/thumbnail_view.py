# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import time
from collections import deque
from typing import Dict, List, Optional

import carb
import carb.settings
import omni.kit.app
from carb.input import KEYBOARD_MODIFIER_FLAG_CONTROL, KEYBOARD_MODIFIER_FLAG_SHIFT
from omni import ui

from ..models import AbstractBrowserModel, DetailItem
from .detail_delegate import DetailDelegate

SETTING_BUILD_BUDGET_MS = "/exts/omni.kit.browser.core/thumbnail_view/build_budget_ms"
# How long tile building may hold the main thread before handing a frame back. Small enough that a
# frame still lands, large enough that a batch is not spread over needless frames.
DEFAULT_BUILD_BUDGET_MS = 8.0


class ThumbnailView(ui.VGrid):
    """
    GridView to show thumbnails of details or categories.

    Keyword Args:
        delegate (DetailDelegate): delegate object to represent detail item
        thumbnail_size (int): width of thumbnail, in pixel. Default 128.
        thumbnail_aspect (float): Aspect ratio of thumbnail. Default 1.0 (width / height).
        extra_filter_fn (callable): Extra filter function called to filter items. Return True to show item otherwise hide.
            Default None. Function signure: bool extra_filter_fn(item: DetailItem)
        thumbnail_padding_width (int): padding width between thumbnails, default 1
        thumbnail_padding_height (int): padding height between thumbnails, default 1
        multiple_drag (bool): True to allow drag multiple items. Default False.

    Properties:
        selection (List[DetailItem]): selected detail items. Readonly.
        thumbnail_size (int): size of thumbnail, in pixel. Read and write.
    """

    def __init__(
        self,
        model,
        delegate: DetailDelegate = None,
        thumbnail_size: int = 128,
        thumbnail_aspect: float = 1,
        extra_filter_fn: callable = None,
        thumbnail_padding_width: int = 1,
        thumbnail_padding_height: int = 1,
        multiple_drag: bool = False,
    ):
        super().__init__(content_clipping=True)

        self._model_sub_ids: Dict[AbstractBrowserModel, callable] = {}
        self.model = model
        self._delegate = delegate or DetailDelegate(self._model)
        self._selections = []
        self._delegates = {}
        # What the grid is currently showing, so a rebuild can tell whether it has anything to do.
        self._built_items = []
        # Tiles asked for but not yet created, drained a few milliseconds at a time - see
        # __build_pending_async.
        self._pending: deque = deque()
        self._build_task: Optional[asyncio.Future] = None
        self._thumbnail_aspect = thumbnail_aspect
        self._thumbnail_padding_width = thumbnail_padding_width
        self._thumbnail_padding_height = thumbnail_padding_height
        self.thumbnail_size = thumbnail_size
        self._extra_filter_fn = extra_filter_fn
        self._multiple_drag = multiple_drag

        self._filter_words: Optional[str] = None
        self._on_selection_changed_fn = None
        self.__in_dragging = False

        if multiple_drag:
            # Multiple drag: keep selections when mouse pressed
            self.set_mouse_released_fn(lambda x, y, btn, flag: self._on_mouse_pressed(btn, flag, None))
            # Handle drag items in view for multiple items instead of delegate for single item
            self._delegate.set_drag_fn(self.on_drag)
        else:
            self.set_mouse_pressed_fn(lambda x, y, btn, flag: self._on_mouse_pressed(btn, flag, None))

        self._padding_left: Dict[DetailItem, ui.Spacer] = {}
        self._padding_right: Dict[DetailItem, ui.Spacer] = {}
        self._padding_top: Dict[DetailItem, ui.Spacer] = {}
        self._padding_bottom: Dict[DetailItem, ui.Spacer] = {}
        self._build_ui()

    def destroy(self):
        self._on_selection_changed_fn = None
        # Clear children widgets, otherwise it will crash when exiting if ui.ImageWithProvider loads remote image
        self.clear()
        self._built_items = []
        self._delegate.destroy()

    @property
    def model(self) -> AbstractBrowserModel:
        return self._model

    @model.setter
    def model(self, new_model: AbstractBrowserModel) -> None:
        # getattr, because __init__ assigns through this setter before _model exists - and a first
        # assignment has nothing on screen to reset.
        previous = getattr(self, "_model", None)
        self._model = new_model
        if previous is not None and new_model is not previous:
            # Everything on screen belongs to the old model. Clearing _built_items alone is not
            # enough: _build_ui reads an empty list as "nothing built yet", which is also what a
            # grown-at-the-end append looks like, so the old tiles would stay and the new ones
            # would be added under them.
            self.__cancel_build()
            self.clear()
            self._delegates = {}
            self._built_items = []
        if new_model not in self._model_sub_ids:
            self._model_sub_ids[new_model] = self._model.add_item_changed_fn(self._model_item_changed)

    @property
    def selection(self) -> List[DetailItem]:
        return self._selections

    @selection.setter
    def selection(self, items: List[DetailItem]) -> None:
        self._clear_selections()
        for item in items:
            self._add_selection(item)
        if self._on_selection_changed_fn is not None:
            self._on_selection_changed_fn(self._selections)

    @property
    def thumbnail_size(self) -> int:
        """Thumbnail size of detail item"""
        return self.column_width - 2 * self._thumbnail_padding_width

    @thumbnail_size.setter
    def thumbnail_size(self, value: int) -> None:
        """Thumbnail size of detail item"""
        self.column_width = value + 2 * self._thumbnail_padding_width

        # Update grid row height
        self.row_height = (
            value / self._thumbnail_aspect + 2 * self._thumbnail_padding_height + self._delegate.get_label_height()
        )
        self._delegate.thumbnail_size = value

    @property
    def thumbnail_padding_width(self) -> int:
        """Padding width between deaiil items"""
        return self._thumbnail_padding_width

    @thumbnail_padding_width.setter
    def thumbnail_padding_width(self, value: int) -> None:
        self._thumbnail_padding_width = value
        self.column_width = self.thumbnail_size + 2 * value
        for item in self._padding_left:
            self._padding_left[item].width = ui.Pixel(value)
            self._padding_right[item].width = ui.Pixel(value)

    @property
    def thumbnail_padding_height(self) -> int:
        """Padding width between deaiil items"""
        return self._thumbnail_padding_width

    @thumbnail_padding_height.setter
    def thumbnail_padding_height(self, value: int) -> None:
        self._thumbnail_padding_height = value
        self.row_height = (
            self.thumbnail_size / self._thumbnail_aspect
            + 2 * self._thumbnail_padding_height
            + self._delegate.get_label_height()
        )
        for item in self._padding_top:
            self._padding_top[item].height = ui.Pixel(value)
            self._padding_bottom[item].height = ui.Pixel(value)

    def filter(self, filter_words: Optional[List[str]]) -> None:
        """
        Filter detail items.
        Args:
            filter_words: A string list to filter detail items. None means filtering nothing.
        """
        self._filter_words = filter_words
        # Update item visibility, donot need to rebuild items.
        self.refresh()

    def set_selection_changed_fn(self, on_selection_changed_fn) -> None:
        """
        Set function called when selection changed.
        Args:
            on_selection_changed_fn (callable): Function called when selection changed. Function signure:
                void on_selection_changed_fn(selection: List[DetailItem])
        """
        self._on_selection_changed_fn = on_selection_changed_fn

    def set_extra_filter_fn(self, extra_filter_fn: Optional[callable]) -> None:
        self._extra_filter_fn = extra_filter_fn
        self.refresh()

    def refresh(self):
        """
        Refresh details items for visibility.
        """
        selection_changed = False
        for item in self._delegates:
            self._delegates[item].visible = self._is_item_visible(item)

            # Since item invisible, clear selection state
            if not self._delegates[item].visible:
                if self._remove_selection(item):
                    selection_changed = True

        if selection_changed and self._on_selection_changed_fn is not None:
            self._on_selection_changed_fn(self._selections)

    def clear(self) -> None:
        """Clear all items and selections"""
        # Tiles queued for the contents being thrown away must not be built onto the new ones.
        self.__cancel_build()
        super().clear()
        # And nothing is built any more. Every caller inside this class resets this on the next
        # line, but clear() is public: leaving it stale means the next notification carrying the
        # same children is read as "already shown" and returns, leaving the view empty.
        self._built_items = []
        self._clear_selections()
        self._delegates.clear()
        self._padding_left.clear()

        if self._on_selection_changed_fn is not None:
            self._on_selection_changed_fn(self._selections)

    def on_drag(self, item: DetailItem) -> str:
        self.__in_dragging = True

        if item not in self._selections:
            return self._delegate.on_drag(item)

        # Combine item drag mime data into one
        drag_mime_datas: List[str] = []
        with ui.VStack():
            multiple = len(self._selections) > 1
            for item in self._selections:
                drag_mime_datas.append(
                    self._delegate.on_multiple_drag(item) if multiple else self._delegate.on_drag(item)
                )
        return "\n".join(drag_mime_datas)

    def _build_ui(self) -> None:
        """
        Bring the grid in line with the model, doing as little as possible.

        Rebuilding wholesale on every notification is what made a browser unusable while a
        collection scanned: the model reports a change per folder discovered, and each one cleared
        every tile and built them all again. Two cases carry almost all the traffic and neither
        needs that - the children are unchanged, or a few have been appended.
        """
        children = self._model.get_item_children()
        children = [] if children is None else list(children)

        if children == self._built_items:
            # Nothing to show that is not already shown. During a scan this is the common case by
            # far, including the whole of a scan that has not yet found anything.
            return

        added = None
        if len(children) > len(self._built_items) and children[: len(self._built_items)] == self._built_items:
            # Grown at the end, which is what a scan does: keep the tiles already built.
            added = children[len(self._built_items) :]
        else:
            self.clear()
            self._delegates = {}
            added = children

        if added:
            self._pending.extend(added)
            self.__ensure_build_task()
        self._built_items = children

    def __ensure_build_task(self) -> None:
        if self._build_task is None or self._build_task.done():
            self._build_task = asyncio.ensure_future(self.__build_pending_async())

    def __cancel_build(self) -> None:
        if self._build_task is not None and not self._build_task.done():
            self._build_task.cancel()
        self._build_task = None
        self._pending.clear()

    async def __build_pending_async(self) -> None:
        """
        Create the queued tiles a few milliseconds at a time.

        Building them in one go is what froze the browser: a scan reports a change per folder it
        finds, so thousands of items can arrive between notifications, and creating a ui.Frame for
        each held the main thread with the GIL for as long as it took. A scan of a drive was caught
        here for **100 seconds**, with all seven other Python threads blocked behind it.

        Yielding on a frame rather than to the loop is what makes the difference: a coroutine
        waiting on a frame is not ready, so Kit's pump can return and the app draws. Anything else
        just keeps the pump busy - the app stays frozen while looking like it yielded.
        """
        try:
            while self._pending:
                budget = self.__build_budget_ms()
                began = time.perf_counter()
                with self:
                    while self._pending and (time.perf_counter() - began) * 1000.0 < budget:
                        item = self._pending.popleft()
                        self._delegates[item] = ui.Frame(build_fn=lambda i=item: self._build_detail_frame(i))
                await omni.kit.app.get_app().next_update_async()
        except asyncio.CancelledError:
            raise
        finally:
            # Only if this is still the current builder. A cancelled one runs its finally when it
            # is next scheduled, which can be after a replacement has started, and clearing the
            # handle then loses the live task: nothing could cancel it and a second builder could
            # start beside it.
            if self._build_task is asyncio.current_task():
                self._build_task = None

    def __build_budget_ms(self) -> float:
        value = carb.settings.get_settings().get(SETTING_BUILD_BUDGET_MS)
        return float(value) if isinstance(value, (int, float)) and value > 0 else DEFAULT_BUILD_BUDGET_MS

    def _build_detail_frame(self, item: DetailItem) -> None:
        with self._delegates[item]:
            with ui.HStack(content_clipping=True):
                self._padding_left[item] = ui.Spacer(width=self._thumbnail_padding_width)
                with ui.VStack(content_clipping=True):
                    self._padding_top[item] = ui.Spacer(height=self._thumbnail_padding_height)
                    self._build_detail_item(item)
                    self._padding_bottom[item] = ui.Spacer(height=self._thumbnail_padding_height)
                self._padding_right[item] = ui.Spacer(width=self._thumbnail_padding_width)

        # To avoid re-creating items, always create first and change visibilty by filter words.
        self._delegates[item].visible = self._is_item_visible(item)
        if item in self._selections:
            # Selected while its tile was still queued - the frame did not exist to carry the state.
            self._delegates[item].selected = True

    def _build_detail_item(self, item: DetailItem) -> None:
        stack = ui.ZStack()
        with stack:
            self._delegate.build_widget(self._model, item)
        if self._multiple_drag:
            stack.set_mouse_released_fn(lambda x, y, btn, flag, item=item: self._on_mouse_pressed(btn, flag, item))
        else:
            stack.set_mouse_pressed_fn(lambda x, y, btn, flag, item=item: self._on_mouse_pressed(btn, flag, item))

    def _on_mouse_pressed(self, btn: int, flag: int, item: DetailItem) -> None:
        if btn == 0:
            self._on_click(flag, item)
        elif btn == 1:
            self._on_right_click(item)

    def _on_click(self, flag: int, item: DetailItem) -> None:
        if self.__in_dragging:
            if item:
                self.__in_dragging = False
            return

        if flag & KEYBOARD_MODIFIER_FLAG_CONTROL:
            if item in self._selections:
                self._remove_selection(item)
            else:
                self._add_selection(item)
        elif flag & KEYBOARD_MODIFIER_FLAG_SHIFT:
            if not self._selections:
                self._add_selection(item)
            elif item:
                last_selection = self._selections[-1]
                current_selection = item
                children = self._model.get_item_children(None)
                last_selection_index = children.index(last_selection)
                current_selection_index = children.index(current_selection)

                first_index = min(last_selection_index, current_selection_index)
                last_index = max(last_selection_index, current_selection_index)
                self._clear_selections()
                for i in reversed(range(first_index, last_index + 1)):
                    child = children[i]
                    frame = self._delegates.get(child)
                    # A tile still queued has no frame to ask. Its filter state is known anyway -
                    # it is what _build_detail_frame will apply - and indexing here instead raised
                    # KeyError, taking the whole selection with it.
                    visible = frame.visible if frame is not None else self._is_item_visible(child)
                    if visible:
                        self._add_selection(child)
        else:
            self._clear_selections()
            self._add_selection(item)

        if self._on_selection_changed_fn is not None:
            self._on_selection_changed_fn(self._selections)

    def _on_right_click(self, item: DetailItem) -> None:
        if self._multiple_drag:
            # Do not change selection for right click in multiple drag mode
            return

        if item not in self._selections:
            self._clear_selections()
            self._add_selection(item)

            if self._on_selection_changed_fn is not None:
                self._on_selection_changed_fn(self._selections)

    def _clear_selections(self) -> None:
        for item in self._selections:
            frame = self._delegates.get(item)
            if frame is not None:
                frame.selected = False
        self._selections.clear()

    def _add_selection(self, item: DetailItem) -> None:
        if item is not None:
            self._selections.append(item)
            frame = self._delegates.get(item)
            if frame is not None:
                # A tile still queued has no frame yet; _build_detail_frame picks the state up.
                frame.selected = True

    def _remove_selection(self, item: DetailItem) -> bool:
        if item in self._selections:
            self._selections.remove(item)
            frame = self._delegates.get(item)
            if frame is not None:
                frame.selected = False
            return True
        else:
            return False

    def _model_item_changed(self, model: ui.AbstractItemModel, item: DetailItem) -> None:
        self._build_ui()

    def _is_item_visible(self, item: DetailItem) -> bool:
        visible = item.filter(self._filter_words)
        if self._extra_filter_fn is not None:
            visible = visible and self._extra_filter_fn(item)

        return visible
