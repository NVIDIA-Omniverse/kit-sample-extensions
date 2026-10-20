# Public API for module omni.sample.ui_scatter_tool:

## Classes

- class ScatterCreatePointInstancerCommand(omni.kit.commands.Command, omni.usd.commands.stage_helper.UsdStageHelper)
  - def __init__(self, path_to: str, transforms: List[Tuple[Gf.Matrix4d, int]], prim_names: List[str], stage: Optional[Usd.Stage] = None, context_name: Optional[str] = None)
  - def do(self)
  - def undo(self)
