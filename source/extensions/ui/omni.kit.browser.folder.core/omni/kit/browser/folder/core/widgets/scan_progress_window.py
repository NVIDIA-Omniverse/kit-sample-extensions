# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["ScanProgressWindow"]

import time
from typing import List, Optional

import omni.ui as ui

from ..models.traverse_context import TraverseState

WINDOW_TITLE = "Scan Progress"
WINDOW_WIDTH = 560
# Sized for roughly four rows plus the header. Fixed: the tree scrolls, so the window never grows
# with the number of queued collections.
WINDOW_HEIGHT = 168
ROW_HEIGHT = 22
COLUMN_WIDTHS = [ui.Fraction(2), ui.Pixel(96), ui.Pixel(110), ui.Pixel(134), ui.Pixel(28)]
# The last column is the per-row cancel button and has no heading: a one-word title over a single
# glyph reads as a data column.
COLUMN_TITLES = ["Name", "Found files", "Resolved files", "Resolved materials", ""]
CANCEL_COLUMN = 4
# An image, not a text glyph: a multiplication sign renders as a question mark in fonts that lack
# it. Copied in rather than referenced from the extensions shipping the same file, since reaching
# into another extension's data is a dependency this one does not declare.
CANCEL_ICON = "${omni.kit.browser.folder.core}/data/icons/Cancel_64.png"
CANCEL_ICON_SIZE = 14
REFRESH_INTERVAL = 0.2

# Left in a column that has no number yet. Blank on purpose: a placeholder glyph reads as a value
# the scan produced, and a row that has not started should look empty rather than answered.
NO_VALUE = ""

STATUS_TEXT = {
    TraverseState.QUEUED: "Pending",
    TraverseState.CONNECTING: "Connecting…",
}


class _ScanItem(ui.AbstractItem):
    """One collection in the tree. Owns the value models and the labels showing them."""

    def __init__(self, folder):
        super().__init__()
        self.folder = folder
        self.name_model = ui.SimpleStringModel(getattr(folder, "name", folder.url))
        self.found_model = ui.SimpleStringModel("")
        self.resolved_model = ui.SimpleStringModel("")
        self.materials_model = ui.SimpleStringModel("")
        self._value_models = (
            self.name_model,
            self.found_model,
            self.resolved_model,
            self.materials_model,
            None,  # the cancel column renders a button, not a value
        )
        self._cancel_button = None
        # Labels, handed back by the delegate as it builds each cell. ui.Label takes a plain string
        # and is not bound to a value model, so setting the models alone repaints nothing - the row
        # would keep whatever numbers it was first drawn with.
        self._labels = {}
        self.refresh()

    def value_model(self, column_id: int) -> ui.SimpleStringModel:
        return self._value_models[column_id]

    def bind_label(self, column_id: int, label: ui.Label) -> None:
        """Adopt the label the delegate just built for this cell."""
        self._labels[column_id] = label

    def bind_cancel_button(self, button) -> None:
        """Adopt the cancel button, so its visibility can follow the row's state."""
        self._cancel_button = button
        self._refresh_cancel_button()

    @property
    def can_cancel(self) -> bool:
        """A finished, failed or already-cancelled collection has nothing left to stop."""
        ctx = getattr(self.folder, "traverse_ctx", None)
        return ctx is not None and not ctx.is_terminal

    def _refresh_cancel_button(self) -> None:
        if self._cancel_button is None:
            return
        try:
            self._cancel_button.visible = self.can_cancel
        except Exception:  # noqa: BLE001 - the row was rebuilt and this widget is gone
            self._cancel_button = None

    def refresh(self) -> None:
        """Pull the current numbers off the folder and push them into the visible cells."""
        for column_id, text in enumerate(self._current_text(), start=1):
            self._set_cell(column_id, text)
        self._refresh_cancel_button()

    def _current_text(self):
        """
        What the three data columns should read right now.

        The last column doubles as the status: a collection that is queued, connecting or failed
        has no material count to show, and a word there is clearer than a zero. The file counts to
        its left are left alone, so a failed row still says how far it got before it gave up.
        """
        ctx = getattr(self.folder, "traverse_ctx", None)
        if ctx is None:
            return NO_VALUE, NO_VALUE, "Pending"
        if ctx.state in STATUS_TEXT:
            # Not counting yet, so say what it is doing instead of showing a misleading zero.
            return NO_VALUE, NO_VALUE, STATUS_TEXT[ctx.state]
        if ctx.state is TraverseState.FAILED:
            # The failure is the headline - a bare number would read as success - but the files it
            # got through stay visible.
            return f"{ctx.files_found:,}", f"{ctx.files_resolved:,}", "Failed"
        if ctx.state is TraverseState.CANCELLED:
            # Same shape as a failure, different word: the counts say how far it got before the
            # user stopped it, and "Cancelled" says it was not the scan's own doing.
            return f"{ctx.files_found:,}", f"{ctx.files_resolved:,}", "Cancelled"
        # Scanning, or finished. A finished row keeps its final numbers.
        return f"{ctx.files_found:,}", f"{ctx.files_resolved:,}", f"{ctx.items_resolved:,}"

    def _set_cell(self, column_id: int, text: str) -> None:
        model = self._value_models[column_id]
        if model is None:
            return
        if model.as_string == text:
            # Nothing moved since the last tick. Most refreshes land here, which is what keeps a
            # scan resolving thousands of files from touching the UI thousands of times.
            return
        model.set_value(text)
        label = self._labels.get(column_id)
        if label is None:
            return
        try:
            label.text = text
        except Exception:  # noqa: BLE001 - the row was rebuilt and this widget is gone
            # Dropping the reference is enough: the delegate re-binds on the next build, and the
            # value model already carries the new text for it to start from.
            self._labels.pop(column_id, None)


