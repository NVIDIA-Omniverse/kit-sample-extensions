import asyncio
import functools

import omni.kit as ok
import omni.ui as ui
import omni.usd as ou

# We don't want to depend on omni.kit.window.property just to get at these constants.
# In the long run we need to break ui and evaluation of omni.ramp into two extensions.
# from omni.kit.window.property.templates import LABEL_WIDTH, HORIZONTAL_SPACING
LABEL_WIDTH = 160
HORIZONTAL_SPACING = 4

DEF_ATTR_DATA = {
    "inputs:rampPositions": [0, 1],
    "inputs:rampValues": [0, 1],
    "inputs:rampInterpolations": [1, 1],
    "inputs:tags": [],
}


class Interpolation:
    kNone = 0
    kLinear = 1
    kSmooth = 2


class Attribute:
    value = []
    path = None
    name = None

    def __init__(self, path):
        self.path = path
        self.name = path.split(".")[1]
        self.value = DEF_ATTR_DATA[self.name]
        # print(self.name, self.value)

    def Get(self):
        return self.value

    def Set(self, value):
        self.value = value

    def IsValid(self):
        return True

    def GetPath(self):
        return self.path


class Prim:
    path = None
    attrs = {}

    def __init__(self, path):
        self.path = path

    def GetAttribute(self, name):
        if not name in self.attrs.keys():
            self.attrs[name] = Attribute(self.path + "." + name)
        return self.attrs[name]

    def GetPath(self):
        return self.path


# example use of the ramp widgets without stage prims as a backend
class Window2:
    sub_stage_update = None

    def __init__(self, ramp):
        self.window = ui.Window(
            "ramp widget",
            width=425,
            height=0,
            menu_path="window/ramp",
            dock=ui.DockPreference.LEFT_BOTTOM,
            flags=ui.WINDOW_FLAGS_NO_SCROLLBAR,
        )

        self.context = ou.get_context()
        self.stage = self.context.get_stage()
        if not self.stage:
            return

        prim = Prim("/test")
        if not prim:
            return

        _ramp = RampWidget(ramp, self.window.frame, prim)
        # _ramp = Ramp3Widget(ramp, self.window.frame, prim)
        # self.sub_stage_update = self.context.get_stage_event_stream().create_subscription_to_pop(_ramp.update)

    def on_shutdown(self):
        self.sub_stage_update = None
        del self.window


# example use of the ramp widgets
class Window:
    sub_stage_update = None

    def __init__(self, ramp):
        self.window = ui.Window(
            "ramp widget",
            width=425,
            height=0,
            menu_path="window/ramp",
            dock=ui.DockPreference.LEFT_BOTTOM,
            flags=ui.WINDOW_FLAGS_NO_SCROLLBAR,
        )

        self.context = ou.get_context()
        self.stage = self.context.get_stage()
        if not self.stage:
            return

        # prim = self.stage.GetPrimAtPath("/World/OmniGraph/ParticleSystem/ramp_modulator")
        if not prim:
            return

        _ramp = RampWidget(ramp, self.window.frame, prim)
        # _ramp = Ramp3Widget(ramp, self.window.frame, prim)
        # self.sub_stage_update = self.context.get_stage_event_stream().create_subscription_to_pop(_ramp.update)

    def on_shutdown(self):
        self.sub_stage_update = None
        del self.window


