# Metrics Assembler

The Metrics Assembler resolves unit divergency in composed USD stages. When a USD stage references layers authored in different units (e.g., meters vs. centimeters), the assembler detects and resolves these differences so that all geometry and attributes are expressed consistently in the stage's root units.

## Overview

USD stages can compose layers that were authored with different `metersPerUnit`, `kilogramsPerUnit`, or `upAxis` settings. Without resolution, a mesh authored in meters that is referenced into a centimeter stage would appear 100x too small. The Metrics Assembler handles this by:

1. **Detecting divergency** - comparing each composed layer's units against the stage root units.
2. **Resolving xformOps** - applying scale corrections to transform operations on top-level divergent prims so geometry appears at the correct size.
3. **Resolving attributes** - scaling attribute values using custom rules that define how each attribute relates to meters and kilograms.

## Performance

When no custom rules or callbacks are registered, the assembler only resolves xformOps on top-level divergent prims and skips deep hierarchy traversal. This means the expensive per-prim composition arc queries and attribute iteration are avoided for subtrees where no attribute resolution would occur.

## Settings

| Setting | Type | Description |
|---------|------|-------------|
| `/metricsAssembler/operationMode` | int | `0`=Disabled, `1`=Warn, `2`=Ask, `3`=Auto |
| `/metricsAssembler/changeListenerEnabled` | bool | Enable/disable the parameter change listener |
| `/metricsAssembler/conformToXformCommonAPI` | bool | If true, uses XformCommonAPI to adjust the xformOp stack instead of adding additional xformOps with unitsResolve suffix |

## Python API

### Acquiring the Interface

```python
from omni.metrics.assembler.core import get_metrics_assembler_interface

metrics = get_metrics_assembler_interface()
```

### Checking for Divergency

Use `check_stage` to detect whether any composed layers have different units from the stage root:

```python
from pxr import Usd, UsdGeom, UsdPhysics, UsdUtils

stage = Usd.Stage.CreateInMemory()

# Configure stage units
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(stage, 0.01)  # centimeters
UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)

# Insert into stage cache (required for the assembler)
cache = UsdUtils.StageCache.Get()
cache.Insert(stage)
stage_id = cache.GetId(stage).ToLongInt()

# Add a reference to a layer authored in meters
xform = UsdGeom.Xform.Define(stage, "/World/ref")
xform.GetPrim().GetReferences().AddReference("asset_in_meters.usda")

# Check for divergency
is_divergent = metrics.check_stage(stage_id)
# Returns True - the referenced layer uses meters, stage uses centimeters
```

You can also compare two specific layers:

```python
root_layer = stage.GetRootLayer()
for layer in stage.GetUsedLayers():
    result = metrics.check_layers(root_layer.identifier, layer.identifier, stage_id)
    if result["ret_val"]:
        print(f"Divergent: {layer.identifier}")
        print(f"  Root units: {result['units_info0']}")
        print(f"  Layer units: {result['units_info1']}")
```

### Resolving a Stage

Resolve all divergent units across the entire stage:

```python
was_divergent = metrics.resolve_stage(stage_id)
```

Or resolve only a specific subtree:

```python
was_divergent = metrics.resolve_hierarchy(stage_id, "/World/ref")
```

Both methods return `True` if divergent units were found. Without any custom rules registered, only xformOp corrections are applied to top-level divergent prims. To also resolve attribute values, register custom rules (see below).

### Writing Resolved Changes to a Specific Layer

By default, resolved values are written to the strongest layer that defines each attribute. You can redirect all changes to a specific layer (e.g., the session layer):

```python
session_layer = stage.GetSessionLayer()
metrics.set_resolve_layer(session_layer.identifier)

metrics.resolve_stage(stage_id)

# Reset to default behavior
metrics.set_resolve_layer(None)
```

### Changing Stage Units

Change the units of an entire stage, transforming all existing values to match the new units:

```python
from omni.metrics.assembler.core.bindings._metricsAssembler import UnitsInfo

new_units = UnitsInfo()
new_units.meters_per_unit = 1.0      # switch to meters
new_units.kilograms_per_unit = 1.0
new_units.up_axis = "Z"              # switch to Z-up

metrics.change_stage_units(stage_id, new_units)
```

> **Note:** This operation is destructive and writes to the current active target layer. It uses the XformCommonAPI for xformOp stack transformation.

## Custom Resolve Rules

Custom resolve rules tell the assembler how to scale specific attribute values when units diverge. Without rules, only xformOp corrections are applied.

### The Rule Formula

When a rule is registered for an attribute, the assembler applies this formula:

```
resolvedValue = value * (MPU / stageMPU) ^ metersExponent * (KGPU / stageKGPU) ^ kilogramsExponent
```

Where:
- **value** - the original attribute value
- **MPU** - the metersPerUnit of the divergent layer where the attribute is authored
- **stageMPU** - the metersPerUnit of the stage root
- **KGPU** - the kilogramsPerUnit of the divergent layer
- **stageKGPU** - the kilogramsPerUnit of the stage root
- **metersExponent** - defines how the attribute scales with length (registered with the rule)
- **kilogramsExponent** - defines how the attribute scales with mass (registered with the rule)

### Exponent Examples

| Attribute type | metersExponent | kilogramsExponent | Reasoning |
|---------------|----------------|-------------------|-----------|
| Length (distance, radius) | 1 | 0 | Scales linearly with meters |
| Area | 2 | 0 | Scales with meters squared |
| Volume | 3 | 0 | Scales with meters cubed |
| Velocity | 1 | 0 | m/s, length per time |
| Acceleration | 1 | 0 | m/s^2, length per time squared |
| Force | 1 | 1 | kg * m/s^2 |
| Density | -3 | 1 | kg/m^3 |
| No scaling needed | 0 | 0 | Dimensionless values (angles, ratios) |