class _ScanModel(ui.AbstractItemModel):
    """Flat tree over the model's active folders - one row per collection, no children."""

    def __init__(self):
        super().__init__()
        self._items: List[_ScanItem] = []

    @property
    def items(self) -> List[_ScanItem]:
        return self._items

    def add_folders(self, folders) -> bool:
        """
        Append any folder not already listed, keeping the order it was first seen.

        Rows are never removed. A collection that finishes leaves ``active_folders`` immediately -
        that list is what is still in flight - but the row stays so the user can see what a scan
        actually produced. Clearing the list is :meth:`reset`, which the window does when it is
        opened afresh.
        """
        known = {id(item.folder) for item in self._items}
        added = [folder for folder in folders if id(folder) not in known]
        if not added:
            return False
        self._items.extend(_ScanItem(folder) for folder in added)
        self._item_changed(None)
        return True

    def reset(self) -> None:
        self._items = []
        self._item_changed(None)

    def refresh_values(self) -> None:
        for item in self._items:
            item.refresh()

    def get_item_children(self, item):
        return [] if item is not None else self._items

    def get_item_value_model_count(self, item) -> int:
        return len(COLUMN_TITLES)

    def get_item_value_model(self, item, column_id: int):
        if item is None:
            return None
        return item.value_model(column_id)


class _ScanDelegate(ui.AbstractItemDelegate):
    """Plain labels; the numeric columns are right aligned so digits line up between rows."""

    def __init__(self, cancel_fn=None):
        super().__init__()
        self._cancel_fn = cancel_fn

    def build_header(self, column_id: int = 0) -> None:
        with ui.HStack(height=ROW_HEIGHT):
            ui.Label(
                COLUMN_TITLES[column_id],
                # Elided with the full title on hover: the headings are longer than the numbers
                # under them, and a narrowed window must not silently crop one into another.
                elided_text=True,
                tooltip=COLUMN_TITLES[column_id],
                alignment=ui.Alignment.LEFT_CENTER if column_id == 0 else ui.Alignment.RIGHT_CENTER,
            )
            if column_id:
                ui.Spacer(width=6)

    def build_branch(self, model, item, column_id: int = 0, level: int = 0, expanded: bool = False) -> None:
        # Flat list: no expand arrows, but the column still needs to occupy its space.
        ui.Spacer(width=0)

    def build_widget(self, model, item, column_id: int = 0, level: int = 0, expanded: bool = False) -> None:
        if column_id == CANCEL_COLUMN:
            self._build_cancel(item)
            return
        value_model = model.get_item_value_model(item, column_id)
        with ui.HStack(height=ROW_HEIGHT):
            label = ui.Label(
                value_model.as_string,
                elided_text=True,
                alignment=ui.Alignment.LEFT_CENTER if column_id == 0 else ui.Alignment.RIGHT_CENTER,
                tooltip=item.folder.url if column_id == 0 else "",
            )
            # Hand it to the item so progress ticks can retarget it. Rebuilds land here again and
            # replace the reference, so a rebuilt row is never left pointing at a dead widget.
            item.bind_label(column_id, label)
            if column_id:
                ui.Spacer(width=6)

    def _build_cancel(self, item) -> None:
        """
        The row's stop button.

        Clicking it cancels and nothing more. The row is not removed here and the button does not
        disable itself optimistically: the state comes back from the model, so a cancel that loses
        the race to a scan finishing on its own simply shows that scan finishing.
        """
        with ui.HStack(height=ROW_HEIGHT):
            ui.Spacer()
            button = ui.Button(
                image_url=CANCEL_ICON,
                image_width=CANCEL_ICON_SIZE,
                image_height=CANCEL_ICON_SIZE,
                width=20,
                height=18,
                tooltip="Stop scanning this collection",
                clicked_fn=lambda i=item: self._on_clicked(i),
            )
            ui.Spacer(width=4)
            item.bind_cancel_button(button)

    def _on_clicked(self, item) -> None:
        if self._cancel_fn is not None:
            self._cancel_fn(item)


