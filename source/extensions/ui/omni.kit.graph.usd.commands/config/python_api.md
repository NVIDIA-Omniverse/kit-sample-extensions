# Public API for module omni.kit.graph.usd.commands:

## Classes

- class CreateUsdUIBackdropCommand(omni.kit.commands.Command, UsdStageHelper)
  - def __init__(self, parent_path: Sdf.Path, identifier: str, position: Optional[Tuple[float]] = None, size: Optional[Tuple[float]] = None, display_color: Optional[Tuple[float]] = None, stage: Optional[Usd.Stage] = None)
  - def do(self)
  - def undo(self)

- class CreateUsdUINoteCommand(omni.kit.commands.Command, UsdStageHelper)
  - def __init__(self, parent_path: Sdf.Path, identifier: str, position: Optional[Tuple[float]] = None, size: Optional[Tuple[float]] = None, display_color: Optional[Tuple[float]] = None, stage: Optional[Usd.Stage] = None)
  - def do(self)
  - def undo(self)

- class UsdUINodeGraphNodeSetCommand(omni.kit.commands.Command, UsdStageHelper)
  - def __init__(self, attribute: str, prim_path: Sdf.Path, value, prev, stage: Usd.Stage = None)
  - def do(self)
  - def undo(self)

- class UsdUIRemovePositionCommand(omni.kit.commands.Command, UsdStageHelper)
  - def __init__(self, prim_path: Sdf.Path, stage: Usd.Stage = None)
  - def do(self)
  - def undo(self)