### Registering a Rule

```python
# Register a rule for a custom length attribute
rule_id = metrics.register_custom_resolve_rule(
    attribute_name="myNamespace:distance",
    meters_exponent=1,
    kilograms_exponent=0
)

# Register a rule for a density attribute
density_rule_id = metrics.register_custom_resolve_rule(
    attribute_name="myNamespace:density",
    meters_exponent=-3,
    kilograms_exponent=1
)
```

After registration, calling `resolve_stage` or `resolve_hierarchy` will apply these rules to matching attributes on divergent prims.

### Unregistering a Rule

```python
metrics.unregister_custom_resolve_rule(rule_id)
```

### Full Example: Custom Attribute Resolution

```python
from pxr import Usd, UsdGeom, UsdPhysics, UsdUtils
from omni.metrics.assembler.core import get_metrics_assembler_interface

metrics = get_metrics_assembler_interface()

# Setup stage in centimeters
stage = Usd.Stage.CreateInMemory()
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(stage, 0.01)  # cm
UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)

cache = UsdUtils.StageCache.Get()
cache.Insert(stage)
stage_id = cache.GetId(stage).ToLongInt()

# Register a rule for a custom attribute (scales linearly with meters)
ATTR_NAME = "myNamespace:myDistance"
rule_id = metrics.register_custom_resolve_rule(ATTR_NAME, 1, 0)

# Reference a layer authored in meters
xform = UsdGeom.Xform.Define(stage, "/World/ref")
xform.GetPrim().GetReferences().AddReference("asset_in_meters.usda")

# Before resolve: attribute has original value (e.g., 1.0 meaning 1 meter)
prim = stage.GetPrimAtPath("/World/ref/MyPrim")
attr = prim.GetAttribute(ATTR_NAME)
print(f"Before: {attr.Get()}")  # 1.0

# Resolve
metrics.resolve_stage(stage_id)

# After resolve: value scaled to centimeters
# resolvedValue = 1.0 * (1.0 / 0.01)^1 = 100.0
print(f"After: {attr.Get()}")   # 100.0

# Cleanup
metrics.unregister_custom_resolve_rule(rule_id)
```

## Custom Callbacks

Callbacks provide fine-grained control over the resolve process. They allow you to intercept and modify resolution at the prim and attribute level.

### Callback Functions

There are four callback function types:

| Callback | Signature | Description |
|----------|-----------|-------------|
| `resolve_start_fn` | `(stage_id)` | Called once before traversal begins |
| `resolve_end_fn` | `(stage_id)` | Called once after traversal ends |
| `resolve_prim_fn` | `(prim_path, stage_units, resolve_units) -> bool` | Called for each divergent prim. Return `False` to skip the prim entirely |
| `resolve_attribute_fn` | `(prim_path, attr_name, stage_units, resolve_units, meters_exp, kg_exp) -> (bool, meters_exp, kg_exp)` | Called for each attribute. Return a tuple: `(continue, meters_exponent, kilograms_exponent)`. Set `continue` to `False` to skip the attribute, or modify the exponents to override the rule |

Any callback can be `None` if not needed.

### Attribute Token Filtering

For performance, you can specify which attributes should trigger the `resolve_attribute_fn` callback. Without filtering, the callback is invoked for every authored attribute on every divergent prim.

```python
# Only call resolve_attribute_fn for these specific attributes
reg_id = metrics.register_custom_callback(
    None, None, None, my_resolve_fn,
    ["myNamespace:distance", "myNamespace:area"]
)
```

### Example: Overriding an Attribute Rule via Callback

```python
MY_ATTR = "myNamespace:distance"

def resolve_attribute(prim_path, attr_name, stage_units, resolve_units,
                      meters_exponent, kilograms_exponent):
    if attr_name == MY_ATTR:
        # Override: use inverse scaling for this attribute
        return (True, -1, kilograms_exponent)

    # Use default rule for everything else
    return (True, meters_exponent, kilograms_exponent)

reg_id = metrics.register_custom_callback(
    None,               # resolve_start_fn
    None,               # resolve_end_fn
    None,               # resolve_prim_fn
    resolve_attribute,  # resolve_attribute_fn
    [MY_ATTR]           # attribute filter
)

metrics.resolve_stage(stage_id)

metrics.unregister_custom_callback(reg_id)
```

### Example: Skipping Specific Prims

```python
def resolve_prim(prim_path, stage_units, resolve_units):
    # Skip prims under a specific hierarchy
    if prim_path.startswith("/World/NoResolve"):
        return False
    return True

reg_id = metrics.register_custom_callback(
    None, None, resolve_prim, None
)

metrics.resolve_stage(stage_id)

metrics.unregister_custom_callback(reg_id)
```

### Example: Full Callback with Start/End Tracking

```python
class ResolveTracker:
    def __init__(self):
        self.num_prims = 0
        self.num_attributes = 0

    def on_start(self, stage_id):
        print(f"Resolve started for stage {stage_id}")

    def on_end(self, stage_id):
        print(f"Resolve ended: {self.num_prims} prims, {self.num_attributes} attributes")

    def on_prim(self, prim_path, stage_units, resolve_units):
        self.num_prims += 1
        return True

    def on_attribute(self, prim_path, attr_name, stage_units, resolve_units,
                     meters_exp, kg_exp):
        self.num_attributes += 1
        return (True, meters_exp, kg_exp)

tracker = ResolveTracker()
reg_id = metrics.register_custom_callback(
    tracker.on_start,
    tracker.on_end,
    tracker.on_prim,
    tracker.on_attribute
)

metrics.resolve_stage(stage_id)

metrics.unregister_custom_callback(reg_id)
```
