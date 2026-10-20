# Commands API for omni.sample.ui_scatter_tool

This extension provides commands for creating USD PointInstancer prims, which are used for efficient instancing of scattered objects.

## ScatterCreatePointInstancer

Creates a USD PointInstancer prim with multiple instances positioned according to the provided transform matrices. This command is undoable and supports efficient scattering of objects in USD scenes.

### Usage

```python
import omni.kit.commands
from pxr import Gf

# Create transform matrices
matrix1 = Gf.Matrix4d(1.0)
matrix1.SetTranslate(Gf.Vec3d(0, 0, 0))

matrix2 = Gf.Matrix4d(1.0)
matrix2.SetTranslate(Gf.Vec3d(100, 0, 0))

matrix3 = Gf.Matrix4d(1.0)
matrix3.SetTranslate(Gf.Vec3d(200, 0, 0))

# Execute the command
omni.kit.commands.execute(
    "ScatterCreatePointInstancer",
    path_to="/World/Scatter01",
    transforms=[
        (matrix1, 0),  # Use first prototype
        (matrix2, 0),  # Use first prototype
        (matrix3, 1),  # Use second prototype
    ],
    prim_names=["/World/SourcePrim1", "/World/SourcePrim2"]
)
```

### Arguments

- `path_to` (str): The USD path where the PointInstancer prim will be created
- `transforms` (List[Tuple[Gf.Matrix4d, int]]): List of tuples containing transform matrices and prototype indices. Each tuple consists of:
  - `Gf.Matrix4d`: The 4x4 transformation matrix. **Note**: While the command accepts full transformation matrices, only the translation component is used. The UI's `scatter()` function generates translation-only matrices (no rotation or scale). Rotation and scale components in the matrix are ignored.
  - `int`: The index into `prim_names` indicating which prototype to use for this instance
- `prim_names` (List[str]): List of USD prim paths that serve as prototypes for the PointInstancer. These prims will be referenced by the PointInstancer
- `stage` (Optional[Usd.Stage]): Optional USD stage. If not provided, uses the current stage from the USD context
- `context_name` (Optional[str]): Optional context name for stage resolution. If not provided, uses the default context

### Details

- **Undoable**: Yes - The command supports undo/redo operations
- **Performance**: PointInstancer is the recommended method for scattering large numbers of objects (>100 instances) as it provides better performance than copying or referencing prims individually
- **Transform Extraction**: The command extracts **only the translation component** from the transform matrices to set the `positions` attribute of the PointInstancer. Rotation and scale components are ignored.
- **Prototype Indices**: The integer values in the transforms tuples are used to index into the `prim_names` list, allowing different prototypes to be used for different instances
- **UI Behavior**: The scatter tool UI only generates translation matrices (position-only transforms). It does not provide controls for rotation or scale.

### Example: Scattering Objects in a Grid

```python
import omni.kit.commands
from pxr import Gf

# Generate transforms for a 5x5x1 grid
transforms = []
for x in range(5):
    for y in range(5):
        matrix = Gf.Matrix4d(1.0)
        matrix.SetTranslate(Gf.Vec3d(x * 100, y * 100, 0))
        transforms.append((matrix, 0))  # Use first prototype for all instances

omni.kit.commands.execute(
    "ScatterCreatePointInstancer",
    path_to="/World/GridScatter",
    transforms=transforms,
    prim_names=["/World/MyObject"]
)
```

### Related Functions

This command is typically used in conjunction with the `scatter()` function from `omni.sample.ui_scatter_tool.scatter`, which generates transform matrices based on scatter parameters (count, distance, randomization, seed).
