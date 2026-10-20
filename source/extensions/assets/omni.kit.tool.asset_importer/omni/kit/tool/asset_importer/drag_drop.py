import asyncio
import re
from typing import Iterable, List, Optional

import carb


class AssetImporterDragDropSupport:
    """Registers drag/drop entrypoints without requiring stage or viewport extensions."""

    def __init__(self, importer_ext):
        self._importer_ext = importer_ext
        self._stage_drop_subscription = None
        self._viewport_external_drop = None

        self._register_stage_drop()
        self._register_viewport_drop()

    def destroy(self):
        self._stage_drop_subscription = None

        if self._viewport_external_drop:
            self._viewport_external_drop.destroy()
            self._viewport_external_drop = None

        self._importer_ext = None

    def _register_stage_drop(self):
        try:
            from omni.kit.widget.stage import DragAndDropRegistry
        except ImportError:
            return

        registry = DragAndDropRegistry()
        register_drop_handler = getattr(registry, "register_drop_handler", None)
        if not register_drop_handler:
            carb.log_warn("Stage DragAndDropRegistry does not expose register_drop_handler.")
            return

        self._stage_drop_subscription = register_drop_handler(
            "asset_importer",
            self._accept_stage_drop,
            self._drop_stage,
        )

    def _register_viewport_drop(self):
        try:
            from omni.kit.window.drop_support import ExternalDragDrop
        except ImportError:
            return

        self._viewport_external_drop = ExternalDragDrop("Viewport", self._drop_viewport_external)
        self._ignore_default_viewport_drop_extensions()

    def _accept_stage_drop(self, *args, **kwargs):
        del kwargs
        return bool(self._get_supported_paths(args))

    def _drop_stage(self, *args, **kwargs):
        del kwargs
        paths = self._get_supported_paths(args)
        if not paths:
            return False

        parent_path = self._get_stage_target_path(args)
        self._schedule_import(paths, parent_path=parent_path)
        return True

    def _drop_viewport_external(self, external_drag_drop, dropped_paths):
        paths = dropped_paths
        expand_payload = getattr(external_drag_drop, "expand_payload", None)
        if expand_payload:
            paths = expand_payload(dropped_paths)

        paths = self._get_supported_paths(paths)
        if paths:
            self._schedule_import(paths)

    def _schedule_import(self, paths: List[str], parent_path=None):
        asyncio.ensure_future(
            self._importer_ext._import_paths_async(
                paths, add_reference=True, parent_path=parent_path, use_default_options=True
            )
        )

    def _get_supported_paths(self, values) -> List[str]:
        return [path for path in self._iter_paths(values) if self._importer_ext.is_supported_format(path)]

    def _iter_paths(self, values) -> Iterable[str]:
        if isinstance(values, str):
            yield values
            return

        if isinstance(values, (list, tuple, set)):
            for value in values:
                yield from self._iter_paths(value)
            return

        path = self._get_path_value(values)
        if path:
            yield path

    def _get_path_value(self, value) -> Optional[str]:
        if not value:
            return None

        for attr in ("path", "url", "source_url"):
            path = getattr(value, attr, None)
            if isinstance(path, str):
                return path

        for method_name in ("get_path", "get_url"):
            method = getattr(value, method_name, None)
            if not method:
                continue
            try:
                path = method()
            except Exception:
                continue
            if isinstance(path, str):
                return path

        return None

    def _get_stage_target_path(self, values):
        for value in values:
            path = self._get_path_value(value)
            if path and path.startswith("/") and not self._importer_ext.is_supported_format(path):
                return path

            prim = getattr(value, "prim", None)
            if prim:
                return prim.GetPath()

        return None

    def _ignore_default_viewport_drop_extensions(self):
        scene_drop_delegate = self._get_scene_drop_delegate()
        add_ignored_extension = getattr(scene_drop_delegate, "add_ignored_extension", None)
        if not add_ignored_extension:
            return

        for extension in self._get_supported_extensions():
            try:
                add_ignored_extension(extension)
            except Exception as e:
                carb.log_warn(f"Failed to ignore default viewport drop for '{extension}': {e}")

    def _get_scene_drop_delegate(self):
        try:
            from omni.kit.viewport.window import SceneDropDelegate
        except ImportError:
            return None

        return SceneDropDelegate

    def _get_supported_extensions(self):
        filters, _ = self._importer_ext._importers_manager.get_all_filters()
        extensions = set()
        for filter_regex in filters:
            for extension in re.findall(r"\\\.([A-Za-z0-9_]+)", filter_regex):
                extensions.add("." + extension.lower())

        for extension in extensions:
            if extension not in {".usd", ".usda", ".usdc", ".usdz"}:
                yield extension
