# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import functools
import time
import traceback
import weakref
from pathlib import Path

import carb
import carb.dictionary
import carb.eventdispatcher
import carb.settings
import omni.kit.app
from omni.kit.async_engine import run_coroutine
from omni.kit.search_core import SearchEngineRegistry
from omni.kit.widget.prompt import PromptButtonInfo, PromptManager
from omni.kit.window.content_browser import (
    ContentBrowser,
    ContentBrowserWidget,
    ContentBrowserWindow,
    get_content_window,
)
from omni.kit.window.filepicker import UI_READY_GLOBAL_EVENT, FilePickerView

from ._cmd import (
    ActivateAssetSearch,
    ApplyTreeFilter,
    ClearTreeFilter,
    Cmd,
    DeactivateAssetSearch,
    LoadBackend,
    ResolveBackends,
    SetBrowserSearchEngine,
    ShowErrorPrompt,
    StartIndexing,
    TriggerSearch,
)
from ._config import get_extension_config
from ._loader import AssetLibraryLoader, LibraryConfig
from ._model import AssetLibrarySearchModel
from ._msg import (
    AssetSearchMenuClicked,
    AssetSearchModeSelected,
    BackendLoaded,
    BackendLoadFailed,
    BackendsResolved,
    BrowserSelectionChanged,
    IndexingDone,
    IndexingFailed,
    IndexingProgress,
    Msg,
    SearchCompleted,
    SearchStarted,
)
from ._state import State, UiPhase
from ._update import update
from ._url import (
    Url,
    get_available_backends_for_url,
)
from .search import AssetLibraryInterface, SearchBackend
from .ui import ContentBrowserToolbarPatch, ContentBrowserTreeFilter
from .ui._thumbnail_card import install_patch as _install_thumbnail_patch
from .ui._thumbnail_card import uninstall_patch as _uninstall_thumbnail_patch
from .ui.panel import SearchWizardUi

__all__ = ["BrowserExtensionImpl"]

# Persisted by omni.kit.window.content_browser; read before forcing grid view for asset search.
_CONTENT_BROWSER_SHOW_GRID_VIEW_SETTING = "/exts/omni.kit.window.content_browser/show_grid_view"


def get_extension_path() -> str:
    return omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)


def get_extension_icons_path() -> Path:
    return Path(get_extension_path()) / "icons"


