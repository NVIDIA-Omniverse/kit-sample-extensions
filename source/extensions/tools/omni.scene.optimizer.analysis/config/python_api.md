# Public API for module omni.scene.optimizer.analysis:

## Classes

- class OperationConfig
  - def __init__(self, name: str, args: dict = None)
  - [property] def name(self)
  - [property] def args(self)

## Functions

- def analyze(stage: Usd.Stage, operations: list, context: ExecutionContext = None)
- def create_operations_from_analysis_result(analysis_result: dict)
- def get_iface()
- def optimize(stage: Usd.Stage, operations: list, context: ExecutionContext = None)
