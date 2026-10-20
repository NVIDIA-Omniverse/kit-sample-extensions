"""Implement material graph extension logic for `context_manager/context_manager.py`."""

from typing import Callable, Dict, List, Optional

# pylint: disable=no-member
from pxr import Sdf, Usd, UsdShade, UsdUI

from ..commands.execution import execute_command
from ..config.logging import LogContext, context_suffix, get_logger
from ..plugins.core import Plugin as PluginBase
from ..plugins.core import PluginManager
from ..utils.sdr_wrappers import SdrRegistryWrapper, SdrShaderNodeWrapper
from ..validation.registry import clear_active_validator, set_active_validator
from ..validation.result import ValidationResult
from ..validation.validator import MaterialValidator
from .context import Context
from .context_handle import ContextHandle
from .context_plugin_access import ContextPluginAccess

logger = get_logger()


class ContextManager:
    """Manage material contexts and their plugins."""

    def __init__(self, usd_context: Optional[object]) -> None:
        """Initialize the context manager for a USD context."""
        self._last_error: Optional[str] = None
        # Dynamic boundary: tests and integration paths may pass arbitrary objects.
        if usd_context is None or not callable(getattr(usd_context, "get_stage", None)):
            logger.warning(
                "context manager initialization rejected invalid USD context: actual_type=%s",
                type(usd_context).__name__,
            )
            self._usd_context = None
            self._last_error = "Invalid USD context"
        else:
            self._usd_context = usd_context
        self._plugin_manager = PluginManager()
        self._plugin_access = ContextPluginAccess(self._plugin_manager)
        self._validator = MaterialValidator()
        set_active_validator(self._usd_context, self._validator)

        self._contexts: Dict[str, Context] = {}
        self._validation_results: Dict[str, ValidationResult] = {}
        self._root_prim: Optional[Usd.Prim] = None
        self._destroyed = False
        logger.debug("context manager initialized%s", context_suffix(LogContext(action="init")))

    def destroy(self) -> None:
        """Release contexts and plugin manager resources."""
        if self._destroyed:
            return
        logger.debug(
            "context manager destroy%s",
            context_suffix(LogContext(action="destroy"), file_path=f"contexts={len(self._contexts)}"),
        )
        self._destroyed = True
        for context in self._contexts.values():
            context.destroy()
        self._contexts = {}

        if self._plugin_manager:
            self._plugin_manager.destroy()
            self._plugin_manager = None
            self._plugin_access = None
        clear_active_validator(self._usd_context)
        self._usd_context = None
        self._root_prim = None
        self._validation_results = {}
        self._last_error = None
        self._validator = None

    def subscribe_validation(self, event_name: str, callback: Optional[Callable[..., None]]) -> Optional[int]:
        """Subscribe to validation events from the internal validator."""
        if not self._validator or not callback:
            return None
        return self._validator.subscribe(event_name, callback)

    def unsubscribe_validation(self, sub_id: int) -> None:
        """Unsubscribe a previously registered validation callback id."""
        if self._validator:
            self._validator.unsubscribe(sub_id)

    def get_plugins(self) -> List[PluginBase]:
        """Return all discovered plugins."""
        if not self._plugin_access:
            self._last_error = "Plugin access unavailable"
            logger.warning("get_plugins failed: %s", self._last_error)
            return []
        return self._plugin_access.get_plugins()

    def get_context_names(self) -> List[str]:
        """Return a list of available context names."""
        return list(self._contexts.keys())

    def get_context(self, context_name: str) -> ContextHandle:
        """Return the context handle for a name."""
        if self._destroyed or not self._plugin_access:
            self._last_error = "Context manager destroyed"
            return ContextHandle(None, None, context_name, error="Context manager destroyed")
        plugin = self._plugin_access.get_plugin(context_name)
        if not plugin:
            self._last_error = f"Missing plugin '{context_name}'"
            return ContextHandle(None, None, context_name, error=f"Missing plugin '{context_name}'")
        if not self._validate_root_or_invalidate():
            return ContextHandle(None, plugin, context_name, error=self._last_error)

        context = self._contexts.get(context_name)
        if not context and self._root_prim:
            context = self._create_context(context_name, plugin)
        if not context:
            return ContextHandle(None, plugin, context_name, error=self._last_error)
        return ContextHandle(context, plugin, context_name)

    def add_context(self, context_name: str) -> bool:
        """Create a context for the name if possible."""
        if not self._root_prim:
            message = "No root prim"
            logger.warning("add_context failed: %s context=%s", message, context_name)
            self._last_error = message
            return False
        if not self._validate_root_or_invalidate():
            message = self._last_error or "Root prim is no longer valid"
            logger.warning("add_context failed: %s context=%s", message, context_name)
            self._last_error = message
            return False

        if not self._root_prim.IsA(UsdShade.Material):
            message = "Root prim is not a Material"
            logger.warning(
                "add_context failed: %s context=%s root=%s",
                message,
                context_name,
                self._root_prim.GetPath(),
            )
            self._last_error = message
            return False

        if context_name in self._contexts:
            return True

        plugin = self._plugin_access.get_plugin(context_name)
        if not plugin:
            message = f"Missing plugin '{context_name}'"
            logger.warning("add_context failed: %s context=%s", message, context_name)
            self._last_error = message
            return False

        graph_context = self._create_context(context_name, plugin)
        if not graph_context:
            message = self._last_error or f"Context create failed '{context_name}'"
            logger.warning("add_context failed: %s context=%s", message, context_name)
            self._last_error = message
            return False

        logger.info(
            "context added '%s' on %s",
            context_name,
            self._root_prim.GetPath(),
        )
        return True

    def destroy_context(self, context_name: str) -> bool:
        """Destroy and forget a cached context if present, without authoring USD edits.

        Use this when a context must be rebuilt from scratch (e.g. after a
        MaterialX upgrade rewrote shader ids) so that the next
        :meth:`get_context` call constructs a fresh graph. Unlike
        :meth:`remove_context`, this never touches material outputs.
        Returns ``True`` if a context was destroyed, ``False`` otherwise.
        """
        context = self._contexts.pop(context_name, None)
        if context is None:
            return False
        context.destroy()
        # Drop any cached validation result for the destroyed context so
        # ``get_validation_result`` cannot return a pre-rebuild snapshot
        # before the next ``validate_context`` runs.
        self._validation_results.pop(context_name, None)
        return True

    def remove_context(self, context_name: str) -> bool:
        """Remove a context and its material outputs."""
        if context_name not in self._contexts:
            self._last_error = f"Missing context '{context_name}'"
            logger.warning("remove_context failed: %s", self._last_error)
            return False

        context = self._contexts[context_name]
        success, message = self._remove_context_outputs(context)
        if not success:
            self._last_error = message or f"Failed to remove outputs for '{context_name}'"
            logger.warning("remove_context failed: %s context=%s", self._last_error, context_name)
            return False
        context.destroy()
        del self._contexts[context_name]

        logger.info(
            "context removed '%s' from %s",
            context_name,
            self._root_prim.GetPath(),
        )
        return True

    def clear(self) -> None:
        """Clear all contexts and reset state."""
        logger.debug(
            "context manager clear%s",
            context_suffix(LogContext(action="clear"), file_path=f"contexts={len(self._contexts)}"),
        )
        for context in self._contexts.values():
            context.destroy()

        self._contexts = {}
        self._root_prim = None
        if self._validator:
            self._validator.set_root_prim(None)
        self._validation_results = {}
        self._last_error = None

    def load(self, path: Sdf.Path) -> bool:
        """Load the material at a prim path into context state."""
        if not self._usd_context:
            self._last_error = "Invalid USD context"
            logger.warning("material load failed for requested path %s: invalid USD context", path)
            return False
        stage = self._usd_context.get_stage()
        if not stage:
            logger.warning("material load failed for requested path %s: no USD stage is open", path)
            self._last_error = "No USD stage"
            return False
        new_root = self._resolve_material_prim(stage, path)
        if not new_root:
            self._last_error = f"Material prim not found at {path}"
            logger.warning("load failed: %s", self._last_error)
            return False

        if not UsdShade.Material(new_root):
            logger.warning(
                "load failed: root prim is not a Material root=%s",
                new_root.GetPath(),
            )
            self._last_error = "Root prim is not a Material"
            return False

        if self._root_prim and (new_root.GetPath() == self._root_prim.GetPath()):
            if not self._root_prim.IsValid():
                for context in self._contexts.values():
                    context.destroy()
                self._contexts = {}
                self._root_prim = new_root
                if self._validator:
                    self._validator.set_root_prim(new_root)
                self._validation_results = {}
                self._last_error = None
                logger.info("reloaded material %s", new_root.GetPath())
                return True
            return True

        for context in self._contexts.values():
            context.destroy()
        self._contexts = {}
        self._validation_results = {}
        self._root_prim = new_root
        if self._validator:
            self._validator.set_root_prim(new_root)
        self._last_error = None
        logger.info("loaded material %s", new_root.GetPath())
        return True

    def check_materialx_upgrade(self, context_name: str) -> None:
        """Run the MaterialX upgrade check for the given context.

        Called by ``ContextModelController.set_context`` when switching to a
        MaterialX context.  If the context already exists and changes are
        found, the context is destroyed so ``get_context`` will rebuild it.
        """
        if not self._root_prim or not self._plugin_access:
            return
        from ..plugins.impl.materialx.plugin import MaterialXPlugin

        plugin = self._plugin_access.get_plugin(context_name)
        if not plugin or not isinstance(plugin, MaterialXPlugin):
            return

        auto_upgrade = plugin.get_plugin_property("autoUpgradeNodes", True)
        self._run_materialx_upgrade_if_needed(self._root_prim, apply_changes=auto_upgrade)

        # If auto-upgrade applied changes and a context already exists,
        # destroy it so it gets rebuilt with updated models.
        if auto_upgrade and not plugin._pending_upgrade_changes and self._last_upgrade_had_changes:
            self.destroy_context(context_name)

    def _run_materialx_upgrade_if_needed(self, root_prim: Usd.Prim, apply_changes: bool = True) -> None:
        """Build a MaterialX document from the USD network with Python APIs,
        run upgradeVersion(), and optionally apply identifier fixes to the USD prims.

        When *apply_changes* is False the detected changes are stored on the
        plugin as ``_pending_upgrade_changes`` for the UI to present in a menu.
        """
        # Reset before any early-return so callers that consult the flag
        # (e.g. ``check_materialx_upgrade``) never see a stale ``True``
        # carried over from a previous invocation.
        self._last_upgrade_had_changes = False

        if not self._plugin_access:
            return
        from ..plugins.impl.materialx.plugin import MaterialXPlugin

        mtlx_plugin = None
        for plugin in self._plugin_access.get_plugins():
            if isinstance(plugin, MaterialXPlugin):
                mtlx_plugin = plugin
                break
        if mtlx_plugin is None:
            return

        try:
            from ..materialx_upgrade import upgrade_materialx_identifiers
        except ImportError as exc:
            logger.error(
                "[MaterialX Upgrade] check unavailable for material='%s' plugin='%s': Python support import failed: "
                "%s; no identifiers were changed",
                root_prim.GetPath(),
                mtlx_plugin.name,
                exc,
            )
            # Drop any prior pending list; without MaterialX support we can no
            # longer compute changes for the current material, and leaving
            # stale entries would let the UI offer (and ``apply_single_upgrade``
            # act on) prims from a previous material/stage.
            mtlx_plugin._pending_upgrade_changes = []
            return

        stage = root_prim.GetStage()
        if not stage:
            mtlx_plugin._pending_upgrade_changes = []
            return

        result = upgrade_materialx_identifiers(root_prim, mtlx_plugin.name)

        for diag in result.diagnostics:
            logger.info("[MaterialX Upgrade] %s", diag)

        if not result.any_changes:
            mtlx_plugin._pending_upgrade_changes = []
            return

        if apply_changes:
            if self._apply_upgrade_changes(result.changes, stage, mtlx_plugin):
                mtlx_plugin._pending_upgrade_changes = []
                self._last_upgrade_had_changes = True
            else:
                mtlx_plugin._pending_upgrade_changes = list(result.changes)
        else:
            mtlx_plugin._pending_upgrade_changes = list(result.changes)
            logger.info(
                "[MaterialX Upgrade] %d upgradeable node(s) stored for manual upgrade",
                len(result.changes),
            )

    def _apply_upgrade_changes(self, changes, stage, mtlx_plugin) -> bool:
        """Apply identifier changes transactionally and clear the shader cache on success."""
        resolved = []
        for change in changes:
            prim = stage.GetPrimAtPath(Sdf.Path(change.prim_path))
            if not prim or not prim.IsValid():
                logger.warning("[MaterialX Upgrade] Missing prim for %s", change.prim_path)
                return False
            api = UsdShade.NodeDefAPI(prim)
            if not api:
                logger.warning("[MaterialX Upgrade] Missing NodeDefAPI for %s", change.prim_path)
                return False
            resolved.append((change, api, api.GetShaderId()))

        applied = []
        try:
            for change, api, previous_identifier in resolved:
                if api.SetShaderId(change.new_identifier) is False:
                    raise RuntimeError(f"SetShaderId failed for {change.prim_path}")
                applied.append((change, api, previous_identifier))
                logger.info(
                    "[MaterialX Upgrade] Updated %s: %s -> %s",
                    change.prim_path,
                    change.old_identifier,
                    change.new_identifier,
                )
        except (RuntimeError, ValueError, TypeError) as exc:
            failed_change = change if "change" in locals() else None
            for applied_change, api, previous_identifier in reversed(applied):
                try:
                    api.SetShaderId(previous_identifier)
                except (RuntimeError, ValueError, TypeError) as rollback_exc:
                    logger.error(
                        "[MaterialX Upgrade] identifier rollback failed for prim='%s' previous_identifier='%s': %s; "
                        "the material may contain a partial upgrade",
                        applied_change.prim_path,
                        previous_identifier,
                        rollback_exc,
                    )
            logger.error(
                "[MaterialX Upgrade] upgrade failed at prim='%s' requested_identifier='%s': %s; "
                "applied identifiers were rolled back",
                getattr(failed_change, "prim_path", "<unknown>"),
                getattr(failed_change, "new_identifier", "<unknown>"),
                exc,
            )
            return False
        mtlx_plugin._shader_node_cache.clear()
        return True

    def apply_single_upgrade(self, change) -> bool:
        """Apply one pending upgrade change from the UI menu.

        Updates ``info:id`` on the prim, removes the change from the pending
        list, and destroys the mtlx context so it will be fully rebuilt with
        the new SDR node definitions on the next ``get_context("mtlx")``.
        """
        if not self._root_prim or not self._root_prim.IsValid():
            return False
        stage = None
        if self._usd_context:
            stage = self._usd_context.get_stage()
        if not stage:
            return False

        from ..plugins.impl.materialx.plugin import MaterialXPlugin

        mtlx_plugin = None
        if self._plugin_access:
            for plugin in self._plugin_access.get_plugins():
                if isinstance(plugin, MaterialXPlugin):
                    mtlx_plugin = plugin
                    break
        if not mtlx_plugin:
            return False

        prim = stage.GetPrimAtPath(Sdf.Path(change.prim_path))
        if not prim or not prim.IsValid():
            return False

        api = UsdShade.NodeDefAPI(prim)
        if not api:
            return False
        try:
            if api.SetShaderId(change.new_identifier) is False:
                return False
        except (RuntimeError, ValueError, TypeError) as exc:
            logger.error("[MaterialX Upgrade] Manual upgrade failed for %s: %s", change.prim_path, exc)
            return False
        logger.info(
            "[MaterialX Upgrade] Manual upgrade: %s: %s -> %s",
            change.prim_path,
            change.old_identifier,
            change.new_identifier,
        )

        # Remove from pending list
        mtlx_plugin._pending_upgrade_changes = [
            c for c in mtlx_plugin._pending_upgrade_changes if c.prim_path != change.prim_path
        ]

        mtlx_plugin._shader_node_cache.clear()
        # Drop the cached MaterialX context so the next ``get_context`` call
        # rebuilds it against the freshly-rewritten shader ids; otherwise the
        # UI keeps showing stale nodes/ports keyed off the old SDR entries.
        self.destroy_context(mtlx_plugin.name)
        return True

    def validate_context(self, context_name: str) -> ValidationResult:
        """Run validation for one context and cache the result."""
        if not self._root_prim or not self._root_prim.IsValid():
            result = ValidationResult.ok(context_name)
            self._validation_results[context_name] = result
            return result
        handle = self.get_context(context_name)
        if not handle.is_valid:
            result = ValidationResult.ok(context_name)
            self._validation_results[context_name] = result
            return result
        if not self._validator:
            result = ValidationResult.ok(context_name)
            self._validation_results[context_name] = result
            return result
        result = self._validator.validate(
            context_name,
            self._root_prim,
            handle.plugin,
            model=handle.context.model if handle.context else None,
        )
        self._validation_results[context_name] = result
        return result

    def get_validation_result(self, context_name: str) -> ValidationResult:
        """Return cached validation result for a context, or a default passing result."""
        return self._validation_results.get(context_name, ValidationResult.ok(context_name))

    def get_node(self, context: str, identifier: str) -> Optional[SdrShaderNodeWrapper]:
        """Return the SDR node for the identifier in the context."""
        plugin = self._plugin_access.get_plugin(context)

        if plugin:
            return plugin.get_node(identifier)
        message = f"Missing plugin '{context}'"
        self._last_error = message
        logger.warning("get_node failed: %s context=%s", message, context)
        return None

    def _create_context(self, context_name: str, plugin: PluginBase) -> Optional[Context]:
        """Create and register a context for the given plugin."""
        graph_context = Context.create_context(
            self._root_prim,
            context_name,
            self._usd_context,
            plugin,
            validator=self._validator,
        )
        if not graph_context:
            message = f"Context create failed '{context_name}'"
            logger.error("context create failed: %s root=%s", context_name, self._root_prim.GetPath())
            self._last_error = message
            return None
        self._contexts[context_name] = graph_context
        skip_activation_sync = getattr(graph_context.model, "skip_next_activation_sync", None)
        if callable(skip_activation_sync):
            skip_activation_sync()
        return graph_context

    def get_last_error(self) -> Optional[str]:
        """Return the last error message."""
        return self._last_error

    def _validate_root_or_invalidate(self) -> bool:
        """Validate the cached root prim and invalidate contexts if it changed.

        USD may return an expired/invalid prim object after prim removal; treat
        those as missing roots and clear cached contexts accordingly.
        """
        if not self._root_prim:
            self._last_error = "No root prim"
            logger.warning("material root validation failed: no material root is currently loaded")
            return False
        if not self._usd_context:
            logger.warning(
                "material root validation failed for %s: invalid USD context",
                self._root_prim.GetPath(),
            )
            self._invalidate_root("Invalid USD context")
            return False
        stage = self._usd_context.get_stage()
        if not stage:
            logger.warning(
                "material root validation failed for %s: no USD stage is open",
                self._root_prim.GetPath(),
            )
            self._invalidate_root("No USD stage")
            return False
        root_path = self._root_prim.GetPath()
        if not root_path:
            logger.warning("material root validation failed: cached root prim has no valid path")
            self._invalidate_root("Root prim is no longer valid")
            return False
        prim = stage.GetPrimAtPath(root_path)
        if not prim:
            logger.warning("root validation failed: root prim missing at %s", root_path)
            self._invalidate_root("Root prim is no longer valid")
            return False
        if not prim.IsValid():
            logger.warning("root validation failed: root prim invalid at %s", root_path)
            self._invalidate_root("Root prim is no longer valid")
            return False
        if not self._root_prim.IsValid() and prim.IsValid():
            for context in self._contexts.values():
                context.destroy()
            self._contexts = {}
            self._root_prim = prim
            return True
        if not prim.IsA(UsdShade.Material):
            logger.warning("root validation failed: root is not material at %s", root_path)
            self._invalidate_root("Root prim is not a Material")
            return False
        if prim != self._root_prim:
            for context in self._contexts.values():
                context.destroy()
            self._contexts = {}
            self._root_prim = prim
        return True

    def _invalidate_root(self, message: str) -> None:
        """Clear contexts and record a root validation error."""
        root_path = self._root_prim.GetPath() if self._root_prim else None
        logger.warning("root invalidated: %s root=%s", message, root_path)
        for context in self._contexts.values():
            context.destroy()
        self._contexts = {}
        self._root_prim = None
        if self._validator:
            self._validator.set_root_prim(None)
        self._validation_results = {}
        self._last_error = message

    def _remove_context_outputs(self, context: Optional[Context]) -> tuple[bool, Optional[str]]:
        """Remove bound material output attributes for a context."""
        if not context or not self._root_prim:
            logger.warning(
                "context output removal failed: context_present=%s material_root=%s",
                bool(context),
                self._root_prim.GetPath() if self._root_prim else "<missing>",
            )
            return False, "Missing context or root prim"
        plugin = context.plugin
        if not plugin:
            logger.warning(
                "context output removal failed for material %s: context plugin is unavailable",
                self._root_prim.GetPath(),
            )
            return False, "Missing context plugin"
        stage = self._root_prim.GetStage()
        edit_layer = stage.GetEditTarget().GetLayer() if stage else None
        if not edit_layer:
            logger.warning(
                "context output removal failed for material %s plugin=%s: no editable USD layer",
                self._root_prim.GetPath(),
                getattr(plugin, "name", type(plugin).__name__),
            )
            return False, "Missing edit layer"
        before_layer = Sdf.Layer.CreateAnonymous("material_graph_context_outputs_before.usda")
        before_layer.TransferContent(edit_layer)
        success = True
        error_message = None
        removed_paths = []
        # The registered transaction below owns the single undo item. Author
        # directly through the root prim so no nested Kit command can survive
        # a failed batch and the edit always targets the owning USD stage.
        for output_name in plugin.get_material_output_names():
            attr = self._root_prim.GetAttribute(output_name)
            if not attr:
                continue
            if self._remove_context_output(attr):
                removed_paths.append(attr.GetPath())
                continue
            success = False
            error_message = f"Failed to remove material output '{output_name}' on {self._root_prim.GetPath()}"
            logger.warning(
                "failed to remove material output '%s' on %s",
                output_name,
                self._root_prim.GetPath(),
            )
            break
        if not success:
            edit_layer.TransferContent(before_layer)
            if not all(self._root_prim.GetAttribute(path.name) for path in removed_paths):
                logger.error("failed to roll back partial context output removal on %s", self._root_prim.GetPath())
                error_message = f"{error_message}; rollback failed"
            return False, error_message
        if removed_paths:
            after_layer = Sdf.Layer.CreateAnonymous("material_graph_context_outputs_after.usda")
            after_layer.TransferContent(edit_layer)
            result = execute_command(
                "MaterialGraph_CommitLayerTransactionCommand",
                target_layer=edit_layer,
                before_layer=before_layer,
                after_layer=after_layer,
                already_applied=True,
            )
            if not result.success:
                edit_layer.TransferContent(before_layer)
                logger.warning("failed to commit context output removal on %s", self._root_prim.GetPath())
                return False, "Failed to commit context output removal"
        return success, error_message

    @staticmethod
    def _remove_context_output(attribute: Usd.Attribute) -> bool:
        """Remove one output directly from its owning prim."""
        prim = attribute.GetPrim() if attribute else None
        return bool(prim and prim.RemoveProperty(attribute.GetName()))

    def _resolve_material_prim(self, stage: Usd.Stage, path: Sdf.Path) -> Optional[Usd.Prim]:
        """Resolve a material prim from a path or bound material."""
        if not path:
            logger.warning("material load failed: requested path is invalid (%r)", path)
            return None
        current = path
        depth = 0
        while current:
            prim = stage.GetPrimAtPath(current)
            if prim:
                if prim.IsA(UsdShade.Material):
                    return prim
                if prim.IsA(UsdShade.NodeGraph) or prim.IsA(UsdShade.Shader) or prim.IsA(UsdUI.Backdrop):
                    current = current.GetParentPath()
                    depth += 1
                    continue
                api = UsdShade.MaterialBindingAPI(prim)
                if api:
                    mat = api.ComputeBoundMaterial()
                    if mat and mat[0]:
                        return mat[0].GetPrim()
            logger.warning("load failed: prim not found at %s", current)
            return None
        logger.warning("load failed: no material at %s", path)
        return None
