"""Implement material graph extension logic for `plugins/core/base.py`."""

import ast
import asyncio
import bisect
import os
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import omni.UsdMdl
from pxr import Sdf, Sdr, Usd, UsdShade

from ...config.color import string_to_random_abgr
from ...config.logging import LogContext, context_suffix, get_logger
from ...config.paths import Paths
from ...models.catalog.items import GroupItem, ShaderItem
from ...models.catalog.registries.icon_registry import clear_context as clear_catalog_icon_context
from ...models.catalog.registries.icon_registry import register as cache_catalog_icon
from ...settings.settings import Settings
from ...utils.lifecycle_registry import LifecycleRegistry
from ...utils.sdr_wrappers import SdrRegistryWrapper, wrap_shader_node
from ...validation.issue import ValidationIssue
from .polymorphic_state import PolymorphicState
from .properties_base import PluginPropertiesBase
from .property import PluginProperty

# pylint: disable=no-member

logger = get_logger()


class Plugin(ABC):
    """Base class for material graph plugins."""

    class RenderTypeMatch(Enum):
        """Represent column behavior for the material graph extension."""

        UNKNOWN = -1
        NO_MATCH = 0
        MATCH = 1

    def __init__(
        self,
        context_name: str,
        display_name: Optional[str] = None,
        properties: Optional[PluginPropertiesBase] = None,
        load_catalog: bool = True,
    ) -> None:
        """Initialize instance state for this material graph component."""

        self._catalog_items = []
        self._texture_shaders: Dict[int, List[Any]] = {}
        self._catalog_build_id = 0
        self._on_reload_cb: Optional[Callable[[], None]] = None
        self._catalog_task: Optional[asyncio.Task] = None
        self._catalog_reload_pending = False
        self._plugin_name = context_name
        self._display_name = display_name
        self._properties = properties
        self._lifecycle = LifecycleRegistry()
        self._destroyed = False
        self._shader_node_cache: Dict[Tuple[str, str], Any] = {}
        self._setup_properties()
        logger.debug(
            "plugin initialized%s",
            context_suffix(
                LogContext(plugin_name=context_name, action="init"), file_path=f"load_catalog={load_catalog}"
            ),
        )
        if load_catalog:
            self._load_catalog()

    def destroy(self) -> None:
        """Execute destroy behavior for material graph workflows."""

        self._destroyed = True
        if self._catalog_task and not self._catalog_task.done():
            self._catalog_task.cancel()
        self._lifecycle.cleanup()
        self._lifecycle = None
        self._teardown_properties()
        self._catalog_task = None
        self._on_reload_cb = None
        self._shader_node_cache.clear()

    def _load_catalog(self) -> None:
        """Execute load catalog behavior for material graph workflows."""

        logger.debug(
            "catalog load requested%s",
            context_suffix(LogContext(plugin_name=self._plugin_name, action="catalog_load")),
        )

        async def build_catalog_async() -> None:
            """Asynchronously execute build catalog async behavior for material graph workflows."""

            if self._destroyed:
                return
            self._catalog_items.clear()
            self._texture_shaders.clear()

            self._safe_build_catalog_items()
            if self._on_reload_cb and not self._destroyed:
                self._on_reload_cb()

        if self._destroyed:
            return
        if self._catalog_task and not self._catalog_task.done():
            self._catalog_reload_pending = True
            logger.debug(
                "catalog load queued%s",
                context_suffix(LogContext(plugin_name=self._plugin_name, action="catalog_queue")),
            )
            return

        self._catalog_task = self._lifecycle.add_task(build_catalog_async(), label="catalog build")
        if self._catalog_task:
            self._catalog_task.add_done_callback(self._on_catalog_task_done)

    def _on_catalog_task_done(self, _task: asyncio.Task) -> None:
        """Execute on catalog task done behavior for material graph workflows."""

        if self._destroyed:
            return
        try:
            _task.result()
        except asyncio.CancelledError:
            return
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.warning("catalog task failed (%s): %s", self._plugin_name, exc)
        if _task is self._catalog_task:
            self._catalog_task = None
        if not self._catalog_reload_pending:
            return
        self._catalog_reload_pending = False
        self._load_catalog()

    def _next_catalog_context_id(self) -> str:
        """Execute next catalog context id behavior for material graph workflows."""

        self._catalog_build_id += 1
        return f"{self._plugin_name}:{self._catalog_build_id}"

    def reload(self) -> None:
        """Execute reload behavior for material graph workflows."""

        if self._destroyed:
            return
        logger.debug("catalog reload%s", context_suffix(LogContext(plugin_name=self._plugin_name, action="reload")))
        if self._catalog_task and not self._catalog_task.done():
            self._catalog_reload_pending = True
            return
        self._load_catalog()

    def _safe_build_catalog_items(self) -> None:
        """Execute safe build catalog items behavior for material graph workflows."""

        if self._destroyed:
            return
        try:
            clear_catalog_icon_context(self._plugin_name)
            self._catalog_items.clear()
            self._texture_shaders.clear()
            self._shader_node_cache.clear()
            self.build_catalog_items()
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.warning("plugin catalog build failed (%s): %s", self._plugin_name, exc)
            self._catalog_items.clear()

    def compare_render_types(self, source_model: Any, target_model: Any) -> RenderTypeMatch:
        source = source_model.proxy_attribute
        target = target_model.proxy_attribute

        if not (source.render_type and target.render_type):
            return self.RenderTypeMatch.UNKNOWN

        if source.render_type == target.render_type:
            return self.RenderTypeMatch.MATCH

        return self.RenderTypeMatch.NO_MATCH

    def compare_types(self, source_model: Any, target_model: Any) -> bool:
        source = source_model.proxy_attribute
        target = target_model.proxy_attribute

        if source.type_name == target.type_name:
            return True

        def _find_value_type(value: Any) -> Any:
            if value is None:
                return None
            # ValueTypeNames.Find expects a token string, not ValueTypeName objects.
            if isinstance(value, Sdf.ValueTypeName):
                value = str(value)
            return Sdf.ValueTypeNames.Find(str(value))

        # compare underlying C++ type or role
        source_value_type = _find_value_type(source.type_name)
        target_value_type = _find_value_type(target.type_name)

        if source_value_type and target_value_type:
            return source_value_type.type == target_value_type.type

        return False

    def can_connect(self, source_model: Any, target_model: Any) -> bool:
        """Return True if a connection can be created between the two models."""

        if Settings.get_force_connect():
            return True

        src_proxy = getattr(source_model, "proxy_attribute", None)
        tgt_proxy = getattr(target_model, "proxy_attribute", None)
        src_ifo = getattr(src_proxy, "connectability", None) == UsdShade.Tokens.interfaceOnly
        tgt_ifo = getattr(tgt_proxy, "connectability", None) == UsdShade.Tokens.interfaceOnly
        if src_ifo or tgt_ifo:

            def _is_interface_port(model):
                """True if port is on an IO node OR on the material root prim."""
                proxy = getattr(model, "proxy_attribute", None)
                if bool(getattr(proxy, "owner_is_interface", False)):
                    return True
                parent = getattr(model, "parent", None)
                if parent is not None and hasattr(parent, "source"):
                    return True
                # container-prim ports: the port's prim is a NodeGraph
                try:
                    prim = getattr(model, "prim", None)
                    if prim and prim.IsA(UsdShade.NodeGraph):
                        return True
                except Exception:
                    pass
                return False

            if src_ifo and not _is_interface_port(target_model):
                return False
            if tgt_ifo and not _is_interface_port(source_model):
                return False

        match = self.compare_render_types(source_model, target_model)
        if match != self.RenderTypeMatch.UNKNOWN:
            return match == self.RenderTypeMatch.MATCH

        return self.compare_types(source_model, target_model)

    def can_connect_polymorphic_models(self, source_model: object, target_model: object) -> bool:
        """Return True when a plugin allows tentative polymorphic connections."""
        return False

    def resolve_polymorphic_overload_for_prim(self, prim: Optional[Usd.Prim]) -> bool:
        """Resolve and apply polymorphic overload for a prim if supported."""
        return False

    def resolve_polymorphic_overload_for_connection(self, source_model: object, target_model: object) -> bool:
        """Resolve polymorphic overload(s) from a concrete connection pair."""
        return False

    def get_polymorphic_state_for_prim(self, prim: Optional[Usd.Prim]) -> PolymorphicState:
        """Return plugin-specific polymorphic state for a prim."""
        return PolymorphicState()

    def get_validation_issues(self, context_name: str, root_prim: Optional[Usd.Prim]) -> List[ValidationIssue]:
        """Return plugin-specific validation issues for one context/material."""
        return []

    @property
    def name(self) -> str:
        """Execute name behavior for material graph workflows."""

        return self._plugin_name

    @property
    def display_name(self) -> Optional[str]:
        """Execute display name behavior for material graph workflows."""

        return self._display_name

    @property
    def Paths(self):  # noqa: N802
        """Execute paths behavior for material graph workflows."""

        return Paths

    @property
    def Settings(self):  # noqa: N802
        """Execute settings behavior for material graph workflows."""

        return Settings

    @property
    def GroupItem(self):  # noqa: N802
        """Execute group item behavior for material graph workflows."""

        return GroupItem

    @property
    def ShaderItem(self):  # noqa: N802
        """Execute shader item behavior for material graph workflows."""

        return ShaderItem

    @property
    def properties(self) -> List[PluginProperty]:
        """Execute properties behavior for material graph workflows."""

        if self._properties:
            return list(self._properties.list())
        return []

    @property
    def context_name(self) -> str:
        """Execute context name behavior for material graph workflows."""

        return self._plugin_name

    def get_catalog_items(self) -> List[Any]:
        """Execute get catalog items behavior for material graph workflows."""

        return self._catalog_items

    def build_port_names(self, port_names: Iterable[str]) -> List[str]:
        """Execute build port names behavior for material graph workflows."""

        return [
            f"{UsdShade.Tokens.outputs}{self.context_name}{Sdf.Path.namespaceDelimiter}{port_name}"
            for port_name in port_names
        ]

    def get_material_output_names(self) -> List[str]:
        """Execute get material output names behavior for material graph workflows."""

        base_default = [UsdShade.Tokens.displacement, UsdShade.Tokens.surface, UsdShade.Tokens.volume]
        default = base_default
        for prop in self.properties:
            if prop.key == "outputPorts" and isinstance(prop.default, list):
                default = prop.default
                break
        port_names = self.get_plugin_property("outputPorts", default)
        if not isinstance(port_names, list):
            port_names = default
        port_names = [str(item) for item in port_names if item]
        if default is not base_default and port_names == [str(item) for item in base_default]:
            port_names = [str(item) for item in default if item]
        return self.build_port_names(port_names)

    def get_shader_source_type(self) -> str:
        """Execute get shader source type behavior for material graph workflows."""

        return self._plugin_name

    @staticmethod
    def _shader_node_cache_key(prim: Any, plugin_name: str) -> Optional[Tuple[str, str]]:
        """Return a cacheable key: ``info:id`` token, or MDL ``sourceAsset`` + ``subIdentifier``."""
        try:
            shader = UsdShade.Shader(prim)
            if not shader:
                return None
            sid = shader.GetShaderId()
            if sid:
                text = str(sid).strip()
                if text:
                    return (plugin_name, f"id:{text}")
            if shader.GetImplementationSource() == UsdShade.Tokens.sourceAsset:
                asset_attr = prim.GetAttribute("info:mdl:sourceAsset")
                sub_attr = prim.GetAttribute("info:mdl:sourceAsset:subIdentifier")
                if asset_attr and sub_attr and asset_attr.HasAuthoredValue() and sub_attr.HasAuthoredValue():
                    asset_v = asset_attr.Get()
                    sub_v = sub_attr.Get()
                    if asset_v is not None and sub_v is not None:
                        sub_text = str(sub_v).strip()
                        if sub_text:
                            return (plugin_name, f"mdl:{str(asset_v)}::{sub_text}")
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return None
        return None

    def get_shader_node_for_prim(self, prim: Any) -> Optional[Any]:
        """Execute get shader node for prim behavior for material graph workflows."""

        if not prim:
            return None
        key = self._shader_node_cache_key(prim, self._plugin_name)
        if key is not None and key in self._shader_node_cache:
            return self._shader_node_cache[key]
        try:
            api = UsdShade.NodeDefAPI(prim)
            if not api:
                return None
            node = wrap_shader_node(api.GetShaderNodeForSourceType(self.get_shader_source_type()))
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.debug("shader definition lookup failed for %s: %s", prim.GetPath(), exc)
            return None
        if key is not None and node is not None:
            self._shader_node_cache[key] = node
        return node

    @abstractmethod
    def build_catalog_items(self) -> None:
        """Execute build catalog items behavior for material graph workflows."""

        raise NotImplementedError()

    def set_reload_callback(self, cb: Optional[Callable[[], None]]) -> None:
        """Execute set reload callback behavior for material graph workflows."""

        self._on_reload_cb = cb

    def _setup_properties(self) -> None:
        """Execute setup properties behavior for material graph workflows."""

        Settings.set_plugin_property_schema(self.name, self.properties)
        for prop in self.properties:
            existing = Settings.get_plugin_property(self.name, prop.key, None)
            if existing is None:
                Settings.set_plugin_property(self.name, prop.key, prop.default)

    def _teardown_properties(self) -> None:
        """Remove plugin property schema during teardown."""
        Settings.clear_plugin_property_schema(self.name)

    def get_plugin_property(self, key: str, default: Any = None) -> Any:
        """Execute get plugin property behavior for material graph workflows."""

        return Settings.get_plugin_property(self.name, key, default)

    def set_plugin_property(self, key: str, value: Any) -> None:
        """Execute set plugin property behavior for material graph workflows."""

        Settings.set_plugin_property(self.name, key, value)

    @abstractmethod
    def is_supported_prim(self, prim: Any) -> bool:
        """Execute is supported prim behavior for material graph workflows."""

        raise NotImplementedError()

    def get_node(self, identifier: str) -> Optional[Any]:
        """Execute get node behavior for material graph workflows."""
        return SdrRegistryWrapper().GetShaderNodeByIdentifier(identifier)

    def get_style(self) -> Dict[str, Dict[str, str]]:
        """Execute get style behavior for material graph workflows."""

        return {
            "Graph.Node.Icon": {"image_url": f"{Paths.ICON_PATH}/type_function_noBorder_dark.svg"},
        }

    def create_texture(self, channels: int) -> List[Any]:  # noqa: ARG002
        """Execute create texture behavior for material graph workflows."""

        def find_equal_or_next(values: List[int], x: int) -> int:
            """Execute find equal or next behavior for material graph workflows."""

            values.sort()
            idx = bisect.bisect_left(values, x)
            return values[idx] if idx < len(values) else values[-1]

        if self._texture_shaders:
            key = find_equal_or_next(list(self._texture_shaders.keys()), channels)
            return self._texture_shaders[key]

        return []

    def _get_icon(self, identifier: str, annotations: dict, base_uri: Path, family: str) -> Tuple[str, int]:
        """Execute get icon behavior for material graph workflows."""

        annotation = annotations.get("thumbnail", {})
        annotation = annotation if isinstance(annotation, dict) else {}
        name = annotation.get("name", None)
        if name:
            thumb_path = str(base_uri.joinpath(Path(name)))
            if os.path.exists(thumb_path):
                icon_color = 0xFFFFFFFF
                cache_catalog_icon(self._plugin_name, identifier, thumb_path, icon_color)
                return (thumb_path, icon_color)

        annotation = annotations.get("icon", {})
        annotation = annotation if isinstance(annotation, dict) else {}
        path = annotation.get("path", None)
        if path:
            icon_path = str(base_uri.joinpath(Path(path)))
            if os.path.exists(icon_path):
                icon_color = string_to_random_abgr(family.split(":")[0])
                cache_catalog_icon(self._plugin_name, identifier, icon_path, icon_color)
                return (icon_path, icon_color)

        return ("", 0x00000000)

    def _get_catalog_excluded_annotations(self) -> tuple[str, ...]:
        """Return annotation keys that should exclude a shader from catalog."""
        return ("deprecated", "hidden")

    def _should_skip_catalog_shader(self, annotations: dict[str, object]) -> bool:
        """Return True when shader annotations indicate catalog exclusion."""
        for key in self._get_catalog_excluded_annotations():
            if key and annotations.get(key):
                return True
        return False

    def _create_shader_item(self, name: str, sdr_node: Any) -> Optional[ShaderItem]:
        """Execute create shader item behavior for material graph workflows."""

        metadata = sdr_node.GetMetadata()
        identifier = sdr_node.GetIdentifier()

        raw_annotations = metadata.get(omni.UsdMdl.Metadata.Annotation, "{}")
        try:
            annotations = ast.literal_eval(raw_annotations) if isinstance(raw_annotations, str) else raw_annotations
        except (SyntaxError, ValueError, TypeError) as exc:
            logger.warning(
                "invalid MDL annotation metadata; ignoring annotations plugin=%s shader=%s reason=%s",
                self._plugin_name,
                identifier,
                exc,
            )
            annotations = {}
        if not isinstance(annotations, dict):
            logger.warning(
                "invalid MDL annotation metadata type; ignoring annotations plugin=%s shader=%s actual_type=%s",
                self._plugin_name,
                identifier,
                type(annotations).__name__,
            )
            annotations = {}

        if self._should_skip_catalog_shader(annotations):
            return None

        doc = sdr_node.GetHelp()
        family = metadata.get(Sdr.PropertyMetadata.Page, "unclassified")

        impl_uri = Path(sdr_node.GetResolvedImplementationURI())
        parent_path = impl_uri.parent
        icon, icon_color = self._get_icon(identifier, annotations, parent_path, family)

        ui_order = annotations.get("ui_order", {})
        ui_order = ui_order.get("order", None) if isinstance(ui_order, dict) else None

        shader_item = ShaderItem(
            name,
            self._plugin_name,
            sdr_node.GetIdentifier(),
            info=doc,
            tooltip=doc,
            family=family,
            icon=icon,
            icon_color=icon_color,
            ui_order=ui_order,
            tags=annotations.get("key_words", None),
        )

        return shader_item
