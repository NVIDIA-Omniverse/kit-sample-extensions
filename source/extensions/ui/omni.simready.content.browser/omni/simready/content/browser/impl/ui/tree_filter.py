# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, Callable

import carb

from .._config import get_extension_config
from .._url import Url, ensure_trailing_slash
from ..search import SearchBackend

if TYPE_CHECKING:
    from omni.kit.widget.filebrowser import FileBrowserItem

# Collection identifiers from the filepicker's NavigationModel
# (omni.kit.window.filepicker.collections.*). These control which top-level
# collection roots ("Omniverse", "S3", "Azure", ...) are rendered at all —
# see ``NavigationModel.available_collections``. We can't distinguish them by
# name/path in our filter_fn because S3, Azure and Custom all report the
# same ``https://`` path, which would pass a naive ancestor match.
_COLLECTION_S3 = "s3"
_COLLECTION_HTTP = "http"
_COLLECTION_OMNIVERSE = "omniverse"
_COLLECTION_FILESYSTEM = "my-computer"
_COLLECTION_REGISTRATION_ERROR = "Could not register S3 or HTTP collections"


def backend_collection_identifiers(backend: SearchBackend) -> list[str]:
    """Return the top-level navigation collections that should be visible for *backend*.

    The list is in display order. Empty list means "don't touch the current set"
    — which is never what we want once filtering is active, so callers should
    always map to a concrete list per backend.
    """
    match backend:
        case SearchBackend.USD_SEARCH:
            return [_COLLECTION_S3]
        case SearchBackend.WORKSPACE_CACHE:
            return [_COLLECTION_OMNIVERSE, _COLLECTION_S3]
        case SearchBackend.FILE_INDEX:
            return [_COLLECTION_S3, _COLLECTION_FILESYSTEM]
        case _:
            return []


def _usd_search_allowed_prefixes(config) -> list[str]:
    """Allow only the S3 subtree rooted at the mapped index location's asset folder.

    The active USD search service (``default_usd_search_endpoint``) selects the
    index URL from ``default_usd_search_index_mapping``; other S3 buckets are
    excluded from the filtered tree. ``usd_search_tree_root_subpath`` narrows
    the index bucket down to the folder that should act as the tree root.
    """
    tree_root_url = config.default_usd_search_tree_root_url
    if tree_root_url is None:
        carb.log_warn(
            "[SimReady] USD search tree filter: no index location in usd_search_index_mapping "
            f"for endpoint {config.default_usd_search_endpoint!r}; S3 subtree filtering is disabled."
        )
        return []
    prefix = ensure_trailing_slash(str(tree_root_url))
    return [prefix] if prefix else []


def _backend_prefixes(backend: SearchBackend) -> list[str]:
    """Return the allowed path prefixes for items *inside* visible collections.

    Prefixes are directory-style (trailing slash) thanks to ``_config`` sanitization.
    """
    config = get_extension_config()
    match backend:
        case SearchBackend.USD_SEARCH:
            prefixes = _usd_search_allowed_prefixes(config)
        case SearchBackend.WORKSPACE_CACHE:
            prefixes = [str(u) for u in config.default_wscache_root_urls]
        case SearchBackend.FILE_INDEX:
            prefixes = [str(u) for u in config.default_file_index_locations]
        case _:
            prefixes = []
    # Drop empties so ``startswith("")`` (which matches everything) never fires.
    return [p for p in prefixes if p]