class RampWidget:
    positions_attr_name = "inputs:rampPositions"
    values_attr_name = "inputs:rampValues"
    interpolations_attr_name = "inputs:rampInterpolations"
    tags_attr_name = "inputs:tags"

    default_key_positions = [0, 1]
    default_key_values = [0, 1]
    default_key_interpolations = [1, 1]

    default_range = None

    handle_style = {"background_color": 0xFF909090, "border_color": 0xFF000000, "border_width": 1}
    handle_style_selected = {"background_color": 0xFF909090, "border_color": 0xFFFFFFFF, "border_width": 1}

    def rebuild_ramp(self):
        self.parent_widget.rebuild()

    # attr_names - a list with 3 strings specifiying attribute names (positions, values, interpolations)
    # default_keys - a list with 3 elements:
    # key positions - a list of floats
    # key values - a list of floats
    # key interpolations - a list of integers
    # default_range - a list with 2 floats specifying min/max values for the ramp
    def __init__(
        self,
        ramp,
        parent_widget,
        prim,
        width=400,
        height=100,
        label="float ramp",
        attr_names=None,
        default_keys=None,
        default_range=None,
        clamp_values=False,
        fixed_clamp_values=False,
        graph_style={"border_color": 0xFF000000, "border_width": 1},
    ):

        self.context = ou.get_context()
        self.ramp = ramp
        self.parent_widget = parent_widget
        self.prim = prim
        self.width = width
        self.height = height
        self.label = label
        self.image = None
        self.prim_path = prim.GetPath()
        self.default_range = default_range
        self.clamp_values = clamp_values
        self.fixed_clamp_values = fixed_clamp_values

        if type(attr_names) == list:
            self.positions_attr_name = attr_names[0]
            self.values_attr_name = attr_names[1]
            self.interpolations_attr_name = attr_names[2]
            if len(attr_names) > 3:
                self.tags_attr_name = attr_names[3]

        if type(default_keys) == list:
            self.default_key_positions = default_keys[0]
            self.default_key_values = default_keys[1]
            self.default_key_interpolations = default_keys[2]

        self.key_handle_size = 10
        self.margin = 2

        self.placers_to_indices = {}
        self.indices_to_placers = {}
        self.handles = {}
        self.tag_placers = []

        self.new_placer = None

        self.min_value = 0
        self.max_value = 1

        self.sub_position_changed = None
        self.sub_value_changed = None
        self.sub_interp_changed = None

        self.initial_key_index = -1
        self.key_index = -1
        self.selected_key_index = -1

        self.key_positions_attr = None
        self.key_values_attr = None
        self.key_interps_attr = None
        self.tags_attr = None

        self.key_positions = []
        self.key_values = []
        self.key_interps = []
        self.tags = []

        self.num_keys = 0

        self.width_ratio = 1
        self.height_ratio = 1

        self.async_task_update_keys = None
        self.async_task_add_new_key = None

        self.stage = self.context.get_stage()
        if self.stage or isinstance(self.prim, Prim):
            if self.prim:
                self.key_positions_attr = self.prim.GetAttribute(self.positions_attr_name)
                self.key_values_attr = self.prim.GetAttribute(self.values_attr_name)
                self.key_interps_attr = self.prim.GetAttribute(self.interpolations_attr_name)
                self.tags_attr = self.prim.GetAttribute(self.tags_attr_name)
                if self.key_positions_attr and self.key_values_attr and self.key_interps_attr:
                    with self.parent_widget:
                        with ui.HStack(spacing=HORIZONTAL_SPACING):
                            if label:
                                ui.Label(
                                    self.label,
                                    name="label",
                                    style={"alignment": ui.Alignment.RIGHT_TOP},
                                    width=LABEL_WIDTH,
                                )
                                ui.Spacer(width=HORIZONTAL_SPACING)
                            with ui.VStack(height=0):
                                with ui.HStack():
                                    with ui.ZStack():
                                        ui.Rectangle(style_type_name_override="GraphBackground")
                                        vstack = ui.VStack(height=self.height)
                                        with vstack:
                                            self.byte_image_provider = ui.ByteImageProvider()
                                            self.image = ui.ImageWithProvider(
                                                self.byte_image_provider,
                                                fill_policy=ui.IwpFillPolicy.IWP_STRETCH,
                                                mouse_pressed_fn=functools.partial(
                                                    self.on_mouse_button_pressed_2, vstack
                                                ),
                                                mouse_moved_fn=functools.partial(self.on_mouse_moved_2, vstack),
                                                mouse_released_fn=self.on_mouse_button_released_2,
                                                computed_content_size_changed_fn=self.on_computed_content_size_changed,
                                                style=graph_style,
                                            )
                                        self.zstack_keys = ui.ZStack()
                                with ui.HStack(style={"margin": self.margin}):
                                    ui.Label("position", alignment=ui.Alignment.RIGHT_CENTER)
                                    self.position = ui.FloatField(width=50).model
                                    self.sub_position_changed = self.position.subscribe_end_edit_fn(
                                        self.set_key_position
                                    )

                                    ui.Label("value", width=45, alignment=ui.Alignment.RIGHT_CENTER)
                                    self.value = ui.FloatField(width=50).model
                                    self.sub_value_changed = self.value.subscribe_end_edit_fn(self.set_key_value)

                                    ui.Label("interpolation", width=85, alignment=ui.Alignment.RIGHT_CENTER)
                                    self.interpolation = ui.ComboBox(0, "none", "linear", "smooth", width=75).model
                                    self.sub_interp_changed = self.interpolation.subscribe_item_changed_fn(
                                        self.set_key_interpolation
                                    )
                                    self.interpolation = self.interpolation.get_item_value_model()

        if len(self.indices_to_placers):
            placer = self.indices_to_placers[0]
            self.on_mouse_button_pressed(placer, False)

        self.update()

    # public
    # call this when the ramp has to sync with the usd stage
    def update(self, dt=None):
        # print("update")

        self.stage = self.context.get_stage()
        if not self.stage:
            return

        if not self.prim:
            self.prim = self.stage.GetPrimAtPath(self.prim_path)
            if not self.prim:
                return

        self.width_ratio = self.image.computed_width / self.width
        self.key_positions_attr = self.prim.GetAttribute(self.positions_attr_name)
        self.key_values_attr = self.prim.GetAttribute(self.values_attr_name)
        self.key_interps_attr = self.prim.GetAttribute(self.interpolations_attr_name)
        self.tags_attr = self.prim.GetAttribute(self.tags_attr_name)

        self.initialize_if_empty_ramp()

        if self.key_positions_attr:
            self.key_positions = list(self.key_positions_attr.Get())
        if self.key_values_attr:
            self.key_values = list(self.key_values_attr.Get())
        if self.key_interps_attr:
            self.key_interps = list(self.key_interps_attr.Get())
        if self.tags_attr:
            self.tags = list(self.tags_attr.Get())
        self.num_keys = len(self.key_positions)
        self.selected_key_index = 0
        self.update_ui_elements()

        #
        # display tags, basically discreet values
        #

        for placer in self.tag_placers:
            placer.visible = False

        c = len(self.tags)
        for i in range(c):
            with self.zstack_keys:
                placer = ui.Placer(width=0, height=0, offset_x=0, offset_y=i * self.height / c)
                self.tag_placers.append(placer)
                with placer:
                    with ui.ZStack():
                        ui.Label(self.tags[i], style={"color": 0x20FFFFFF})
                        if i > 0:
                            ui.Rectangle(width=self.width, height=1, style={"color": 0x20FFFFFF})

    def on_shutdown(self):
        self.sub_position_changed = None
        self.sub_value_changed = None
        self.sub_interp_changed = None

    # private
    def update_ui_elements(self):
        self.update_limits()
        self.update_ramp()
        self.update_keys()
        index = self.selected_key_index if self.selected_key_index >= 0 else 0
        self.on_mouse_button_pressed(self.indices_to_placers[index], True)
        self.on_mouse_button_released()

    def update_limits(self):
        # print("update limits")
        if self.fixed_clamp_values:
            return
        if len(self.key_values) == 0:
            return
        self.min_value = min(self.key_values)
        self.max_value = max(self.key_values)
        self.range = self.max_value - self.min_value

    def set_key_position(self, *arg):
        # print("set key positions")

        if self.selected_key_index >= 0:
            self.store_undo_data()

            if self.key_index >= 0:
                index = self.key_index
            else:
                index = self.initial_key_index
            if index < 0:
                index = self.selected_key_index

            position = max(0, min(1, self.position.as_float))

            self.store_undo_data()

            self.key_positions[index] = position
            self.key_index = index
            self.order_keys(position)

            self.key_positions_attr.Set(self.key_positions)
            self.key_values_attr.Set(self.key_values)
            self.key_interps_attr.Set(self.key_interps)

            self.update_ramp()
            self.update_keys()

            self.append_to_undo_stack()

            # preserve selected key
            if self.async_preserve_selected_key_task:
                self.async_preserve_selected_key_task.cancel()
            self.async_preserve_selected_key_task = asyncio.ensure_future(self.async_preserve_selected_key(index))

    def set_key_value(self, *arg):
        # print("set key values")

        if self.selected_key_index >= 0:
            self.store_undo_data()

            if self.key_index >= 0:
                index = self.key_index
            else:
                index = self.initial_key_index
            if index < 0:
                index = self.selected_key_index

            self.key_values = list(self.key_values_attr.Get())
            if self.clamp_values:
                self.key_values[index] = max(self.min_value, min(self.max_value, self.value.as_float))
            else:
                self.key_values[index] = self.value.as_float
            self.key_values_attr.Set(self.key_values)

            self.update_limits()

            self.update_ramp()
            self.update_keys()

            self.append_to_undo_stack()

            # preserve selected key
            if self.async_preserve_selected_key_task:
                self.async_preserve_selected_key_task.cancel()
            self.async_preserve_selected_key_task = asyncio.ensure_future(self.async_preserve_selected_key(index))

    async_preserve_selected_key_task = None

    async def async_preserve_selected_key(self, index):
        # print("preserve selected key")

        # await ok.app.get_app().next_update_async()
        # await ok.app.get_app().next_update_async()
        placer = self.indices_to_placers[index]
        self.on_mouse_button_pressed(placer, False)
        self.on_mouse_button_released()

    def set_key_interpolation(self, *arg):
        # print("set key interpolations")

        if self.selected_key_index >= 0:
            self.store_undo_data()

            if self.key_index >= 0:
                index = self.key_index
            else:
                index = self.initial_key_index
            if index < 0:
                index = self.selected_key_index

            self.key_interps = list(self.key_interps_attr.Get())
            self.key_interps[index] = self.interpolation.get_value_as_int()
            self.key_interps_attr.Set(self.key_interps)

            self.update_ramp()

            self.append_to_undo_stack()

            # preserve selected key
            # if self.async_preserve_selected_key_task:
            #    self.async_preserve_selected_key_task.cancel()
            # self.async_preserve_selected_key_task = asyncio.ensure_future(self.async_preserve_selected_key(index))

    def on_mouse_button_double_clicked(self, *arg):
        # print("delete key")
        if not self.parent_widget.enabled:
            return

        if self.selected_key_index >= 0:
            self.key_positions = list(self.key_positions_attr.Get())
            if len(self.key_positions) > 1:
                self.key_values = list(self.key_values_attr.Get())
                self.key_interps = list(self.key_interps_attr.Get())

                self.key_positions.pop(self.selected_key_index)
                self.key_values.pop(self.selected_key_index)
                self.key_interps.pop(self.selected_key_index)

                self.key_positions_attr.Set(self.key_positions)
                self.key_values_attr.Set(self.key_values)
                self.key_interps_attr.Set(self.key_interps)

                # Work around a bug where omni.ui crashes Kit when
                # trying to compute width for some widgets.
                # Instead of calling self.update_keys at the end of this
                # method, we only hide the placer/key and remove it from
                # the associated buffers.
                placer = self.indices_to_placers[self.selected_key_index]
                placer.visible = False
                del self.handles[self.selected_key_index]
                del self.placers_to_indices[placer]
                del self.indices_to_placers[self.selected_key_index]

                for index in sorted(self.handles.keys()):
                    if index > self.selected_key_index:
                        self.handles[index - 1] = self.handles[index]
                        self.indices_to_placers[index - 1] = self.indices_to_placers[index]

                for placer, index in self.placers_to_indices.items():
                    if index > self.selected_key_index:
                        self.placers_to_indices[placer] = index - 1
                # END - work around a bug where omni.ui crashes ...

                self.num_keys -= 1
                self.selected_key_index = -1
                self.initial_key_index = -1

                self.update_ramp()
                # self.update_keys()

    def on_mouse_button_pressed_2(self, *arg):
        # print("add key, pressed")
        if not self.parent_widget.enabled:
            return

        self.store_undo_data()

        # add key on the next Kit tick
        if self.async_task_add_new_key:
            self.async_task_add_new_key.cancel()
        self.async_task_add_new_key = asyncio.ensure_future(self.async_add_new_key_on_mouse_button_press(arg))

    new_placer_offset_x = None
    new_placer_offset_y = None

    def on_mouse_moved_2(self, *arg):
        if not self.parent_widget.enabled:
            return

        if self.new_placer:
            # print("add key, moved")

            # omni.ui bug prevents us from moving the placer right
            # upon its creation, so lets calculate its position x/y
            # that will be used in on_mouse_moved
            vstack_x = arg[0].screen_position_x
            vstack_y = arg[0].screen_position_y
            cursor_x = arg[1]
            cursor_y = arg[2]
            self.new_placer_offset_x = cursor_x - vstack_x
            self.new_placer_offset_y = cursor_y - vstack_y

            self.on_mouse_moved(self.new_placer)

    def on_computed_content_size_changed(self, *arg):
        self.update()

    def on_mouse_button_released_2(self, *arg):
        if not self.parent_widget.enabled:
            return

        # print("add key, released")
        self.update_keys()

        # if user only clicked on the ramp the self.key_index
        # won't be updated by ::on_mouse_move, use the
        # self.initial_key_index instead
        if self.key_index < 0:
            self.key_index = self.initial_key_index
        if self.key_index < 0:
            self.key_index = self.selected_key_index
        if self.key_index < 0:
            self.key_index = 0
        placer = self.indices_to_placers[self.key_index]

        self.new_placer_offset_x = None
        self.new_placer_offset_y = None

        # select the newly created key
        self.on_mouse_button_pressed(placer, True)
        # complete the cycle
        self.on_mouse_button_released()

        self.append_to_undo_stack()

    PRESSED = False

    def on_mouse_button_pressed(self, *arg):
        # print("select key")

        placer = arg[0]
        self.PRESSED = arg[1]

        # establish initial index and buffer index
        self.selected_key_index = self.placers_to_indices[placer]
        self.initial_key_index = self.placers_to_indices[placer]
        self.key_index = -1

        # get latest ramp keys data
        self.key_positions = list(self.key_positions_attr.Get())
        self.key_values = list(self.key_values_attr.Get())
        self.key_interps = list(self.key_interps_attr.Get())

        self.num_keys = len(self.key_positions)
        self.initial_placer_position = placer.offset_x.value
        self.initial_placer_value = placer.offset_y.value

        # hilite selected key
        for ii in range(self.num_keys):
            if self.initial_key_index == ii:
                self.initial_key_value = self.key_values[self.initial_key_index]
                self.handles[ii].set_style(self.handle_style_selected)
            else:
                self.handles[ii].set_style(self.handle_style)

        self.position.set_value(self.key_positions[self.selected_key_index])
        self.value.set_value(self.key_values[self.selected_key_index])
        self.interpolation.set_value(self.key_interps[self.selected_key_index])

    async def async_add_new_key_on_mouse_button_press(self, *arg):
        # await ok.app.get_app().next_update_async()
        if not self.PRESSED:
            # print("async add key")

            vstack = arg[0][0]
            cursor_position_x = arg[0][1]
            cursor_position_y = arg[0][2]

            width = self.width * self.width_ratio
            position = (cursor_position_x - vstack.screen_position_x) / width
            value = (
                self.min_value
                + ((self.height - (cursor_position_y - vstack.screen_position_y)) / self.height) * self.range
            )

            self.key_positions = list(self.key_positions_attr.Get())
            self.key_values = list(self.key_values_attr.Get())
            self.key_interps = list(self.key_interps_attr.Get())
            self.num_keys = len(self.key_positions)

            interpolation = -1
            if self.num_keys == 1:
                interpolation = self.key_interps[0]
            else:
                for i in range(self.num_keys):
                    if self.key_positions[i] < position:
                        interpolation = self.key_interps[i]
                    else:
                        break
                if interpolation == -1:
                    interpolation = self.key_interps[0]

            self.key_positions.append(position)
            self.key_values.append(value)
            self.key_interps.append(interpolation)

            self.key_index = self.num_keys
            self.num_keys += 1
            if self.num_keys > 1:
                self.order_keys(position)

            self.key_positions_attr.Set(self.key_positions)
            self.key_values_attr.Set(self.key_values)
            self.key_interps_attr.Set(self.key_interps)

            self.update_ramp()
            self.update_keys()

            self.new_placer = self.indices_to_placers[self.key_index]
            # omni.ui bug prevents us from moving a placer right upon
            # its creation, so hide it for now and unhide it when user
            # releases the mouse button
            self.new_placer.visible = False

            # key_index = self.key_index
            self.on_mouse_button_pressed(self.new_placer, True)
            # self.key_index = key_index
            self.RELEASED = False

    async def async_update_keys_on_mouse_button_release(self, index):
        # await ok.app.get_app().next_update_async()
        self.width_ratio = self.image.computed_width / self.width
        self.height_ratio = self.image.computed_height / self.height
        self.update_keys()
        self.on_mouse_button_pressed(self.indices_to_placers[index], False)
        self.PRESSED = False

    RELEASED = False

    def on_mouse_button_released(self, *arg):
        # print("mouse button released")

        self.RELEASED = True

        # remap ui widgets if user reordered keys
        if self.initial_key_index >= 0 and self.key_index >= 0 and self.initial_key_index != self.key_index:
            placer1 = self.indices_to_placers[self.initial_key_index]
            placer2 = self.indices_to_placers[self.key_index]
            self.placers_to_indices[placer1] = self.key_index
            self.placers_to_indices[placer2] = self.initial_key_index
            self.indices_to_placers[self.initial_key_index] = placer2
            self.indices_to_placers[self.key_index] = placer1

            handles1 = self.handles[self.initial_key_index]
            handles2 = self.handles[self.key_index]
            self.handles[self.initial_key_index] = handles2
            self.handles[self.key_index] = handles1

        self.update_limits()
        self.update_ramp()

        # update keys on the next tick
        if self.async_task_update_keys:
            self.async_task_update_keys.cancel()
        index = self.key_index if self.key_index >= 0 else self.initial_key_index
        self.async_task_update_keys = asyncio.ensure_future(self.async_update_keys_on_mouse_button_release(index))

        # restore initial conditions
        self.initial_key_index = -1
        self.key_index = -1
        self.new_placer = None

        self.RELEASED = False

    def on_mouse_moved(self, *arg):
        if self.RELEASED:
            return

        # print("move key")

        placer = arg[0]

        # Workaround to omni.ui bug where new placers
        # cannot be moved right after their creation.
        # If moving existing key use it's placer position,
        # otherwise use the values provided by on_mouse_moved_2.
        if self.new_placer_offset_x is None:
            x = placer.offset_x.value
        else:
            x = self.new_placer_offset_x

        if self.new_placer_offset_y is None:
            y = placer.offset_y.value
        else:
            y = self.new_placer_offset_y

        width = self.width * self.width_ratio

        key_position = round(max(0, min(1, x / width)), 4)
        key_value = self.initial_key_value + (self.initial_placer_value - y) * (self.range / self.height)
        if key_value < self.min_value:
            key_value = self.min_value
        elif key_value > self.max_value:
            key_value = self.max_value

        if self.key_index < 0:
            self.key_index = self.initial_key_index

        self.key_positions[self.key_index] = key_position
        self.key_values[self.key_index] = key_value

        if self.key_index < 0:
            self.key_index = self.initial_key_index

        self.key_positions[self.key_index] = key_position
        self.key_values[self.key_index] = key_value

        # update keys data, order them if user dragged one in front, or behind others
        self.order_keys(key_position)
        self.key_values_attr.Set(self.key_values)
        self.key_interps_attr.Set(self.key_interps)
        self.key_positions_attr.Set(self.key_positions)

        self.selected_key_index = self.key_index

        # limit dragged placer within the ramp area
        if x < 0 or x > width:
            placer.offset_x = round(max(0, min(width, x)))
        if y < 0 or y > self.height:
            placer.offset_y = round(max(0, min(self.height, y)))

        # update widgets
        self.position.set_value(key_position)
        self.value.set_value(self.key_values[self.key_index])
        self.interpolation.set_value(self.key_interps[self.key_index])

        self.update_ramp()

    def order_keys(self, position):
        self.key_positions.sort()
        new_index = self.key_positions.index(position, 0, self.num_keys)

        if new_index == self.key_index:
            return False
        else:
            value = self.key_values.pop(self.key_index)
            interp = self.key_interps.pop(self.key_index)

            self.key_values.insert(new_index, value)
            self.key_interps.insert(new_index, interp)

            self.key_index = new_index

            return True

    def initialize_if_empty_ramp(self):
        if len(self.key_positions_attr.Get()) == 0:
            self.key_positions_attr.Set(self.default_key_positions)
            self.key_values_attr.Set(self.default_key_values)
            self.key_interps_attr.Set(self.default_key_interpolations)

    def update_ramp(self):
        # print("update ramp")

        self.initialize_if_empty_ramp()

        if self.default_range:
            if self.min_value > self.default_range[0]:
                self.min_value = self.default_range[0]
            if self.max_value < self.default_range[1]:
                self.max_value = self.default_range[1]

        if self.key_positions_attr.IsValid() and self.key_positions_attr.IsValid() and self.key_interps_attr.IsValid():
            pixels = self.ramp.get_float_array_as_rgba8_2(
                self.width,
                self.height,
                self.min_value,
                self.max_value,
                self.key_positions,
                self.key_values,
                self.key_interps,
            )
        else:
            pixels = [0] * self.width * self.height * 4

        self.byte_image_provider.set_bytes_data(pixels, [self.width, self.height])

    def update_keys(self):
        # print("update keys")

        # currently omni.ui API cannot delete widgets - hide them instead
        for placer in self.indices_to_placers.values():
            placer.visible = False
        for handle in self.handles.values():
            handle.visible = False

        if self.default_range:
            if self.min_value > self.default_range[0]:
                self.min_value = self.default_range[0]
            if self.max_value < self.default_range[1]:
                self.max_value = self.default_range[1]

        self.range = self.max_value - self.min_value

        with self.zstack_keys:
            for i in range(self.num_keys):
                x = self.key_positions[i] * self.width
                if self.range:
                    y = self.height - abs((self.key_values[i] - self.min_value) / self.range * self.height)
                else:
                    y = self.height
                self.create_key_handle(i, x, y)

    def create_key_handle(self, index, x, y):
        offset = -self.key_handle_size * 0.5
        with ui.Placer(offset_x=offset, offset_y=offset):
            placer = ui.Placer(
                width=self.key_handle_size,
                height=self.key_handle_size,
                offset_x=x * self.width_ratio,
                offset_y=y * self.height_ratio,
                draggable=True,
                stable_size=True,
            )
            placer.set_offset_x_changed_fn(functools.partial(self.on_mouse_moved, placer))
            placer.set_offset_y_changed_fn(functools.partial(self.on_mouse_moved, placer))

            with placer:
                with ui.ZStack(
                    mouse_pressed_fn=functools.partial(self.on_mouse_button_pressed, placer, True),
                    mouse_released_fn=self.on_mouse_button_released,
                ):
                    circle = ui.Circle(
                        radius=self.key_handle_size * 0.5,
                        mouse_double_clicked_fn=self.on_mouse_button_double_clicked,
                        style=self.handle_style,
                    )

            self.handles[index] = circle
            self.placers_to_indices[placer] = index
            self.indices_to_placers[index] = placer

        return placer

    init_key_positions = None
    init_key_values = None
    init_key_interps = None

    def store_undo_data(self):
        self.init_key_positions = self.key_positions.copy()
        self.init_key_values = self.key_values.copy()
        self.init_key_interps = self.key_interps.copy()

    def append_to_undo_stack(self):
        if (
            self.init_key_positions != self.key_positions
            or self.init_key_values != self.key_values
            or self.init_key_interps != self.key_interps
        ):
            ok.commands.execute(
                "SetRampValuesCommand",
                prim_path=self.prim_path,
                pos_attr_name=self.positions_attr_name,
                val_attr_name=self.values_attr_name,
                int_attr_name=self.interpolations_attr_name,
                old_positions=self.init_key_positions,
                old_values=self.init_key_values,
                old_interps=self.init_key_interps,
                new_positions=self.key_positions,
                new_values=self.key_values,
                new_interps=self.key_interps,
            )


