import omni.ramp
import omni.ui as ui
from omni.kit.property.usd.custom_layout_helper import CustomLayoutFrame, CustomLayoutGroup, CustomLayoutProperty
from omni.kit.window.property.templates import HORIZONTAL_SPACING, LABEL_WIDTH


class CustomLayout:
    def __init__(self, compute_node_widget):
        # Enable template
        self.enable = True
        self.compute_node_widget = compute_node_widget
        self.compute_node_widget.get_bundles()  # ?

        self.window_width_change_fn_set = False
        self.weights_ramp_widget = None
        self.object_indices_ramp_widget = None

    def apply(self, props):
        frame = CustomLayoutFrame(hide_extra=True)
        with frame:
            with CustomLayoutGroup("Ramps"):
                CustomLayoutProperty("inputs:weightsRampPositions", "Scatter Weights Ramp Positions")
                CustomLayoutProperty("inputs:weightsRampValues", "Scatter Weights Ramp Values")
                CustomLayoutProperty("inputs:weightsRampInterpolations", "Scatter Weights Ramp Interpolations")
                CustomLayoutProperty("inputs:objectIndicesRampPositions", "Object Indices Ramp Positions")
                CustomLayoutProperty("inputs:objectIndicesRampValues", "Object Indices Ramp Values")
                CustomLayoutProperty("inputs:objectIndicesRampInterpolations", "Object Indices Ramp Interpolations")
                CustomLayoutProperty("inputs:objectIndicesRampTags", "Object Indices Ramp Tags")
                CustomLayoutProperty(None, None, build_fn=self.weights_ramp_build_fn)

        return frame.apply(props)

    def weights_ramp_build_fn(self, *args):
        widget = self.compute_node_widget

        with ui.VStack():
            ramp_interface = omni.ramp.acquire_interface()
            ramp_prim = widget.get_widget_prim()

            ui.Spacer(height=4)
            self.weights_ramp_frame = ui.Frame()
            width = self.get_ramp_width(self.weights_ramp_frame) * 3
            self.weights_ramp_widget = omni.ramp.RampWidget(
                ramp_interface,
                self.weights_ramp_frame,
                ramp_prim,
                width=width,
                label="weights ramp",
                attr_names=[
                    "inputs:weightsRampPositions",
                    "inputs:weightsRampValues",
                    "inputs:weightsRampInterpolations",
                ],
                default_keys=[[0, 1], [1, 1], [1, 1]],
            )
            ui.Spacer(height=4)
            self.object_indices_ramp_frame = ui.Frame()
            width = self.get_ramp_width(self.object_indices_ramp_frame) * 3
            self.object_indices_ramp_widget = omni.ramp.RampWidget(
                ramp_interface,
                self.object_indices_ramp_frame,
                ramp_prim,
                width=width,
                label="object indices ramp",
                attr_names=[
                    "inputs:objectIndicesRampPositions",
                    "inputs:objectIndicesRampValues",
                    "inputs:objectIndicesRampInterpolations",
                    "inputs:objectIndicesRampTags",
                ],
                default_keys=[[0, 1], [-1, -1], [1, 1]],
            )
            self.width_changed_subscribe()

    def get_ramp_width(self, frame):
        computed_width = int(frame.computed_width)
        if computed_width <= 0:
            computed_width = 400
        return computed_width - 20 - LABEL_WIDTH - HORIZONTAL_SPACING

    def width_changed(self, window_width):
        if self.window_width_change is False:
            return
        if self.weights_ramp_frame is not None and self.weights_ramp_widget is not None:
            self.weights_ramp_widget.width = self.get_ramp_width(self.weights_ramp_frame)
            self.weights_ramp_widget.update()
        if self.object_indices_ramp_frame is not None and self.object_indices_ramp_widget is not None:
            self.object_indices_ramp_widget.width = self.get_ramp_width(self.object_indices_ramp_frame)
            self.object_indices_ramp_widget.update()

    def width_changed_subscribe(self):
        self.window = ui.Workspace.get_window("Property")
        self.window_width_change = True
        if not self.window_width_change_fn_set:
            self.window.set_width_changed_fn(self.width_changed)
            self.window_width_change_fn_set = True