class BrowserExtensionImpl:
    ASSET_SEARCH_ENGINE_NAME = "SimReady Search"
    # Built-in content browser file search; used as the default so registering
    # our engine never silently becomes the active search.
    DEFAULT_SEARCH_ENGINE_NAME = "File Search"
    """Implementation details for the SimReady content browser extension."""

    def __init__(self):
        self._weak_self = weakref.ref(self)
        self._search_engine_sub = None
        self._library_loader: AssetLibraryLoader = AssetLibraryLoader()
        self._wizard_ui: SearchWizardUi | None = None
        self._state = State()
        self._content_browser_ref: weakref.ref[ContentBrowser] | None = None
        self._menu_items: list[dict] = []
        self._ui_ready_sub = None
        # Tree-view filtering stays dormant until the user first activates the
        # Asset Search UI — we don't want to interfere with the default Content
        # Browser experience for users who never open the search wizard.
        self._tree_filter_active = False
        # Backward-compatibility fields for in-session hot-reload transitions:
        # older method bodies may still execute briefly from stale tasks.
        self._current_tree_filter = None
        self._original_available_collections: list[str] | None = None
        self._injected_tree_items: list[tuple[object, object, object]] = []
        self._tree_filter_ui = ContentBrowserTreeFilter(lambda: self.content_browser)
        self._toolbar_patch = ContentBrowserToolbarPatch(
            lambda: self.content_browser,
            on_mode_selected=lambda backend, ws=self._weak_self: (impl := ws())
            and impl._dispatch(AssetSearchModeSelected(backend)),
        )
        self._fallback_search_engine: str | None = None

    def _dispatch(self, msg: Msg) -> None:
        """Single entry point for all state changes."""
        previous_anchor = self._state.search_location_anchor
        new_state, cmds, rebuild = update(msg, self._state)
        # `update()` is pure and must stay Kit-free, so this is the one place
        # that can report which messages produced which side effects — a
        # `SearchClicked` with no `TriggerSearch` means it was short-circuited.
        carb.log_info(
            f"[SimReady Search] dispatch {type(msg).__name__} -> cmds={[type(c).__name__ for c in cmds]} "
            f"backend={new_state.active_backend} phase={new_state.ui_phase} "
            f"anchor={new_state.search_location_anchor} status={new_state.status_message!r}"
        )
        self._state = new_state
        if previous_anchor != new_state.search_location_anchor:
            anchor = new_state.search_location_anchor
            AssetLibrarySearchModel.set_search_path_anchor(str(anchor) if anchor else None)
        self._render(new_state, rebuild)
        for cmd in cmds:
            run_coroutine(self._execute(cmd))

    def _render(self, state: State, rebuild: bool = True) -> None:
        """Push the new state snapshot into the view; no logic here."""
        if self._wizard_ui:
            self._wizard_ui.set_state(state, rebuild=rebuild)

    async def _execute(self, cmd: Cmd) -> None:
        """Execute a side-effect command returned by ``update()``."""
        if isinstance(cmd, ActivateAssetSearch):
            self._enable_overrides()
            self._set_browser_current_search_engine(self.ASSET_SEARCH_ENGINE_NAME)
            await self._popup_wizard_ui()
        elif isinstance(cmd, DeactivateAssetSearch):
            self._deactivate_asset_search()
        elif isinstance(cmd, LoadBackend):
            await BrowserExtensionImpl._load_backend(self._weak_self, cmd.backend, cmd.url)
        elif isinstance(cmd, TriggerSearch):
            # The delegate only routes to our model while OUR engine is active.
            # Kit caches the engine per server and, for a server it hasn't seen,
            # falls back to the alphabetically-first registered one ("File
            # Search" < "SimReady Search"). Any navigation that moves the browser
            # path therefore re-routes our query away from
            # AssetLibrarySearchModel, so re-assert the engine at the point of use.
            active_engine = self._get_browser_current_search_engine()
            if active_engine != self.ASSET_SEARCH_ENGINE_NAME:
                carb.log_info(
                    f"[SimReady Search] engine drifted to {active_engine!r}; "
                    f"restoring {self.ASSET_SEARCH_ENGINE_NAME!r}"
                )
                self._set_browser_current_search_engine(self.ASSET_SEARCH_ENGINE_NAME)
            search_delegate = self._get_toolbar_search_delegate()
            carb.log_info(
                f"[SimReady Search] TriggerSearch query={cmd.search_params.raw_search_query!r} "
                f"engine={self._get_browser_current_search_engine()!r} "
                f"search_dir={getattr(search_delegate, 'search_dir', None)!r}"
            )
            if search_delegate:
                search_delegate.search(search_query=cmd.search_params.raw_search_query)
            else:
                carb.log_warn("[SimReady Search] TriggerSearch dropped: no toolbar search delegate")
        elif isinstance(cmd, StartIndexing):
            self._start_file_indexing(cmd.locations, cmd.url)
        elif isinstance(cmd, SetBrowserSearchEngine):
            self._set_browser_current_search_engine(cmd.name)
            await self._popup_wizard_ui()
        elif isinstance(cmd, ResolveBackends):
            available = await get_available_backends_for_url(cmd.url)
            self._dispatch(BackendsResolved(url=cmd.url, available=available))
        elif isinstance(cmd, ApplyTreeFilter):
            # Only apply once the user has activated the Asset Search UI at
            # least once — before that we deliberately leave the Content
            # Browser's tree untouched (see `_popup_wizard_ui`).
            if self._tree_filter_active:
                self._apply_tree_filter(cmd.backend)
        elif isinstance(cmd, ClearTreeFilter):
            # Wizard closed — drop any active filter so the Content Browser
            # returns to its default behavior. `_tree_filter_active` goes
            # back to False so the next wizard open re-arms from scratch.
            if self._tree_filter_active:
                self._clear_tree_filter()
                self._tree_filter_active = False
        elif isinstance(cmd, ShowErrorPrompt):
            PromptManager.post_simple_prompt(cmd.title, cmd.message, PromptButtonInfo("Ok", lambda: None))

    # ------------------------------------------------------------------
    # Startup / shutdown
    # ------------------------------------------------------------------

    def startup(self):
        self._toolbar_patch.install()
        _install_thumbnail_patch()
        run_coroutine(self._initialize())

    async def _initialize(self):

        config = get_extension_config()
        weak_self = self._weak_self

        self._state.file_index_locations = config.default_file_index_locations
        self._state.usd_search_endpoint = config.default_usd_search_endpoint
        self._content_browser_ref = weakref.ref(get_content_window())
        self._toolbar_patch.rebuild_if_needed()

        # Re-apply the tree filter whenever the Content Browser UI is rebuilt,
        # e.g. after the user closes and reopens the window. The handler is a
        # no-op until the user first activates the Asset Search UI. The event
        # fires for any filepicker-style window so we gate on the "Content"
        # title in the callback.
        self._ui_ready_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            observer_name="omni.simready.content.browser._tree_filter",
            event_name=UI_READY_GLOBAL_EVENT,
            on_event=functools.partial(BrowserExtensionImpl._on_ui_ready, self._weak_self),
        )

        # Save the current search engine before registering ours
        previous_engine = self._get_browser_current_search_engine()
        if previous_engine == self.ASSET_SEARCH_ENGINE_NAME:
            # Left over from a previous session or a hot-reload. Our engine is
            # only registered once the user activates a search mode, so keeping
            # it selected would leave the browser on a missing engine.
            previous_engine = None
        self._fallback_search_engine = previous_engine

        # Store the exact callable for unsubscribe_selection_changed (identity must match).
        self._browser_selection_callback = functools.partial(
            BrowserExtensionImpl._on_browser_selection_changed, weak_self
        )

        if cb_api := self.content_browser_api:
            cb_api.subscribe_selection_changed(self._browser_selection_callback)

        # Restore the previously-active engine so registering ours never makes
        # it the default. Fall back to the built-in file search when nothing was
        # active yet, otherwise our engine would win the alphabetical fallback
        # in EngineSelection and appear (misleadingly) as the default.
        self._set_browser_current_search_engine(previous_engine or self.DEFAULT_SEARCH_ENGINE_NAME)

        self._menu_items = [
            {
                "name": "AssetSearch here",
                "icon": (get_extension_icons_path() / "search.svg").as_posix(),
                "onclick_fn": functools.partial(BrowserExtensionImpl._on_asset_search_menu_clicked, weak_self),
                "show_fn": lambda selected: Url.parse_from_str(selected) is not None,
                "index": 0,
            },
        ]
        if browser := self.content_browser:
            for item in self._menu_items:
                browser.add_context_menu(item["name"], item["icon"], item["onclick_fn"], item["show_fn"], item["index"])

    def shutdown(self):
        # First, because it is what makes a hot-reload safe and the rest of the
        # teardown below can raise. `SearchEngineRegistry` is a singleton owned
        # by another extension, so an entry we leave behind keeps pointing at
        # this (about to be replaced) AssetLibrarySearchModel class object, and
        # the reloaded extension can no longer attach a library to it.
        self._unregister_asset_search_model()
        # Session teardown is shared with DeactivateAssetSearch (wizard, library,
        # tree filter, search engine, thumbnail patch). The rest of this method
        # is extension-lifetime: toolbar, menus, subscriptions, loader.
        self._deactivate_asset_search()
        self._toolbar_patch.uninstall()
        self._ui_ready_sub = None
        if browser := self.content_browser:
            for item in self._menu_items:
                browser.delete_context_menu(item["name"])
        self._library_loader = None

        if cb_api := self.content_browser_api:
            cb_api.unsubscribe_selection_changed(self._browser_selection_callback)
        self._browser_selection_callback = None
        self._state = State()

    # ------------------------------------------------------------------
    # External event handlers — all delegate to _dispatch
    # ------------------------------------------------------------------

    @staticmethod
    def _on_asset_search_menu_clicked(weak_self: weakref.ref["BrowserExtensionImpl"], _: object, item_path: str):
        if self := weak_self():
            self._dispatch(AssetSearchMenuClicked(item_path))

    @staticmethod
    def _on_browser_selection_changed(weak_self: weakref.ref["BrowserExtensionImpl"], _, items):
        self = weak_self()
        if not self:
            return
        self._dispatch(BrowserSelectionChanged(selected_items=items))

    # ------------------------------------------------------------------
    # Wizard UI lifecycle
    # ------------------------------------------------------------------

    def _close_wizard_ui(self) -> None:
        if wizard_ui := self._wizard_ui:
            # Clear the reference *before* destroy so a visibility-change
            # callback firing mid-teardown (which dispatches WizardUiClosed)
            # doesn't re-enter `_render` with a half-torn-down window.
            self._wizard_ui = None
            wizard_ui.destroy()

    async def _popup_wizard_ui(self):
        """Open (or refresh) the search wizard window."""
        # First activation of the Asset Search UI flips on tree-view filtering.
        # The actual filter is applied later, from the BackendLoaded handler
        # (so a successful library load is a prerequisite). Subsequent backend
        # switches keep the flag on and refresh the filter the same way;
        # UI_READY (window rebuild) re-applies whatever's current.
        if not self._tree_filter_active:
            self._tree_filter_active = True
            if self._state.ui_phase == UiPhase.Ready:
                # Library was already loaded before the user ever opened the
                # wizard — apply the filter now, otherwise nothing else will.
                self._apply_tree_filter(self._state.active_backend)
            else:
                # First activation: a LoadBackend is about to run for the
                # default backend (below). Prime the flag that BackendLoaded
                # checks so it emits ApplyTreeFilter on success — otherwise
                # nothing would trigger the initial filter (the default path
                # doesn't go through BackendSelected).
                import dataclasses as _dc

                self._state = _dc.replace(
                    self._state,
                    pending_tree_filter_backend=self._state.active_backend,
                )

        # Sync current browser selection into state before opening.
        if cb_api := self.content_browser_api:
            selected_items = cb_api.get_current_selections(pane=None)
            if selected_items:
                self._dispatch(BrowserSelectionChanged(selected_items=selected_items))

        if ui := self._wizard_ui:
            ui.show()
            ui.set_state(self._state, rebuild=True)
            return

        self._wizard_ui = SearchWizardUi(
            self._state,
            dispatch=functools.partial(BrowserExtensionImpl._dispatch_from_ui, self._weak_self),
        )
        self._wizard_ui.set_state(self._state, rebuild=True)
        await self._execute(LoadBackend(self._state.active_backend, url=self._state.selected_url))

    @staticmethod
    def _dispatch_from_ui(weak_self: weakref.ref["BrowserExtensionImpl"], msg: Msg) -> None:
        """Trampoline so the UI can dispatch without holding a strong reference."""
        if self := weak_self():
            self._dispatch(msg)

    # ------------------------------------------------------------------
    # Backend loading (side effect of LoadBackend cmd)
    # ------------------------------------------------------------------

    @staticmethod
    async def _load_backend(
        weak_self: weakref.ref["BrowserExtensionImpl"],
        backend: SearchBackend,
        url: Url | None = None,
    ):
        self = weak_self()
        if not self or not self._library_loader:
            return

        if library := self._library_loader.get_interface(backend, url):
            await BrowserExtensionImpl._attach_library(weak_self, library)
            return

        if self._wizard_ui:
            self._wizard_ui.set_state(State(**{**self._state.__dict__, "ui_phase": UiPhase.Loading}), rebuild=True)
            for _ in range(3):
                await omni.kit.app.get_app().next_update_async()

        attach_cb = functools.partial(BrowserExtensionImpl._attach_library, weak_self)
        try:
            await self._library_loader.load(
                LibraryConfig(
                    backend=backend,
                    usd_search_endpoint=self._state.usd_search_endpoint,
                    workspace_cache_location=get_extension_config().default_wscache_s3_url,
                    index_locations=self._state.file_index_locations,
                    selected_url=url,
                ),
                attach_cb,
            )
        except Exception as e:
            traceback.print_exc()
            carb.log_error(f"Failed to load search backend: {backend}: {e}")
            self = weak_self()
            if self:
                self._dispatch(BackendLoadFailed(e))

    @staticmethod
    async def _attach_library(weak_self: weakref.ref["BrowserExtensionImpl"], library: AssetLibraryInterface):
        self = weak_self()
        if not self:
            return
        AssetLibrarySearchModel.set_asset_library(library)
        AssetLibrarySearchModel.set_search_complete_callback(
            functools.partial(BrowserExtensionImpl._on_search_complete, weak_self)
        )
        AssetLibrarySearchModel.set_search_started_callback(
            functools.partial(BrowserExtensionImpl._on_search_started, weak_self)
        )
        AssetLibrarySearchModel.set_search_error_callback(
            functools.partial(BrowserExtensionImpl._on_search_error, weak_self)
        )

        # Populate filter autocomplete values from the loaded library.
        import dataclasses

        features = sorted(library.get_available_features())
        profiles = sorted(library.get_available_profiles())
        self._dispatch(BackendLoaded(library))
        # Patch in the populated autocomplete pools after BackendLoaded
        # (which resets to Loading→Ready). These are suggestion lists for the
        # UI, not search inputs, so they live on State.
        self._state = dataclasses.replace(
            self._state,
            available_features=features,
            available_profiles=profiles,
        )
        if self._wizard_ui:
            self._wizard_ui.set_state(self._state, rebuild=False)

        anchor = self._state.search_location_anchor
        AssetLibrarySearchModel.set_search_path_anchor(str(anchor) if anchor else None)
        carb.log_info(
            f"[SimReady Search] library attached: {type(library).__name__} anchor={anchor} "
            f"profiles={len(profiles)} features={len(features)}"
        )

    # ------------------------------------------------------------------
    # File indexing (side effect of StartIndexing cmd)
    # ------------------------------------------------------------------

    def _start_file_indexing(self, locations, url: Url | None = None):
        if not self._library_loader:
            return
        weak_self = self._weak_self
        self._library_loader.start_indexing(
            locations,
            url=url,
            on_done=functools.partial(BrowserExtensionImpl._on_indexing_done, weak_self),
            on_error=functools.partial(BrowserExtensionImpl._on_indexing_error, weak_self),
        )
        run_coroutine(BrowserExtensionImpl._poll_indexing_progress(weak_self))

    @staticmethod
    async def _poll_indexing_progress(weak_self: weakref.ref["BrowserExtensionImpl"]):
        await asyncio.sleep(0.1)
        start = time.perf_counter()
        while True:
            self = weak_self()
            if not self or not self._library_loader:
                return
            library = self._library_loader.get_interface(SearchBackend.FILE_INDEX, self._state.selected_url)
            if not library or not library.is_indexing():
                break
            await asyncio.sleep(0.1)
            self = weak_self()
            if not self:
                return
            elapsed = time.perf_counter() - start
            self._dispatch(IndexingProgress(file_count=library.num_indexed_files(), elapsed=elapsed))
            if self._wizard_ui:
                self._wizard_ui.show_status_message(self._state.status_message)

    @staticmethod
    def _on_indexing_done(weak_self: weakref.ref["BrowserExtensionImpl"], asset_count: int):
        self = weak_self()
        if not self:
            return
        self._dispatch(IndexingDone(asset_count=asset_count))
        if self._wizard_ui:
            self._wizard_ui.show_status_message(self._state.status_message)

    @staticmethod
    def _on_indexing_error(weak_self: weakref.ref["BrowserExtensionImpl"], exc: Exception):
        carb.log_error(f"Indexing failed: {exc}")
        if self := weak_self():
            self._dispatch(IndexingFailed(error=exc))
            if self._wizard_ui:
                self._wizard_ui.show_status_message(self._state.status_message)

    # ------------------------------------------------------------------
    # Search callbacks
    # ------------------------------------------------------------------

    @staticmethod
    async def _on_search_complete(weak_self: weakref.ref["BrowserExtensionImpl"], asset_count: int, duration: float):
        if self := weak_self():
            self._dispatch(SearchCompleted(asset_count=asset_count, duration=duration))
            if self._wizard_ui:
                self._wizard_ui.show_status_message(self._state.status_message)

    @staticmethod
    async def _on_search_started(weak_self: weakref.ref["BrowserExtensionImpl"]):
        if self := weak_self():
            self._dispatch(SearchStarted())
            if self._wizard_ui:
                self._wizard_ui.show_status_message(self._state.status_message)

    @staticmethod
    def _on_search_error(weak_self: weakref.ref["BrowserExtensionImpl"], error: Exception):
        carb.log_error(f"[SimReady Asset Search] Search failed: {error}")
        traceback.print_exc()
        if self := weak_self():
            self._execute(ShowErrorPrompt("Search Failed", f"Asset search failed:\n{error}"))

    def _apply_tree_filter(self, backend):
        if error := self._tree_filter_ui.apply_tree_filter(backend):
            self._dispatch(BackendLoadFailed(RuntimeError(error)))

    def _clear_tree_filter(self):
        self._tree_filter_ui.clear_tree_filter()
        self._tree_filter_ui.remove_registered_s3_urls()

    @staticmethod
    def _on_ui_ready(weak_self: weakref.ref["BrowserExtensionImpl"], event):
        self = weak_self()
        if not self:
            return
        error = self._tree_filter_ui.on_ui_ready(
            event, backend=self._state.active_backend, tree_filter_active=self._tree_filter_active
        )
        if error:
            self._dispatch(BackendLoadFailed(RuntimeError(error)))

    @property
    def content_browser(self) -> "ContentBrowser | None":
        if self._content_browser_ref is None:
            return None
        return self._content_browser_ref()

    @property
    def content_browser_window(self) -> "ContentBrowserWindow | None":
        if browser := self.content_browser:
            return getattr(browser, "_window", None)
        return None

    @property
    def content_browser_widget(self) -> "ContentBrowserWidget | None":
        if cb_window := self.content_browser_window:
            return cb_window.widget
        return None

    @property
    def content_browser_filepicker_view(self) -> "FilePickerView | None":
        if cb_widget := self.content_browser_widget:
            return getattr(cb_widget, "_view", None)
        return None

    @property
    def content_browser_api(self) -> "ContentBrowserApi | None":  # noqa: F821
        if browser := self.content_browser:
            return browser.api
        return None

    def _get_toolbar_search_delegate(self) -> "SearchDelegate | None":  # noqa: F821
        if api := self.content_browser_api:
            if tool_bar := api.tool_bar:
                return getattr(tool_bar, "_search_delegate", None)
        return None

    def _get_browser_current_search_engine(self) -> str | None:
        if search_delegate := self._get_toolbar_search_delegate():
            if engine_delegate := getattr(search_delegate, "_engine_delegate", None):
                return engine_delegate.current_engine
        return None

    def _set_browser_current_search_engine(self, engine_name: str):
        if api := self.content_browser_api:
            if tool_bar := api.tool_bar:
                if search_delegate := getattr(tool_bar, "_search_delegate", None):
                    if engine_delegate := getattr(search_delegate, "_engine_delegate", None):
                        engine_delegate.current_engine = engine_name

    def _clear_browser_search_field(self):
        """Empty the toolbar search field and drop the results it produced.

        The delegate owns the text, the tokens and the result model, so we
        trigger its own clear action instead of reproducing the reset here.
        Passing an empty query to `search()` would leave the field in its
        "searching" visual state with the hint label hidden.
        """
        search_delegate = self._get_toolbar_search_delegate()
        if search_delegate is None:
            return
        if clear := getattr(search_delegate, "_on_clear_clicked", None):
            clear()
        else:
            search_delegate.search(search_query="")

    def _detach_active_library(self):
        AssetLibrarySearchModel.set_asset_library(None)
        AssetLibrarySearchModel.set_search_path_anchor(None)
        AssetLibrarySearchModel.set_search_complete_callback(None)
        AssetLibrarySearchModel.set_search_started_callback(None)
        AssetLibrarySearchModel.set_search_error_callback(None)

    def _register_asset_search_model(self) -> None:
        if self._search_engine_sub is not None:
            return
        registry = SearchEngineRegistry()
        name = self.ASSET_SEARCH_ENGINE_NAME
        # Delete the engine from the registry if it exists.
        if registry.get_search_model(name) is not None:
            del registry._engines[name]
        self._search_engine_sub = registry.register_search_model(name, AssetLibrarySearchModel)

    def _unregister_asset_search_model(self) -> None:
        self._search_engine_sub = None

    def _enable_overrides(self) -> None:
        self._register_asset_search_model()
        _install_thumbnail_patch()
        self._switch_to_grid_view()
        if error := self._tree_filter_ui.ensure_usd_search_s3_url(self._state.active_backend):
            self._dispatch(BackendLoadFailed(RuntimeError(error)))

    def _deactivate_asset_search(self) -> None:
        """Undo session-scoped asset search (ActivateAssetSearch / _enable_overrides).

        Shared by ``DeactivateAssetSearch`` and ``shutdown()``. Does not touch
        extension-lifetime hooks (toolbar patch, context menus, selection
        subscription, UI_READY observer, library loader).
        """
        self._close_wizard_ui()
        self._detach_active_library()
        self._unregister_asset_search_model()
        _uninstall_thumbnail_patch()
        # Always restore the tree, even if the active flag is stale — shutdown
        # and deactivate must leave the Content Browser unfiltered.
        self._clear_tree_filter()
        self._tree_filter_active = False
        self._set_browser_current_search_engine(self.DEFAULT_SEARCH_ENGINE_NAME)
        # Clear the browser search field from any previous search results.
        self._clear_browser_search_field()

    def _switch_to_grid_view(self) -> None:
        """Switch the Kit content browser to grid (tile) view while SimReady search is active."""
        if browser := self.content_browser:
            browser.toggle_grid_view(True)
        if filepicker_view := self.content_browser_filepicker_view:
            filepicker_view.scale_grid_view(1.2)
