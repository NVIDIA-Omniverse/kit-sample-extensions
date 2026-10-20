# omni.usd.metrics.assembler.usdgeom

Custom Metrics Assembler resolve rules for `UsdGeom` scene-unit attributes.

This extension registers per-attribute scaling rules with the core Metrics
Assembler so that `UsdGeomCamera` attributes which are explicitly defined in
*scene units* (per the
[UsdGeomCamera schema](https://openusd.org/release/api/class_usd_geom_camera.html))
are converted correctly when a USD layer authored in different units is
referenced, sublayered, or payloaded into a stage.

## Rules registered

| Attribute        | metersExponent | kilogramsExponent |
|------------------|----------------|-------------------|
| `focusDistance`  | 1              | 0                 |
| `clippingRange`  | 1              | 0                 |

`focalLength`, `horizontalAperture`, `verticalAperture` and their `*Offset`
counterparts are documented as *tenths of stage unit* and are corrected by the
renderer; they are intentionally *not* registered here.

## Why this is needed

Without this extension, dragging a camera authored in meters into a stage in
centimeters leaves `focusDistance` and `clippingRange` with their original
numeric value, which produces wrong focus / clipping in any consumer that
reads scene units (NVBugs 5494562 / OMPE-61911).