class ScanProgressWindow:
    """
    A small floating window listing every collection seen scanning since it was opened.

    Rows are added from the model's ``active_folders`` and then kept, showing what each collection
    finished with: a row that vanished the moment its folder left that list would take the result
    with it. The window stays open when the list drains, for the same reason, and is closed by the
    user.

    Args:
        model: The ``FolderBrowserModel`` whose active folders to display.
    """

    def __init__(self, model):
        self._model = model
        self._tree_model = _ScanModel()
        self._delegate = _ScanDelegate(cancel_fn=self._cancel_row)
        self._tree: Optional[ui.TreeView] = None
        self._last_refresh = 0.0

        self._window = ui.Window(
            WINDOW_TITLE,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            visible=False,
            dockPreference=ui.DockPreference.DISABLED,
            flags=(
                ui.WINDOW_FLAGS_NO_DOCKING
                | ui.WINDOW_FLAGS_NO_COLLAPSE
                | ui.WINDOW_FLAGS_NO_SCROLLBAR
                | ui.WINDOW_FLAGS_NO_RESIZE
            ),
        )
        self._window.frame.set_build_fn(self._build_ui)

        self._model._add_active_folders_changed_fn(self._on_active_folders_changed)
        self._model._add_traverse_progress_fn(self._on_progress)

    def destroy(self) -> None:
        # Called twice in a teardown that unwinds more than one way - the model is dropped on the
        # first call, so the second used to raise AttributeError before reaching the rest.
        if self._model is not None:
            self._model._remove_active_folders_changed_fn(self._on_active_folders_changed)
            self._model._remove_traverse_progress_fn(self._on_progress)
        if self._window is not None:
            self._window.visible = False
            self._window.destroy()
            self._window = None
        self._tree = None
        self._tree_model = None
        self._delegate = None
        self._model = None

    @property
    def visible(self) -> bool:
        return self._window is not None and self._window.visible

    def show(self) -> None:
        """
        Open the popup. Does nothing if it is already open - clicking again must not toggle.

        Opening it when nothing is running starts a fresh list: rows accumulate for as long as the
        window is up, but a new session should not begin with the leftovers of the last one.
        """
        if self._window is None or self._window.visible:
            return
        if self._model is not None and not self._model.active_folders:
            self._tree_model.reset()
        self._window.visible = True
        self._refresh()

    def hide(self) -> None:
        if self._window is not None:
            self._window.visible = False

    def _cancel_row(self, item) -> None:
        """Stop one collection. The row stays; its state changes to Cancelled."""
        if self._model is None:
            return
        url = getattr(item.folder, "url", None)
        if not url:
            return
        self._model._cancel_traverse(url)
        # Repaint now rather than waiting for the next progress tick: a cancelled traverse stops
        # producing them, so without this the row would keep its last running numbers on screen.
        self._refresh()

    # ------------------------------------------------------------------------------ internals --

    def _build_ui(self) -> None:
        with ui.VStack(spacing=4):
            ui.Spacer(height=2)
            with ui.ScrollingFrame(
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
            ):
                # Counts only, no bar: "found" keeps growing as listing discovers more, so a bar
                # would be a fraction of a moving denominator - it slides backwards and implies an
                # end point the scan cannot predict. Plain columns are honest about that.
                self._tree = ui.TreeView(
                    self._tree_model,
                    delegate=self._delegate,
                    root_visible=False,
                    header_visible=True,
                    column_widths=COLUMN_WIDTHS,
                )
            ui.Spacer(height=2)
        self._refresh()

    def _on_active_folders_changed(self) -> None:
        # Deliberately does NOT close when the list drains. Completed collections keep their row so
        # the user can see what the scan produced; closing on the last completion would hide the
        # result at the moment it became interesting. The window is dismissed by the user.
        self._refresh()

    def _on_progress(self, ctx) -> None:
        # Throttled: a scan resolves thousands of files and each one notifies.
        now = time.time()
        if now - self._last_refresh < REFRESH_INTERVAL:
            return
        self._last_refresh = now
        self._refresh()

    def _refresh(self) -> None:
        """
        Bring the tree up to date.

        Rows are only rebuilt when the set of collections changes; a progress tick just pushes new
        strings into the existing value models, so a scan updating counts many times a second does
        not churn widgets.
        """
        if self._model is None or not self.visible:
            return
        # Add whatever is newly in flight, then repaint every row - including finished ones, whose
        # numbers have settled but which are still listed.
        self._tree_model.add_folders(list(self._model.active_folders))
        self._tree_model.refresh_values()