def build_tree_filter(
    backend: SearchBackend,
    *,
    include_ancestors: bool = True,
) -> Callable[["FileBrowserItem"], bool]:
    """Build a `FileBrowserModel.filter_fn` for items *inside* visible collections.

    Top-level collection roots (Omniverse, S3, ...) are handled separately via
    ``NavigationModel.available_collections``; see
    :func:`backend_collection_identifiers`. This filter therefore only needs
    to worry about sub-items: servers/buckets and folders below them.

    Matching is done on the trailing-slash forms of both item path and
    prefix, so ``.../Foo`` never matches ``.../Foobar``.

    ``include_ancestors`` controls whether items that sit *above* an allowed
    prefix are kept visible. The default (True) is what you want when the
    tree must display the full chain down from the collection root to the
    prefix — otherwise the user can't drill in (items are lazy-loaded). Pass
    False when the caller injects explicit shortcut items directly under the
    collection: those shortcuts *are* the prefix, and everything in between
    (bucket root, intermediate folders) should disappear.
    """
    prefixes = _backend_prefixes(backend)
    # Normalize once: every prefix in path-slash form so comparisons are O(1)
    # string ops on the hot path.
    prefix_slashes = [p if p.endswith("/") else p + "/" for p in prefixes]
    # Whether items belonging to the "My Computer" collection should pass the
    # filter. Its children don't carry the ``my-computer://`` scheme — they
    # report raw local paths (``/home/...``, ``C:/Users/...``), so a path
    # prefix match is impractical. We allow all path-shaped entries when the
    # collection is enabled for this backend.
    allow_local_fs = _COLLECTION_FILESYSTEM in backend_collection_identifiers(backend)

    def _filter(item: "FileBrowserItem") -> bool:
        path = getattr(item, "path", None) or ""
        if not path:
            return False
        path_slash = path if path.endswith("/") else path + "/"
        # Scheme-only paths (``https://``, ``omniverse://``, ...) identify
        # top-level NavigationModel collection roots. Their visibility is
        # governed by ``NavigationModel.available_collections``, *not* by
        # path-prefix matching — a strict descendants-only filter would
        # otherwise hide the collection itself and everything under it.
        if path_slash.endswith("://"):
            return True
        # Local filesystem entries can show up either as raw paths
        # ("/home/...", "C:/...") or as file URLs ("file://..."), especially
        # in Bookmarks. No stable path-prefix rule covers both forms, so allow
        # them wholesale when the filesystem collection is enabled.
        parsed = urllib.parse.urlparse(path)
        if allow_local_fs and ("://" not in path_slash or parsed.scheme == "file"):
            return True
        for prefix_slash in prefix_slashes:
            if path_slash.startswith(prefix_slash):
                return True
            if include_ancestors and prefix_slash.startswith(path_slash):
                return True
        return False

    return _filter


def tree_shortcut_label(url: Url) -> str:
    """Short display label for a tree-shortcut item — the URL's last path segment.

    Falls back to the whole string when there is no path (e.g. a bare
    ``omniverse://server/``) so the injected item is never nameless.
    """
    stripped = str(url).rstrip("/")
    idx = stripped.rfind("/")
    leaf = stripped[idx + 1 :] if idx != -1 else stripped
    return leaf or stripped


