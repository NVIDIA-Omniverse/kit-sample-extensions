import carb
import omni.ui as ui
from omni.kit.waypoint.core import ViewportWaypoint, WaypointItem, WaypointItemEditWidget

from .style import EDIT_WINDOW_STYLES

THUMBNAIL_WIDTH = 160
THUMBNAIL_HEIGHT = 90


class WaypointEditWindow(ui.Window):  # pragma: no cover
    def __init__(self):
        self._edit_widget = None
        flags = (
            ui.WINDOW_FLAGS_NO_TITLE_BAR
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_DOCKING
            | ui.WINDOW_FLAGS_NO_CLOSE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
        )
        super().__init__("Edit Waypoint", flags=flags, padding_x=0, padding_y=0, visible=False)
        self.frame.set_style(EDIT_WINDOW_STYLES)

        self.set_visibility_changed_fn(self._on_visibility_changed)

    def destroy(self):
        if self._edit_widget:
            self._edit_widget.destroy()
        self.visible = False

    def show(self, item: WaypointItem, x_offset: float = 0, y_offset: float = 0) -> None:
        self._x_offset = x_offset
        self._y_offset = y_offset
        self._build_ui(item)
        self.visible = True

        self._update_position()

    def _on_visibility_changed(self, visible: bool) -> None:
        viewport = ui.Workspace.get_window("Viewport")
        if not viewport:
            carb.log_error("No viewport window to attach edit window!")
            return
        if visible:
            viewport.set_width_changed_fn(self._update_position)
        else:
            viewport.set_width_changed_fn(None)

    def _update_position(self, *args):
        viewport = ui.Workspace.get_window("Viewport")
        if not viewport:
            carb.log_error("No viewport window to attach edit window!")
            return

        self.position_x = viewport.position_x + viewport.width + self._x_offset - THUMBNAIL_WIDTH
        self.position_y = viewport.position_y + self._y_offset

    def _build_ui(self, item: WaypointItem):
        self.frame.clear()
        if self._edit_widget:
            self._edit_widget.destroy()

        with self.frame:
            with ui.ZStack():
                with ui.VStack(width=THUMBNAIL_WIDTH):
                    with ui.ZStack(height=THUMBNAIL_HEIGHT):
                        self._build_thumbnail(item)
                        self._edit_widget = WaypointItemEditWidget(item, on_edit_end_fn=self._on_edit_end)

                    ui.Label(
                        item.waypoint.name,
                        height=20,
                        word_wrap=True,
                        elided_text=True,
                        skip_draw_when_clipped=True,
                        alignment=ui.Alignment.CENTER_TOP,
                        style_type_name_override="GridView.Item",
                    )
                ui.Rectangle(style_type_name_override="GridView.Item.Selection").checked = True

    def _build_thumbnail(self, item: WaypointItem) -> None:
        if item.thumbnail_provider:
            ui.ImageWithProvider(
                item.thumbnail_provider,
                alignment=ui.Alignment.CENTER,
                fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                style_type_name_override="GridView.Image",
            )
        else:
            ui.Image(
                item.waypoint.thumbnail, fill_policy=ui.FillPolicy.STRETCH, style_type_name_override="GridView.Image"
            )

    def _on_edit_end(self, item: ViewportWaypoint):
        self.visible = False
