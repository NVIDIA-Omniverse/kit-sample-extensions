"""Texture-drop workflow helpers for creating shader nodes from dropped textures."""

import asyncio

import omni.kit.app
import omni.ui
from pxr import Gf, Sdf

from ....commands.wrappers.nodes import CreateShader

# pylint: disable=no-member
from ....config.logging import logger
from ....models.catalog.registries.texture.info import get_texture_info
from ....utils.async_utils import ensure_future_logged
from ...interaction.menu_utils import show_menu_at_cursor


class TextureDropHandler:
    """Handle texture drops and shader creation."""

    def __init__(self, widget: object, context_manager: object) -> None:
        """Initialize texture drop handling."""
        self._widget = widget
        self._context_manager = context_manager
        self._texture_menu = None
        self._menu_task: asyncio.Task | None = None

    def can_accept(self, file_path: str) -> bool:
        """Return True if the JSON payload is supported."""
        info = get_texture_info(file_path)
        if info is None:
            return False

        valid, _ = info
        return valid

    def _resolve_plugin_choices(self, channels: int):
        """Resolve texture shader creation choices for current context plugin."""
        handle = self._context_manager.get_context(self._widget.current_context)
        plugin = handle.plugin
        if not plugin:
            logger.warning(
                "texture drop unavailable: render context='%s' has no discovery plugin; no shader was created",
                self._widget.current_context,
            )
            return None, []
        create_fn = getattr(plugin, "create_texture", None)
        if not callable(create_fn):
            logger.warning(
                "texture drop unavailable: plugin='%s' for context='%s' does not implement texture-node creation",
                getattr(plugin, "name", type(plugin).__name__),
                self._widget.current_context,
            )
            return plugin, []
        choices = create_fn(channels) or []
        if not choices:
            logger.warning(
                "texture drop unavailable: plugin='%s' returned no shader choices for channels=%s context='%s'",
                getattr(plugin, "name", type(plugin).__name__),
                channels,
                self._widget.current_context,
            )
        return plugin, choices

    def _create_choice_callback(self, plugin: object, event: omni.ui.WidgetMouseDropEvent):
        """Create closure that instantiates one chosen texture shader variant."""

        def create_choice(choice: object, path: str) -> None:
            """Create a texture shader choice and set its file input."""
            shader_item = choice[0]
            attr_name = choice[1]
            identifier = shader_item.identifier
            if not identifier:
                logger.warning(
                    "texture info: shader choice missing identifier context=%s", self._widget.current_context
                )
                self._widget.show_error("texture shader definition is missing an identifier", log_message=False)
                return
            isolation_model = self._widget.isolation_model
            model = isolation_model.root if isolation_model else None
            if not model:
                self._widget.show_error(
                    "texture drop ignored: no material graph is loaded; open or create a material and try again"
                )
                return
            sdr_node = self._context_manager.get_node(self._widget.current_context, identifier)
            if not sdr_node:
                logger.warning("texture info: unknown shader %s context=%s", identifier, self._widget.current_context)
                self._widget.show_error(f"texture shader definition not found ({identifier})", log_message=False)
                return
            graph_view = self._widget.graph_view
            position = Gf.Vec2f(graph_view.screen_to_canvas(event.x, event.y))
            try:
                extra = dict(shader_item.extra_mime_data or {})
            except (TypeError, ValueError):
                logger.warning("texture info: shader choice has invalid creation metadata identifier=%s", identifier)
                self._widget.show_error("texture shader definition has invalid creation metadata", log_message=False)
                return
            if "context" not in extra:
                extra["context"] = plugin.get_shader_source_type() if plugin else None
            extra["input_values"] = {
                attr_name: (Sdf.ValueTypeNames.Asset, Sdf.AssetPath(path)),
            }
            prim = getattr(model, "prim", None)
            stage = prim.GetStage() if prim and callable(getattr(prim, "GetStage", None)) else None
            extra["stage"] = stage
            result = CreateShader(model.prim_path, sdr_node, position, **extra)
            if not result.success or not result.payload:
                message = result.message or "texture shader creation failed"
                logger.warning(
                    "texture drop failed path='%s' shader='%s' parent='%s' context='%s': %s; no shader was created",
                    path,
                    identifier,
                    model.prim_path,
                    self._widget.current_context,
                    getattr(result, "error_code", None) or message,
                )
                self._widget.show_error(
                    f"texture shader '{identifier}' could not be created: {message}",
                    log_message=False,
                )
                return
            self._widget.clear_error()

        return create_choice

    def _show_choices_menu(
        self, choices: list[object], create_choice: object, file_path: str, event: omni.ui.WidgetMouseDropEvent
    ) -> None:
        """Show multi-choice texture menu and schedule display."""
        if self._texture_menu:
            self._texture_menu.hide()
        menu = omni.ui.Menu("Texture shader")
        self._texture_menu = menu
        with menu:
            for choice in choices:
                shader_item = choice[0]
                label = shader_item.name or shader_item.identifier or "Texture"
                omni.ui.MenuItem(label, triggered_fn=lambda c=choice: create_choice(c, file_path))

        async def _show_menu_async() -> None:
            """Show the texture choice menu on next update."""
            await omni.kit.app.get_app().next_update_async()
            if self._texture_menu is menu:
                show_menu_at_cursor(menu, (event.x or 0, event.y or 0))

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # Drag/drop callbacks can run outside asyncio loop ownership.
            # Fall back to immediate menu display so texture selection still works.
            show_menu_at_cursor(menu, (event.x or 0, event.y or 0))
            return

        if self._menu_task and not self._menu_task.done():
            self._menu_task.cancel()
        self._menu_task = ensure_future_logged(_show_menu_async(), "texture menu show")
        if self._menu_task is None:
            show_menu_at_cursor(menu, (event.x or 0, event.y or 0))

    def handle_drop(self, file_path: str, event: omni.ui.WidgetMouseDropEvent) -> bool:
        """Handle a texture file drop and return True if processed."""
        info = get_texture_info(file_path)
        if info is None:
            return True

        valid, channels = info
        logger.info(
            "texture info: path=%s valid=%s channels=%s context=%s",
            file_path,
            valid,
            channels,
            self._widget.current_context,
        )
        if not valid:
            logger.warning(
                "texture drop ignored: file is missing, unreadable, or not a supported texture path='%s'",
                file_path,
            )
            return True

        plugin, choices = self._resolve_plugin_choices(channels)
        if not choices:
            return True

        create_choice = self._create_choice_callback(plugin, event)

        if len(choices) == 1:
            create_choice(choices[0], file_path)
            return True

        self._show_choices_menu(choices, create_choice, file_path, event)
        return True

    def destroy(self) -> None:
        """Release handler subscriptions and temporary resources created for drop processing."""
        if self._menu_task and not self._menu_task.done():
            self._menu_task.cancel()
        if self._texture_menu:
            self._texture_menu.hide()
        self._menu_task = None
        self._widget = None
        self._context_manager = None
        self._texture_menu = None
