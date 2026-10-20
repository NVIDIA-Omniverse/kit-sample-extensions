# Public API for module omni.kit.tool.teleport:

## Classes

- class Teleport
  - def __init__(self, test = False)
  - def unbind_widget_material(self)
  - def set_widget_usd_file(self, path)
  - def get_model(self)
  - static def get_instance(test = False)
  - def destroy(self)
  - def set_enabled_picking(self, enabled: bool)
  - def set_active(self, active, test = False)
  - def get_active(self)
  - def on_moved(self, coords: Sequence[float], hit_result)
  - def on_drag(self, hit_result)
  - def end_drag(self, hit_result)
  - def on_clicked(self, coords: Sequence[float], hit_result)
  - def show_arc(self, show: bool = True)
  - def is_using_ring_manipulator(self)

## Functions

- def get_instance()
