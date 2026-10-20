# Public API for module omni.graph.visualization.nodes:

## Classes

- class PublicExtension(omni.ext.IExt)
  - def __init__(self)
  - def on_startup(self, ext_id)
  - def on_shutdown(self)

- class ViewportManager
  - class ViewportNextFactory
    - def __init__(self, factory_args, *ui_args, **ui_kwargs)
    - def destroy(self)
  - class def request_rebuild(cls)
  - class def add_layout_builder(cls, node_path, build_fn: Callable)
  - class def remove_layout_builder(cls, node_path)
  - def __init__(self)
  - def startup(self)
  - def shutdown(self)

- class VisualizationModel(sc.AbstractManipulatorModel)
  - class Line
    - def __init__(self, start, end, color, thickness)
  - class Label
    - def __init__(self, text, color, size, transform)
  - class PositionItem(sc.AbstractManipulatorItem)
    - def __init__(self)
  - def __init__(self)
  - def add_line(self, path, start, end, color, thickness)
  - def add_label(self, path, text, color, size, transform)
  - def destroy(self)
