import omni.ui as ui
from omni.kit.viewport.menubar.core import ViewportMenuItem


class ViewportNavigationSeparator(ViewportMenuItem):
    """A simple separator"""

    def build_fn(self, factory):
        style = {"Line::separator": {"color": 0xFF9E9E9E}}
        with ui.HStack(width=0):
            ui.Spacer(width=8)
            with ui.VStack():
                ui.Spacer(height=ui.Percent(10))
                # OM-70677: total tall is 56px, so the line's tall is 56 * (1- 0.1 -0.1) nearly 45
                ui.Line(width=0, height=45, name="separator", alignment=ui.Alignment.H_CENTER, style=style)
                ui.Spacer(height=ui.Percent(10))
            ui.Spacer(width=8)

    # OM-70677 total space between section is leftspace + width + rightspace = 4+17+4 = 25
    @property
    def width(self):
        return 17
