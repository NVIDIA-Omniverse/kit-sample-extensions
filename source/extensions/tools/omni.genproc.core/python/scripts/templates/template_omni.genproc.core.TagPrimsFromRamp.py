import omni.ramp
import omni.ui as ui
from omni.kit.property.usd.custom_layout_helper import CustomLayoutFrame, CustomLayoutGroup, CustomLayoutProperty
from omni.kit.property.usd.usd_model_base import UsdBase
from omni.kit.window.property.templates import HORIZONTAL_SPACING, LABEL_WIDTH


class CustomLayout:
    def __init__(self, compute_node_widget):
        # Enable template
        self.enable = True
        self.compute_node_widget = compute_node_widget
        self.compute_node_widget.get_bundles()  # ?

        self.scalar_attribs = []
        self.window_width_change_fn_set = False
        self.ramp_widget = None

    def apply(self, props):
        frame = CustomLayoutFrame(hide_extra=True)
        with frame:
            with CustomLayoutGroup("Parameters"):
                CustomLayoutProperty("inputs:rampPositionsName", "Ramp Positions Name")
                CustomLayoutProperty("inputs:rampValuesName", "Ramp Values Name")
                CustomLayoutProperty("inputs:rampInterpolationsName", "Ramp Interpolations Name")
                CustomLayoutProperty("inputs:rampTagsName", "Ramp Tags Name")
                CustomLayoutProperty(None, None, build_fn=self.ramp_build_fn)

        return frame.apply(props)

    def ramp_build_fn(self, *args):
        widget = self.compute_node_widget

        init_positions = [0, 1]
        init_keys = [0, 0]
        init_interpolations = [1, 1]
        default_range = [0, 1]

        with ui.VStack():
            ramp_interface = omni.ramp.acquire_interface()
            ramp_prim = widget.get_widget_prim()

            ui.Spacer(height=4)
            self.ramp_frame = ui.Frame()
            width = self.get_ramp_width(self.ramp_frame) * 3
            self.ramp_widget = omni.ramp.RampWidget(
                ramp_interface,
                self.ramp_frame,
                ramp_prim,
                width=width,
                label="tagRamp",
                attr_names=[
                    "inputs:rampPositions",
                    "inputs:rampValues",
                    "inputs:rampInterpolations",
                    "inputs:rampTags",
                ],
                default_keys=[init_positions, init_keys, init_interpolations],
                default_range=default_range,
                clamp_values=True,
            )
            ui.Spacer(height=4)
            self.width_changed_subscribe()

    def get_ramp_width(self, frame):
        computed_width = int(frame.computed_width)
        if computed_width <= 0:
            computed_width = 400
        return computed_width - 20 - LABEL_WIDTH - HORIZONTAL_SPACING

    def width_changed(self, window_width):
        if self.window_width_change == False:
            return
        if self.ramp_frame is not None and self.ramp_widget is not None:
            self.ramp_widget.width = self.get_ramp_width(self.ramp_frame)
            self.ramp_widget.update()

    def width_changed_subscribe(self):
        self.window = ui.Workspace.get_window("Property")
        self.window_width_change = True
        if not self.window_width_change_fn_set:
            self.window.set_width_changed_fn(self.width_changed)
            self.window_width_change_fn_set = True
