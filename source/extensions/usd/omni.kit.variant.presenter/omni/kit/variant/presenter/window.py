## Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

import asyncio
import weakref
from typing import List, Optional

import carb
import omni.ui as ui
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.widget.settings import get_style

from . import style
from .delegate import Delegate
from .model import Model
from .stage_change_helper import StageChangeHelper


class VariantPresenterWindow:

    def __init__(self):
        self._window = ui.Window("Variant Presenter", width=600, height=800, dockPreference=ui.DockPreference.RIGHT_TOP)
        self._window.deferred_dock_in("Stage", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)
        self._tab_collection = ui.RadioCollection()
        self._view_collection = ui.RadioCollection()
        self._usd_context = omni.usd.get_context()
        self._stage = self._usd_context.get_stage()
        self._model = Model()
        self._selected = 0
        self._selection_index = 1
        self._stage_event_subs = [
            get_eventdispatcher().observe_event(
                observer_name="Variant Presenter Window:Stage",
                event_name=self._usd_context.stage_event_name(event),
                on_event=func,
            )
            for event, func in (
                (omni.usd.StageEventType.OPENED, self._on_stage_opened),
                (omni.usd.StageEventType.CLOSED, self._on_stage_closed),
                (omni.usd.StageEventType.SELECTION_CHANGED, self._on_stage_selection_changed),
            )
        ]
        self._delegate = Delegate()
        self._tree_view = None
        self._remove_all_window = None
        self._groups_stack: ui.HStack() = None
        self._prims_stack: ui.HStack() = None
        self._build_ui()
        self._item_changed_subscription = self._model.subscribe_item_changed_fn(self._on_item_changed)
        self._stage_change_helper = None
        self._expand_inflight = False
        # If a stage is already loaded when the window is created, the OPENED event
        # has already fired and _on_stage_opened() will never run, leaving the stage
        # change listener unregistered and the model unloaded. Simulate the opened
        # flow here so variant changes are detected and "View All" shows the current
        # stage's variant prims.
        if self._stage:
            self._register_listener()
            self._load_model()

    def set_visible(self, value: bool):
        """Set window visibility."""
        self._window.visible = value

    def set_visibility_changed_listener(self, listener):
        """Set external visibility change listener."""
        self._window.set_visibility_changed_fn(listener)

    def _load_model(self):
        if self._tree_view:
            # Use current stage from context so we never reload with a stale/invalid stage
            # (e.g. after new_stage_async() before OPENED event has run).
            self._stage = self._usd_context.get_stage()
            # Ensure stage change listener is registered so variant changes are detected.
            # This is needed when the window opens after the stage is already loaded,
            # since the OPENED event will have already fired before the window existed.
            self._register_listener()
            self._model.reload(self._usd_context, self._stage)
            asyncio.ensure_future(self._expand_tree())

    def _on_item_changed(self, model: Model, item):
        if self._tree_view:
            if item:
                if self._groups_stack.visible and self._tree_view:
                    self._selected = len(self._tree_view.selection)
                    if self._selected == self._selection_index:
                        self._model.refresh()
                        asyncio.ensure_future(self._expand_tree())
                        self._selection_index = 1
                    else:
                        self._selection_index += 1
            else:
                asyncio.ensure_future(self._expand_tree())

    def _register_listener(self):
        if self._stage and not self._stage_change_helper:
            self._stage_change_helper = StageChangeHelper(model=self)
            self._stage_change_helper.register_stage_listener(self._stage)

    def _deregister_listener(self):
        if self._stage_change_helper:
            self._stage_change_helper.unregister_stage_listener()
            self._stage_change_helper = None

    def update_dirty(self):
        """Update model based on cached USD changes."""
        dirty_prim_paths = self._stage_change_helper.consume_dirty_paths()
        if not dirty_prim_paths:
            return
        if not self._stage:
            return

        # We already filtered for "set()" properties in StageChangeHelper,
        # so we know these are variant selection changes. No need to re-validate.
        try:
            self._model.invalidate_variant_prims_cache()
            # Invalidate cache for each changed prim
            for prim_path in dirty_prim_paths.keys():
                self._model.invalidate_vset_cache_for(prim_path)
        except Exception:
            pass

        # Trigger debounced refresh
        self._model.refresh()
        asyncio.ensure_future(self._expand_tree())

    def _on_stage_opened(self, _):
        self._usd_context = omni.usd.get_context()
        self._stage = self._usd_context.get_stage()
        self._register_listener()
        if not self._item_changed_subscription:
            self._item_changed_subscription = self._model.subscribe_item_changed_fn(self._on_item_changed)
        self._load_model()

    def _on_stage_closed(self, _):
        self._deregister_listener()
        if self._item_changed_subscription:
            self._item_changed_subscription = None
        self._model.destroy()

    def _on_stage_selection_changed(self, _):
        if self._tree_view:
            if self._prims_stack.visible and self._model._view_state == 1:
                self._model.refresh(True)
                asyncio.ensure_future(self._expand_tree())

    def destroy(self):
        """ """
        if self._stage_event_subs:
            self._stage_event_subs.clear()
            self._stage_event_subs = None
        if self._item_changed_subscription:
            self._item_changed_subscription = None
        if self._stage_change_helper:
            self._stage_change_helper.destroy()
            self._stage_change_helper = None
        # Tear the model down explicitly so its pending debounced refresh task
        # is cancelled. Otherwise, destroying the window without a prior stage
        # close (e.g. extension unload, ad-hoc test cleanup) leaves the model
        # orphaned with a live asyncio task that holds the only reference back
        # to it. Model.destroy() is idempotent with the _on_stage_closed path.
        if self._model is not None:
            self._model.destroy()
        self._window = None
        self._model = None
        self._delegate = None
        self._tree_view = None
        self._remove_all_window = None
        self._groups_stack = None
        self._prims_stack = None

    def _build_ui(self):
        ui_style = get_style()
        use_default_style = carb.settings.get_settings().get_as_bool("/persistent/app/window/useDefaultStyle") or False
        if not use_default_style:
            self._window.frame.set_style(ui_style)
        self._window.frame.clear()
        with self._window.frame:
            with ui.VStack(spacing=5):
                with ui.HStack(height=0):
                    ui.RadioButton(
                        text="PRIMS",
                        radio_collection=self._tab_collection,
                        style=style.TABS,
                        clicked_fn=lambda: self.toggle_tabs(False),
                    )
                    ui.RadioButton(
                        text="GROUPS",
                        radio_collection=self._tab_collection,
                        style=style.TABS,
                        clicked_fn=lambda: self.toggle_tabs(True),
                    )
                ui.Line(height=1)
                with ui.ScrollingFrame(
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                ):
                    with ui.HStack():
                        with ui.VStack(spacing=4, style=style.UI_STYLE):
                            with ui.HStack(height=24):
                                with ui.ZStack():
                                    self._prims_stack = ui.HStack()
                                    with self._prims_stack:
                                        ui.Spacer(width=4)
                                        with ui.HStack(width=0):
                                            ui.RadioButton(
                                                radio_collection=self._view_collection,
                                                width=22,
                                                height=22,
                                                style=style.RADIO,
                                                clicked_fn=lambda: self._set_view(0),
                                            )
                                            ui.Label("View All", tooltip="Display all variants in scene.")
                                        ui.Spacer(width=8)
                                        with ui.HStack():
                                            ui.RadioButton(
                                                radio_collection=self._view_collection,
                                                width=22,
                                                height=22,
                                                style=style.RADIO,
                                                clicked_fn=lambda: self._set_view(1),
                                            )
                                            ui.Label(
                                                "View Selected",
                                                tooltip="Only display variants of currently selected prims.",
                                            )
                                    self._groups_stack = ui.HStack()
                                    with self._groups_stack:
                                        with ui.ZStack(width=125):
                                            ui.Rectangle(height=22, style=style.RECT)
                                            with ui.HStack():
                                                ui.Spacer(width=1)
                                                with ui.VStack():
                                                    ui.Spacer(height=1)
                                                    ui.Image(height=20, width=20, style=style.ADD)
                                            ui.Button(
                                                "Add Group",
                                                height=22,
                                                style=style.BUTTON,
                                                tooltip="Adds a new group.",
                                                clicked_fn=lambda: self._add_group(),
                                            )
                                        ui.Spacer(width=3)
                                        with ui.ZStack(width=125):
                                            ui.Rectangle(height=22, style=style.RECT)
                                            with ui.HStack():
                                                ui.Spacer(width=1)
                                                with ui.VStack():
                                                    ui.Spacer(height=1)
                                                    ui.Image(height=20, width=20, style=style.REMOVE)
                                            ui.Button(
                                                " Remove All",
                                                height=22,
                                                style=style.BUTTON,
                                                tooltip="Removes all groups and returns variants to a flat list.",
                                                clicked_fn=lambda: self._remove_all(),
                                            )
                                with ui.HStack(width=0, style={"alignment": ui.Alignment.RIGHT_CENTER}):
                                    self._checkbox = ui.CheckBox(
                                        width=22,
                                        style={"margin": 4},
                                        tooltip="Hides all variants that are locked and cannot be modified.",
                                    )
                                    self._checkbox.model.add_value_changed_fn(lambda a: self.toggle_locked_variants(a))
                                    ui.Label("Hide Locked Variants")
                            try:
                                from omni.kit.widget.searchfield import SearchField

                                with ui.HStack(height=22):
                                    self._search_field = SearchField(
                                        on_search_fn=self._on_search,
                                        subscribe_edit_changed=True,
                                        style=style.UI_STYLE,
                                        show_tokens=False,
                                    )
                            except ImportError:
                                self._search_field = None
                            with ui.ScrollingFrame(
                                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
                                style_type_name_override="TreeView.ScrollingFrame",
                                alignment=ui.Alignment.CENTER_TOP,
                            ):
                                self._tree_view = ui.TreeView(
                                    self._model,
                                    delegate=self._delegate,
                                    root_visible=False,
                                    header_visible=False,
                                    selection_changed_fn=lambda w: self._set_selection(self._tree_view),
                                )
                                self._model._tree = weakref.ref(self._tree_view)
                            ui.Line(height=2)
                            ui.Button(
                                "",
                                height=24,
                                width=24,
                                style=style.REFRESH,
                                tooltip="Refreshes the variant list.",
                                clicked_fn=lambda: self._model.refresh(),
                            )
        self.toggle_tabs(False)

    def toggle_tabs(self, is_groups):
        self._model.set_tab(is_groups)
        self._prims_stack.visible = not is_groups
        self._groups_stack.visible = is_groups
        asyncio.ensure_future(self._expand_tree())
        self._tab_collection.model.set_value(int(is_groups))

    def toggle_locked_variants(self, state):
        self._model.toggle_locked_variants(state.get_value_as_bool())

    def _on_search(self, search_words: Optional[List[str]]) -> None:
        if self._tree_view:
            self._model.search(search_words)
            asyncio.ensure_future(self._expand_tree(True))

    def _set_view(self, view_state=0):
        self._view_collection.model.set_value(view_state)
        if self._tree_view:
            self._model.set_view_mode(view_state)

    def _add_group(self):
        if self._tree_view:
            self._model.add_group()

    def _set_selection(self, tree_view):
        self._model.set_selection(tree_view.selection)

    def _remove_all(self):
        def on_remove_all():
            for group in self._model.groups:
                self._model.remove_group(group)

        if self._tree_view:
            if self._remove_all_window is None:
                self._remove_all_window = RemoveAllWindow()
            self._remove_all_window.show("Remove All Groups", on_remove_all)

    async def _expand_tree(self, search=False):
        if self._expand_inflight:
            return
        self._expand_inflight = True
        try:
            await omni.kit.app.get_app().next_update_async()
            for group in self._model.groups:
                if search:
                    expand_state = True
                else:
                    try:
                        expand_state = self._model._expanded_state[group.group_name]
                    except:
                        expand_state = True
                # Skip redundant expand operations
                try:
                    if self._tree_view.is_expanded(group) != expand_state:
                        self._tree_view.set_expanded(group, expand_state, False)
                except Exception:
                    self._tree_view.set_expanded(group, expand_state, False)
            for prim in self._model.prims:
                if search:
                    expand_state = True
                else:
                    try:
                        expand_state = self._model._expanded_state[prim.prim_path]
                    except:
                        expand_state = True
                try:
                    if self._tree_view.is_expanded(prim) != expand_state:
                        self._tree_view.set_expanded(prim, expand_state, False)
                except Exception:
                    self._tree_view.set_expanded(prim, expand_state, False)
        finally:
            self._expand_inflight = False


class RemoveAllWindow(ui.Window):
    def __init__(self):
        super().__init__(
            title="Remove All Groups",
            dockPreference=ui.DockPreference.DISABLED,
            visible=False,
            flags=ui.WINDOW_FLAGS_NO_RESIZE | ui.WINDOW_FLAGS_MODAL,
            width=250,
            height=0,
        )
        self._on_remove_all_fn = None

        with self.frame:
            with ui.VStack(height=0):
                ui.Spacer(height=4)
                ui.Label("Do you want to remove all groups?", alignment=ui.Alignment.CENTER)
                ui.Spacer(height=8)
                with ui.HStack():
                    ui.Button(text="Confirm", clicked_fn=lambda *_: self._on_confirm_remove_all())
                    ui.Button(text="Cancel", clicked_fn=lambda *_: self._dismiss())

    def show(self, title, on_remove_all):
        self.title = title
        self._on_remove_all_fn = on_remove_all
        self.visible = True

    def _on_confirm_remove_all(self):
        if self._on_remove_all_fn:
            self._on_remove_all_fn()
        self._dismiss()

    def _dismiss(self):
        self.visible = False
