import omni.ui as ui
from omni.kit.property.usd.custom_layout_helper import CustomLayoutFrame, CustomLayoutGroup, CustomLayoutProperty
from omni.kit.property.usd.usd_model_base import UsdBase
from omni.kit.window.property.templates import HORIZONTAL_SPACING, LABEL_WIDTH

ATTRIB_LABEL_STYLE = {"alignment": ui.Alignment.RIGHT_TOP}

# XXX these types coincidentally align with the corresponding enumerations in OgnRaycast
COLLISION_PROXY_OPTIONS = ["Sphere", "Axis-Oriented Box"]
UP_AXIS_SOURCE_OPTIONS = ["Stage Up Axis", "Node Up Axis"]


class IntOptionItem(ui.AbstractItem):
    def __init__(self, option_name, option_index):
        super().__init__()
        self.model = ui.SimpleStringModel(option_name)
        self.value = option_index


class IntOptionsModel(ui.AbstractItemModel, UsdBase):
    def __init__(self, stage, attribute_paths, self_refresh, options):
        UsdBase.__init__(self, stage, attribute_paths, self_refresh, {})
        ui.AbstractItemModel.__init__(self)

        self._current_index = ui.SimpleIntModel()
        self._current_index.add_value_changed_fn(self._current_index_changed)

        self._items = []
        self.build_option_items(options)

        self._has_index = False
        self._update_value()
        self._has_index = True

    def clean(self):
        UsdBase.clean(self)

    def build_option_items(self, options):
        for i, option in enumerate(options):
            self._items.append(IntOptionItem(option, i))

    def get_item_children(self, item):
        self._update_value()
        return self._items

    def get_item_value_model(self, item, column_id):
        if item is None:
            return self._current_index
        return item.model

    def _current_index_changed(self, model):
        if not self._has_index:
            return

        index = model.as_int
        if self.set_value(self._items[index].value):
            self._item_changed(None)

    def _update_value(self, force=False):
        if UsdBase._update_value(self, force):
            index = -1
            for i in range(len(self._items)):
                if self._items[i].value == self._value:
                    index = i
            self._current_index.set_value(index)

    def _on_dirty(self):
        self._item_changed(None)


class CustomLayout:
    def __init__(self, compute_node_widget):
        # Enable template
        self.enable = True
        self.compute_node_widget = compute_node_widget
        self.compute_node_widget.get_bundles()  # ?

    def apply(self, props):
        frame = CustomLayoutFrame(hide_extra=True)
        with frame:
            with CustomLayoutGroup("Collision Proxy"):
                CustomLayoutProperty(None, None, build_fn=self.collision_proxy_build_fn)
            with CustomLayoutGroup("Horizontal Projection"):
                CustomLayoutProperty("inputs:pushoutHorizontally", "Horizontal Pushout Only")
                CustomLayoutProperty(None, None, build_fn=self.up_source_build_fn)
                CustomLayoutProperty("inputs:upAxis", "Node Up Axis")
            with CustomLayoutGroup("Resolution"):
                CustomLayoutProperty("inputs:samplesPerSegment", "Points per Input Curve Segment")
                CustomLayoutProperty("inputs:numberOfSegments", "Number of Segments per Output Curve")

        return frame.apply(props)

    def collision_proxy_build_fn(self, *args):
        with ui.HStack(spacing=HORIZONTAL_SPACING):
            ui.Label("Collision Proxy Type", name="label", style=ATTRIB_LABEL_STYLE, width=LABEL_WIDTH)
            ui.Spacer(width=HORIZONTAL_SPACING)
            with ui.ZStack():
                attr_path = self.compute_node_widget._payload[-1].AppendProperty("inputs:collisionProxy")
                model = IntOptionsModel(self.compute_node_widget.stage, [attr_path], False, COLLISION_PROXY_OPTIONS)
                ui.ComboBox(model)

    def up_source_build_fn(self, *args):
        with ui.HStack(spacing=HORIZONTAL_SPACING):
            ui.Label("Up Axis Source", name="label", style=ATTRIB_LABEL_STYLE, width=LABEL_WIDTH)
            ui.Spacer(width=HORIZONTAL_SPACING)
            with ui.ZStack():
                attr_path = self.compute_node_widget._payload[-1].AppendProperty("inputs:upAxisSource")
                model = IntOptionsModel(self.compute_node_widget.stage, [attr_path], False, UP_AXIS_SOURCE_OPTIONS)
                ui.ComboBox(model)