class Ramp3Widget:
    positions_attr_name = "inputs:ramp3fPositions"
    values_attr_name = "inputs:ramp3fValues"
    interpolations_attr_name = "inputs:ramp3fInterpolations"

    default_key_positions = [0, 0.5, 1]
    default_key_values = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
    default_key_interpolations = [1, 1, 1]

    key_handle_size = 10
    margin = 2

    key_handle_outline_style = {"background_color": 0x00000000, "border_color": 0xFF000000, "border_width": 1}
    key_handle_selected_style = {"border_color": 0xFFFFFFFF, "border_width": 2}
    key_handle_style = {"border_color": 0xFF000000, "border_width": 1}

    # attr_names - a list with 3 strings specifiying attribute names (positions, values, interpolations)
    # default_keys - a list with 3 elements:
    # key positions - a list of floats
    # key values - a list of tuples, each tuple should contain 3 elements (RGB)
    # key interpolations - a list of integers
    def __init__(
        self, ramp, parent_widget, prim, width=400, height=50, label="color ramp", attr_names=None, default_keys=None
    ):
        self.ramp = ramp
        self.parent_widget = parent_widget
        self.prim = prim
        self.width = width
        self.height = height
        self.image = None
        self.prim_path = prim.GetPath()
        self.context = ou.get_context()
        self.stage = self.context.get_stage()

        if type(attr_names) == list:
            if len(attr_names) == 3:
                self.positions_attr_name = attr_names[0]
                self.values_attr_name = attr_names[1]
                self.interpolations_attr_name = attr_names[2]

        if type(default_keys) == list:
            self.default_key_positions = default_keys[0]
            self.default_key_values = default_keys[1]
            self.default_key_interpolations = default_keys[2]

        self.placers_to_indices = {}
        self.indices_to_placers = {}
        self.handles = {}

        self.new_placer = None

        self.sub_position_changed = None
        self.sub_value_changed = None
        self.sub_interp_changed = None

        self.initial_key_index = -1
        self.key_index = -1
        self.selected_key_index = -1

        self.key_positions_attr = None
        self.key_values_attr = None
        self.key_interps_attr = None

        self.key_positions = []
        self.key_values = []
        self.key_interps = []
        self.max_key_value = 0.0
        self.num_keys = 0

        self.width_ratio = 1

        self.async_task_update_keys = None
        self.PRESSED = False

        if self.stage:
            if self.prim:
                self.key_positions_attr = self.prim.GetAttribute(self.positions_attr_name)
                self.key_values_attr = self.prim.GetAttribute(self.values_attr_name)
                self.key_interps_attr = self.prim.GetAttribute(self.interpolations_attr_name)
                if self.key_positions_attr and self.key_values_attr and self.key_interps_attr:
                    with self.parent_widget:
                        with ui.HStack():
                            if label != "":
                                ui.Label(
                                    label, name="label", style={"alignment": ui.Alignment.RIGHT_TOP}, width=LABEL_WIDTH
                                )
                                ui.Spacer(width=HORIZONTAL_SPACING * 2)
                            with ui.VStack(height=0):
                                with ui.HStack():
                                    ui.Spacer(width=HORIZONTAL_SPACING)
                                    vstack = ui.VStack(height=self.height)
                                    with vstack:
                                        self.byte_image_provider = ui.ByteImageProvider()
                                        self.image = ui.ImageWithProvider(
                                            self.byte_image_provider,
                                            fill_policy=ui.IwpFillPolicy.IWP_STRETCH,
                                            mouse_pressed_fn=functools.partial(self.on_mouse_button_pressed_2, vstack),
                                            mouse_moved_fn=functools.partial(self.on_mouse_moved_2, vstack),
                                            mouse_released_fn=self.on_mouse_button_released_2,
                                            style={"border_color": 0xFF000000, "border_width": 1},
                                        )
                                self.zstack_keys = ui.ZStack(height=self.key_handle_size * 2)
                                with ui.HStack(style={"margin": 2}):
                                    ui.Label("position", alignment=ui.Alignment.RIGHT_CENTER)
                                    self.position = ui.FloatField(width=75).model
                                    self.sub_position_changed = self.position.subscribe_end_edit_fn(
                                        self.set_key_position
                                    )

                                    ui.Label("value", width=45, alignment=ui.Alignment.RIGHT_CENTER)
                                    self.value_widget = ui.ColorWidget(0.0, 0.0, 0.0, width=75)
                                    self.sub_value_changed = self.value_widget.model.subscribe_end_edit_fn(
                                        self.set_key_value
                                    )
                                    sub_models = self.value_widget.model.get_item_children()
                                    self.value_r = self.value_widget.model.get_item_value_model(sub_models[0])
                                    self.value_g = self.value_widget.model.get_item_value_model(sub_models[1])
                                    self.value_b = self.value_widget.model.get_item_value_model(sub_models[2])

                                    ui.Label("interpolation", width=85, alignment=ui.Alignment.RIGHT_CENTER)
                                    self.interpolation = ui.ComboBox(0, "none", "linear", "smooth", width=75).model
                                    self.sub_interp_changed = self.interpolation.subscribe_item_changed_fn(
                                        self.set_key_interpolation
                                    )
                                    self.interpolation = self.interpolation.get_item_value_model()

                    self.update()

                    if len(self.indices_to_placers):
                        placer = self.indices_to_placers[0]
                        self.on_mouse_button_pressed(placer)

    # public
    # call this when the ramp has tosync with the usd stage
    def update(self, dt=None):
        # print("update")

        self.stage = self.context.get_stage()
        if not self.stage:
            return

        if not self.prim:
            self.prim = self.stage.GetPrimAtPath(self.prim_path)
            if not self.prim:
                return

        self.key_positions_attr = self.prim.GetAttribute(self.positions_attr_name)
        self.key_values_attr = self.prim.GetAttribute(self.values_attr_name)
        self.key_interps_attr = self.prim.GetAttribute(self.interpolations_attr_name)

        self.initialize_if_empty_ramp()

        if self.key_positions_attr:
            self.key_positions = list(self.key_positions_attr.Get())
        if self.key_values_attr:
            self.key_values = list(self.key_values_attr.Get())
        if self.key_interps_attr:
            self.key_interps = list(self.key_interps_attr.Get())
        self.num_keys = len(self.key_positions)

        self.update_ui_elements()

        # update keys on the next tick
        if self.async_task_update_keys:
            self.async_task_update_keys.cancel()
        index = self.key_index if self.key_index >= 0 else self.initial_key_index
        self.async_task_update_keys = asyncio.ensure_future(self.async_update_keys_on_mouse_button_release(index))

    def update_ui_elements(self):
        self.update_ramp()
        self.update_keys()
        index = self.selected_key_index if self.selected_key_index >= 0 else 0
        self.on_mouse_button_pressed(self.indices_to_placers[index])

    def on_shutdown(self):
        self.sub_position_changed = None
        self.sub_value_changed = None
        self.sub_interp_changed = None

    # private
    def set_key_position(self, *arg):
        # print("set key positions")

        if self.selected_key_index >= 0:
            self.store_undo_data()

            if self.key_index >= 0:
                index = self.key_index
            else:
                index = self.initial_key_index
            if index < 0:
                index = self.selected_key_index

            position = max(0, min(1, self.position.as_float))

            self.key_positions[index] = position
            self.key_index = index
            self.order_keys(position)

            self.key_positions_attr.Set(self.key_positions)
            self.key_values_attr.Set(self.key_values)
            self.key_interps_attr.Set(self.key_interps)

            self.update_ramp()
            self.update_keys()

            self.append_to_undo_stack()

    def set_key_value(self, *arg):
        # print("set key values")

        if self.selected_key_index >= 0:
            self.store_undo_data()

            if self.key_index >= 0:
                index = self.key_index
            else:
                index = self.selected_key_index
            self.key_values = list(self.key_values_attr.Get())

            self.key_values[index] = (self.value_r.as_float, self.value_g.as_float, self.value_b.as_float)
            self.update_max_value()
            self.key_values_attr.Set(self.key_values)

            self.update_ramp()
            self.update_keys()

            self.append_to_undo_stack()

    def update_max_value(self):
        max_value = 0.0
        for v in self.key_values:
            max_value = max(max_value, max(v))
        if max_value <= 0:
            max_value = 1.0
        self.max_component_value = max_value

    def set_key_interpolation(self, *arg):
        # print("set key interpolations")

        if self.selected_key_index >= 0:
            self.store_undo_data()

            if self.key_index >= 0:
                index = self.key_index
            else:
                index = self.selected_key_index
            self.key_interps = list(self.key_interps_attr.Get())
            self.key_interps[index] = self.interpolation.get_value_as_int()
            self.key_interps_attr.Set(self.key_interps)

            self.update_ramp()

            self.append_to_undo_stack()

    def on_mouse_button_double_clicked(self, *arg):
        # print("delete key")

        if self.selected_key_index >= 0:
            self.store_undo_data()
            self.DISABLE_UNDO = True

            self.key_positions = list(self.key_positions_attr.Get())
            if len(self.key_positions) > 1:
                self.key_values = list(self.key_values_attr.Get())
                self.key_interps = list(self.key_interps_attr.Get())

                self.key_positions.pop(self.selected_key_index)
                self.key_values.pop(self.selected_key_index)
                self.key_interps.pop(self.selected_key_index)

                self.key_positions_attr.Set(self.key_positions)
                self.key_values_attr.Set(self.key_values)
                self.key_interps_attr.Set(self.key_interps)

                # Work around a bug where omni.ui crashes Kit when
                # trying to compute width for some widgets.
                # Instead of calling self.update_keys at the end of this
                # method, we only hide the placer/key and remove it from
                # the associated buffers.
                placer = self.indices_to_placers[self.selected_key_index]
                placer.visible = False
                del self.handles[self.selected_key_index]
                del self.placers_to_indices[placer]
                del self.indices_to_placers[self.selected_key_index]

                for index in sorted(self.handles.keys()):
                    if index > self.selected_key_index:
                        self.handles[index - 1] = self.handles[index]
                        self.indices_to_placers[index - 1] = self.indices_to_placers[index]

                for placer, index in self.placers_to_indices.items():
                    if index > self.selected_key_index:
                        self.placers_to_indices[placer] = index - 1
                # END - work around a bug where omni.ui crashes ...

                selected_key_index = self.selected_key_index

                self.num_keys -= 1
                self.selected_key_index = -1
                self.initial_key_index = -1

                self.update_ramp()

                if selected_key_index >= self.num_keys:
                    selected_key_index = self.num_keys - 1

                self.on_mouse_button_pressed(self.indices_to_placers[selected_key_index])

                self.append_to_undo_stack()
                self.DISABLE_UNDO = False

    DISABLE_UNDO = False

    def on_mouse_button_pressed_2(self, *arg):
        # print("add key")

        vstack = arg[0]
        cursor_position_x = arg[1]
        position = (cursor_position_x - vstack.screen_position_x) / self.image.computed_width

        if self.key_positions_attr.IsValid() and self.key_positions_attr.IsValid() and self.key_interps_attr.IsValid():
            value = self.ramp.get_float3_at_position(
                position,
                str(self.key_positions_attr.GetPath()),
                str(self.key_values_attr.GetPath()),
                str(self.key_interps_attr.GetPath()),
            )
        else:
            value = 0

        self.key_positions = list(self.key_positions_attr.Get())
        self.key_values = list(self.key_values_attr.Get())
        self.key_interps = list(self.key_interps_attr.Get())
        self.num_keys = len(self.key_positions)

        self.store_undo_data()
        self.DISABLE_UNDO = True

        interpolation = -1
        if self.num_keys == 1:
            interpolation = self.key_interps[0]
        else:
            for i in range(self.num_keys):
                if self.key_positions[i] < position:
                    interpolation = self.key_interps[i]
                else:
                    break
                if interpolation == -1:
                    interpolation = self.key_interps[0]

        self.width_ratio = self.image.computed_width / self.width
        self.key_positions.append(position)
        self.key_values.append(value)
        self.key_interps.append(interpolation)

        self.key_index = self.num_keys
        self.num_keys += 1
        if self.num_keys > 1:
            self.order_keys(position)

        self.key_positions_attr.Set(self.key_positions)
        self.key_values_attr.Set(self.key_values)
        self.key_interps_attr.Set(self.key_interps)

        self.update_ramp()
        self.update_keys()

        self.new_placer = self.indices_to_placers[self.key_index]

        # there seems to be a bug in the omni.ui API - placers don't get
        # updated when doing placer.offset_x = some_value in ::on_move_moved_2
        # hide it for now and display when mouse button is released, inside on_mouse_button_released_2
        self.new_placer.visible = False

        self.on_mouse_button_pressed(self.new_placer)

    def on_mouse_moved_2(self, *arg):
        if self.new_placer:
            # print("move new key")

            vstack = arg[0]
            cursor_position_x = arg[1]
            placer_position = cursor_position_x - vstack.screen_position_x

            self.new_placer.offset_x = placer_position

    def on_mouse_button_released_2(self, *arg):
        self.update_keys()

        # if user only clicked on the ramp the self.key_index
        # won't be updated by ::on_mouse_move, use the
        # self.initial_key_index instead
        if self.key_index < 0:
            self.key_index = self.initial_key_index
        placer = self.indices_to_placers[self.key_index]

        # select the newly created key
        self.on_mouse_button_pressed(placer)
        # complete the cycle
        self.on_mouse_button_released()

        self.DISABLE_UNDO = False
        self.append_to_undo_stack()

    def on_mouse_button_pressed(self, *arg):
        # print("select key")
        if not self.parent_widget.enabled:
            return

        self.PRESSED = True
        placer = arg[0]

        # establish initial index and buffer index
        self.selected_key_index = self.placers_to_indices[placer]
        self.initial_key_index = self.placers_to_indices[placer]
        self.key_index = -1

        # get latest ramp keys data
        self.key_positions = list(self.key_positions_attr.Get())
        self.key_values = list(self.key_values_attr.Get())
        self.key_interps = list(self.key_interps_attr.Get())

        self.store_undo_data()

        self.num_keys = len(self.key_positions)

        # hilite selected key
        for ii in range(self.num_keys):
            if self.initial_key_index == ii:
                self.handles[ii][2].set_style(self.key_handle_selected_style)
                self.handles[ii][3].set_style(self.key_handle_selected_style)
            else:
                self.handles[ii][2].set_style(self.key_handle_style)
                self.handles[ii][3].set_style(self.key_handle_style)

        self.position.set_value(self.key_positions[self.selected_key_index])
        self.value_r.set_value(self.key_values[self.selected_key_index][0])
        self.value_g.set_value(self.key_values[self.selected_key_index][1])
        self.value_b.set_value(self.key_values[self.selected_key_index][2])
        self.interpolation.set_value(self.key_interps[self.selected_key_index])

    def on_mouse_button_released(self, *arg):
        # print("mouse button released")
        if not self.parent_widget.enabled:
            return

        # remap ui widgets if user reordered keys
        if self.initial_key_index >= 0 and self.key_index >= 0 and self.initial_key_index != self.key_index:
            placer1 = self.indices_to_placers[self.initial_key_index]
            placer2 = self.indices_to_placers[self.key_index]
            self.placers_to_indices[placer1] = self.key_index
            self.placers_to_indices[placer2] = self.initial_key_index
            self.indices_to_placers[self.initial_key_index] = placer2
            self.indices_to_placers[self.key_index] = placer1

            handles1 = self.handles[self.initial_key_index]
            handles2 = self.handles[self.key_index]
            self.handles[self.initial_key_index] = handles2
            self.handles[self.key_index] = handles1

        self.update_ramp()

        # update keys on the next tick
        if self.async_task_update_keys:
            self.async_task_update_keys.cancel()
        index = self.key_index if self.key_index >= 0 else self.initial_key_index
        self.async_task_update_keys = asyncio.ensure_future(self.async_update_keys_on_mouse_button_release(index))

        # restore initial conditions
        self.initial_key_index = -1
        self.key_index = -1
        self.new_placer = None

        self.append_to_undo_stack()
        self.PRESSED = False

    async def async_update_keys_on_mouse_button_release(self, index):
        # await ok.app.get_app().next_update_async()
        self.width_ratio = self.image.computed_width / self.width
        self.update_keys()
        self.on_mouse_button_pressed(self.indices_to_placers[index], False)
        self.PRESSED = False

    def on_mouse_moved(self, *arg):
        # print("move key")
        if not self.parent_widget.enabled:
            return

        placer = arg[0]
        placer_position = placer.offset_x.value

        if self.key_index < 0:
            self.key_index = self.initial_key_index

        width = self.width * self.width_ratio

        # calculate and set new key position
        key_position = round(max(0, min(1, placer_position / width)), 4)
        self.key_positions[self.key_index] = key_position

        # update keys data, order them if user dragged one in front, or behind others
        if self.order_keys(key_position):
            self.key_values_attr.Set(self.key_values)
            self.key_interps_attr.Set(self.key_interps)
        self.key_positions_attr.Set(self.key_positions)

        self.selected_key_index = self.key_index

        # limit dragged placer within the ramp area
        if placer.offset_x.value < 0 or placer.offset_x.value > width:
            placer.offset_x = round(max(0, min(width, placer.offset_x.value)))

        # update widgets
        self.position.set_value(key_position)
        self.value_r.set_value(self.key_values[self.key_index][0])
        self.value_g.set_value(self.key_values[self.key_index][1])
        self.value_b.set_value(self.key_values[self.key_index][2])
        self.interpolation.set_value(self.key_interps[self.key_index])

        self.update_ramp()

    def order_keys(self, position):
        self.key_positions.sort()
        new_index = self.key_positions.index(position, 0, self.num_keys)

        if new_index == self.key_index:
            return False
        else:
            value = self.key_values.pop(self.key_index)
            interp = self.key_interps.pop(self.key_index)

            self.key_values.insert(new_index, value)
            self.key_interps.insert(new_index, interp)

            self.key_index = new_index

            return True

    def initialize_if_empty_ramp(self):
        if len(self.key_positions_attr.Get()) == 0:
            self.key_positions_attr.Set(self.default_key_positions)
            self.key_values_attr.Set(self.default_key_values)
            self.key_interps_attr.Set(self.default_key_interpolations)
        self.max_component_value = 1.0

    def update_ramp(self):
        # print("update ramp")

        self.initialize_if_empty_ramp()

        num_pixels_x = self.width
        num_pixels_y = 1
        pixels = [1] * num_pixels_x * num_pixels_y * 4

        positions = [x / (num_pixels_x - 1) for x in range(num_pixels_x)]
        if self.key_positions_attr.IsValid() and self.key_positions_attr.IsValid() and self.key_interps_attr.IsValid():
            values = self.ramp.get_float3_array(
                positions,
                str(self.key_positions_attr.GetPath()),
                str(self.key_values_attr.GetPath()),
                str(self.key_interps_attr.GetPath()),
            )
        else:
            values = [0] * num_pixels_x

        for x in range(num_pixels_x):
            for y in range(num_pixels_y):
                index = y * num_pixels_x * 4 + x * 4
                pixels[index + 0] = values[x][0]
                pixels[index + 1] = values[x][1]
                pixels[index + 2] = values[x][2]
        self.byte_image_provider.set_bytes_data(pixels, [num_pixels_x, num_pixels_y])

    def update_keys(self):
        self.update_max_value()
        # currently omni.ui API cannot delete widgets - hide them instead
        for placer in self.placers_to_indices.keys():
            placer.visible = False
        for handle in self.handles.values():
            handle[0].visible = False
            handle[1].visible = False
            handle[2].visible = False
            handle[3].visible = False

        self.placers_to_indices = {}
        self.indices_to_placers = {}
        self.handles = {}

        with self.zstack_keys:
            for i in range(self.num_keys):
                self.create_key_handle(i, self.key_positions[i] * self.width, self.key_values[i])

    def create_key_handle(self, index, position, value):
        placer = ui.Placer(
            width=self.key_handle_size,
            height=self.key_handle_size,
            offset_x=position * self.width_ratio,
            offset_y=0,
            draggable=True,
            drag_axis=ui.Axis.X,
            stable_size=True,
        )
        placer.set_offset_x_changed_fn(functools.partial(self.on_mouse_moved, placer))

        with placer:
            with ui.ZStack(
                mouse_pressed_fn=functools.partial(self.on_mouse_button_pressed, placer),
                mouse_released_fn=self.on_mouse_button_released,
            ):
                with ui.Placer():
                    border_triangle = ui.Triangle(
                        width=self.key_handle_size,
                        height=self.key_handle_size * 0.5,
                        alignment=ui.Alignment.CENTER_TOP,
                        style=self.key_handle_outline_style,
                    )
                with ui.Placer(offset_y=self.key_handle_size * 0.5 + 0.5):
                    border_rectangle = ui.Rectangle(
                        width=self.key_handle_size, height=self.key_handle_size - 2, style=self.key_handle_outline_style
                    )

                r = int(self.basic_clamp(value[0]) * 255)
                g = int(self.basic_clamp(value[1]) * 255) << 8
                b = int(self.basic_clamp(value[2]) * 255) << 16

                a = 255 << 24
                with ui.Placer(offset_x=1, offset_y=1):
                    triangle = ui.Triangle(
                        width=self.key_handle_size - 2,
                        height=self.key_handle_size * 0.5 - 1,
                        mouse_double_clicked_fn=self.on_mouse_button_double_clicked,
                        alignment=ui.Alignment.CENTER_TOP,
                        style={"background_color": (r + g + b + a)},
                    )
                with ui.Placer(offset_x=1, offset_y=self.key_handle_size * 0.5 - 0.5):
                    rectangle = ui.Rectangle(
                        width=self.key_handle_size - 1.75,
                        height=self.key_handle_size - 2,
                        mouse_double_clicked_fn=self.on_mouse_button_double_clicked,
                        style={"background_color": (r + g + b + a)},
                    )

                self.handles[index] = (triangle, rectangle, border_triangle, border_rectangle)
                self.placers_to_indices[placer] = index
                self.indices_to_placers[index] = placer

        return placer

    init_key_positions = None
    init_key_values = None
    init_key_interps = None

    def store_undo_data(self):
        if not self.DISABLE_UNDO:
            self.init_key_positions = self.key_positions.copy()
            self.init_key_values = self.key_values.copy()
            self.init_key_interps = self.key_interps.copy()

    def append_to_undo_stack(self):
        if not self.DISABLE_UNDO:
            if (
                self.init_key_positions != self.key_positions
                or self.init_key_values != self.key_values
                or self.init_key_interps != self.key_interps
            ):
                ok.commands.execute(
                    "SetRampValuesCommand",
                    prim_path=self.prim_path,
                    pos_attr_name=self.positions_attr_name,
                    val_attr_name=self.values_attr_name,
                    int_attr_name=self.interpolations_attr_name,
                    old_positions=self.init_key_positions,
                    old_values=self.init_key_values,
                    old_interps=self.init_key_interps,
                    new_positions=self.key_positions,
                    new_values=self.key_values,
                    new_interps=self.key_interps,
                )

    def basic_clamp(self, num):
        return max(min(num, 1.0), 0.0)