class ContentBrowserTreeFilter:
    def __init__(self, get_content_browser: Callable[[], object | None]):
        self._get_content_browser = get_content_browser
        self.current_tree_filter = None
        self.original_available_collections: list[str] | None = None
        self.injected_tree_items: list[tuple[object, object, object]] = []
        self.registered_s3_items: list[tuple[object, object, object]] = []

    def get_tree_filebrowser(self):
        browser = self._get_content_browser()
        if browser is None:
            return None, None
        window = getattr(browser, "_window", None)
        widget = getattr(window, "widget", None) if window is not None else None
        view = getattr(widget, "_view", None) if widget is not None else None
        filebrowser = getattr(view, "_filebrowser", None) if view is not None else None
        if filebrowser is None:
            return None, None
        model = getattr(filebrowser, "navigation_model", None) or getattr(filebrowser, "_models", None)
        if model is None:
            return filebrowser, None
        if not (hasattr(model, "available_collections") and hasattr(model, "collections")):
            return filebrowser, None
        return filebrowser, model

    def apply_tree_filter(self, backend) -> str | None:
        filebrowser, model = self.get_tree_filebrowser()
        if model is None:
            return None
        self.remove_tree_shortcuts()
        self.set_model_available_collections(model, backend_collection_identifiers(backend))
        if error := self.ensure_usd_search_s3_url(backend, model):
            return error
        self.inject_tree_shortcuts(backend, model)
        include_ancestors = not self.injected_tree_items
        filter_fn = build_tree_filter(backend, include_ancestors=include_ancestors)
        self.current_tree_filter = filter_fn
        try:
            model.set_filter_fn(filter_fn)
        except Exception as e:  # noqa: BLE001
            carb.log_warn(f"[SimReady] Failed to set tree filter on {model!r}: {e}")
        if filebrowser is not None and hasattr(filebrowser, "refresh_ui"):
            try:
                filebrowser.refresh_ui()
            except Exception as e:  # noqa: BLE001
                carb.log_warn(f"[SimReady] Failed to refresh filebrowser UI: {e}")
        self.navigate_to_backend_default(backend)
        return None

    def backend_tree_shortcuts(self, backend) -> list[tuple[str, Url]]:
        pairs: list[tuple[str, Url]] = []
        config = get_extension_config()
        if backend == SearchBackend.WORKSPACE_CACHE:
            if s3_url := config.default_wscache_s3_url:
                pairs.append((_COLLECTION_S3, s3_url))
            if nucleus_url := config.default_wscache_nucleus_url:
                pairs.append((_COLLECTION_OMNIVERSE, nucleus_url))
        elif backend == SearchBackend.USD_SEARCH:
            if tree_root_url := config.default_usd_search_tree_root_url:
                pairs.append((_COLLECTION_S3, tree_root_url))
        return pairs

    @staticmethod
    def get_s3_or_http_collection(model):
        collections = getattr(model, "collections", None)
        if not collections:
            return None
        for identifier in (_COLLECTION_S3, _COLLECTION_HTTP):
            if (collection := collections.get(identifier)) is not None:
                return collection
        return None

    def ensure_usd_search_s3_url(self, backend, model=None) -> str | None:
        """Add the active USD Search index root to S3 for AI/Database modes.

        Existing connections are left untouched and therefore are not removed
        during shutdown. Only items created by this extension are tracked.
        Returns an error message when neither S3 nor HTTP is available.
        """
        if backend not in (SearchBackend.USD_SEARCH, SearchBackend.WORKSPACE_CACHE):
            return None
        if model is None:
            _, model = self.get_tree_filebrowser()
        if model is None:
            carb.log_error(f"[SimReady] {_COLLECTION_REGISTRATION_ERROR}")
            return _COLLECTION_REGISTRATION_ERROR
        collection = self.get_s3_or_http_collection(model)
        if collection is None:
            carb.log_error(f"[SimReady] {_COLLECTION_REGISTRATION_ERROR}")
            return _COLLECTION_REGISTRATION_ERROR
        url = get_extension_config().default_usd_search_index_url
        if url is None:
            carb.log_warn(
                "[SimReady] Cannot register the USD search S3 URL: no index location in "
                "usd_search_index_mapping for the active endpoint."
            )
            return None

        target = str(url).rstrip("/")
        children = getattr(collection, "children", None) or {}
        if any((getattr(child, "path", "") or "").rstrip("/") == target for child in children.values()):
            return None

        try:
            item = collection.add_path(tree_shortcut_label(url), str(url))
        except Exception as e:  # noqa: BLE001
            carb.log_warn(f"[SimReady] Failed to register USD search S3 URL {url}: {e}")
            return None
        if item is None:
            return None
        self.registered_s3_items.append((model, collection, item))
        if hasattr(model, "_item_changed"):
            try:
                model._item_changed(collection)
            except Exception:  # noqa: BLE001
                pass
        return None

    def inject_tree_shortcuts(self, backend, model) -> None:
        pairs = self.backend_tree_shortcuts(backend)
        if not pairs:
            return
        collections = getattr(model, "collections", None)
        if not collections:
            return
        for collection_id, url in pairs:
            collection = (
                self.get_s3_or_http_collection(model)
                if collection_id == _COLLECTION_S3
                else collections.get(collection_id)
            )
            if collection is None:
                continue
            label = tree_shortcut_label(url)
            try:
                item = collection.add_path(label, str(url))
            except Exception as e:  # noqa: BLE001
                carb.log_warn(f"[SimReady] Failed to inject tree shortcut {url}: {e}")
                continue
            if item is None:
                continue
            self.injected_tree_items.append((model, collection, item))
            if hasattr(model, "_item_changed"):
                try:
                    model._item_changed(collection)
                except Exception:  # noqa: BLE001
                    pass

    def remove_tree_shortcuts(self) -> None:
        if not self.injected_tree_items:
            return
        for model, collection, item in self.injected_tree_items:
            name = getattr(item, "name", None)
            if not name:
                continue
            try:
                collection.del_child(name)
            except Exception as e:  # noqa: BLE001
                carb.log_warn(f"[SimReady] Failed to remove tree shortcut {name!r}: {e}")
                continue
            if hasattr(model, "_item_changed"):
                try:
                    model._item_changed(collection)
                except Exception:  # noqa: BLE001
                    pass
        self.injected_tree_items.clear()

    def remove_registered_s3_urls(self) -> None:
        """Remove only S3 connections that this extension registered."""
        for model, collection, item in self.registered_s3_items:
            name = getattr(item, "name", None)
            if not name:
                continue
            children = getattr(collection, "children", None) or {}
            if children.get(name) is not item:
                continue
            try:
                collection.del_child(name)
            except Exception as e:  # noqa: BLE001
                carb.log_warn(f"[SimReady] Failed to remove registered S3 URL {name!r}: {e}")
                continue
            if hasattr(model, "_item_changed"):
                try:
                    model._item_changed(collection)
                except Exception:  # noqa: BLE001
                    pass
        self.registered_s3_items.clear()

    def navigate_to_backend_default(self, backend) -> None:
        url = self.backend_default_tree_url(backend)
        if url is None:
            return
        if shortcut := self.find_injected_shortcut(url):
            filebrowser, _ = self.get_tree_filebrowser()
            if filebrowser is not None and hasattr(filebrowser, "select_and_center"):
                try:
                    filebrowser.select_and_center(shortcut)
                    return
                except Exception as e:  # noqa: BLE001
                    carb.log_warn(f"[SimReady] Failed to select shortcut for {url}: {e}")
        if browser := self._get_content_browser():
            try:
                browser.navigate_to(str(url))
            except Exception as e:  # noqa: BLE001
                carb.log_warn(f"[SimReady] Failed to navigate to {url}: {e}")

    def find_injected_shortcut(self, url: Url):
        target = str(url)
        for _model, _collection, item in self.injected_tree_items:
            if getattr(item, "path", None) == target:
                return item
        return None

    @staticmethod
    def backend_default_tree_url(backend) -> Url | None:
        if backend == SearchBackend.WORKSPACE_CACHE:
            return get_extension_config().default_wscache_s3_url
        if backend == SearchBackend.USD_SEARCH:
            return get_extension_config().default_usd_search_tree_root_url
        return None

    def clear_tree_filter(self):
        self.current_tree_filter = None
        self.remove_tree_shortcuts()
        filebrowser, model = self.get_tree_filebrowser()
        if model is None:
            return
        try:
            model.set_filter_fn(None)
        except Exception:  # noqa: BLE001
            pass
        self.restore_model_available_collections(model)
        if filebrowser is not None and hasattr(filebrowser, "refresh_ui"):
            try:
                filebrowser.refresh_ui()
            except Exception:  # noqa: BLE001
                pass

    def set_model_available_collections(self, model, allowed: list[str]) -> None:
        try:
            if self.original_available_collections is None:
                self.original_available_collections = list(model.available_collections or [])
            bookmark_collections = [
                collection_id
                for collection_id in self.original_available_collections
                if "bookmark" in str(collection_id).casefold()
            ]
            merged = list(dict.fromkeys([*allowed, *bookmark_collections]))
            model.available_collections = merged
        except Exception as e:  # noqa: BLE001
            carb.log_warn(f"[SimReady] Failed to narrow available_collections on {model!r}: {e}")

    def restore_model_available_collections(self, model) -> None:
        if self.original_available_collections is None:
            return
        try:
            model.available_collections = list(self.original_available_collections)
        except Exception as e:  # noqa: BLE001
            carb.log_warn(f"[SimReady] Failed to restore available_collections on {model!r}: {e}")

    def on_ui_ready(self, event, *, backend, tree_filter_active: bool) -> str | None:
        if not tree_filter_active:
            return None
        try:
            if event.payload["title"] != "Content":
                return None
        except Exception:  # noqa: BLE001
            return None
        return self.apply_tree_filter(backend)
