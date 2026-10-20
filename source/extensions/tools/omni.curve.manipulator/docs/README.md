# Curve Manipulation [omni.curve.manipulator]

Extension to visualize CVs on UsdGeomBasisCurves prim and the ability to manipulate them within viewport.

## Manipulation/Editing exiting CV
Before starting, making sure the "Drawing" icon in "Curve" floating window is de-activated, to put the tool in editing mode. Only in the mode can you see the manipulation handles for tangents and CVs, and be able to right click on them to see context menu.

If the UsdGeomBasisCurves is cubic bezier curve, additional manipulations are added to the context menu of the CV:
- Break Anchor Tangents
- Smooth Anchor Tangents
- Even Anchor Tangents
- Uneven Anchor Tangents
- Delete CV(s) (only for non-tangent CV)
- Delete and Split at CV(s) (only for non-tangent CV)
- Delete and Split at CV(s) to new BasisCurves (only for non-tangent CV)
- Split at CV(s) (only for non-tangent CV)
- Split at CV(s) to new BasisCurves (only for non-tangent CV)
- Bezier
- Bezier Corner
- Corner
- Open/Close Curve(s)

Depending on the state of the curves, manipulating the anchor and tangents will behave accordingly. Scale or rotate the anchor CV affects its tangents CVs.

If UsdGeomBasisCurves is of other basis (bspline or catmullRom), only translation can be manipulated. No tangent manipulation is offered. Support of linear curve editing is also limited.

If the curve has "wrap" attribute is set to "periodic", manipulation bezier curve's tangent on the first or last CV will be handled repeatedly. If the curve doesn't have correct number of CVs to be periodic, the tool will try to fix them upon editing starts.

Multiple curves in one UsdGeomBasisCurves is supported.

Multiple CVs across multiple UsdGeomBasisCurves can be manipulated at the same time.

## Authoring New CV
Before starting, making sure the "Drawing" icon in "Curve" floating window is activated, to put the tool in authoring  mode.

To add a CV along existing curve, hover mouse near curve to sample a point along it, and click to insert a new CV while keeping original shape of the curve.

To append a CV to the end of existing curve, click (or click and drag to create tangents) on empty space to append new CV. If Perspective camera or user defined camera is selected, the new point is sampled on the floor plane (XZ for Y-up stage and XY for Z-up stage). If a built-in orthographic camera (Top, Front, Right) is selected, the point is sampled on the corresponding plane. If mouse ray doesn't not hit the desired plane, no CV will be added.

To start a new curve within the same BasisCurves prim, hold SHIFT while clicking/dragging on empty space.

Press "Enter" or right click and choose "Stop Editing Control Vertices" to exit Curve Editing mode.

## Bezier Curve Creation with CV and Tangent

You can create a Bezier Curve (backed by UsdGeomBasisCurve) from scratch by going to "Create" -> "BasisCurves" -> "New Curve". It will create a UsdGeomBasisCurve prim, set it to bezier and enter curve editing mode. From then on you can follow `Curve Manipulation/Editing` section to add and edit CVs.
When in authoring mode, the floating Curve window will have the following settings:
- Interpolate Mode:
    - `linear`: Creates curve that linearly interpolates between CVs. The UsdGeomBasisCurve will have linear type and no tangent CV is added.
    - `cubic`: Creates cubic bezier curve. The UsdGeomBasisCurve will have cubic type with tangent CVs.

## Bezier Curve Creation with Pencil Tool
Alternatively, after creating a new curve from the Create menu, you can change the mode from `Bezier` to `Freehand` to draw on screen and let it resample the stroke and creates a bezier curve out of it. When `Freehand` mode is enabled, the floating Curve window will have the following additional settings:
- Spacing: The distance (in world unit) between each CV when resampling the stroke. The smaller the spacing is, the more accurate it is to original stroke, with more CV sampled.

"Freehand" mode finalizes the curve as soon as drawing mouse button is released. To edit a drawn curve, right click and enable curve editing mode.

## Create Curve with Snapping
To have curve/CV snap to various target (e.g. geometry surface, grid, edge, etc.) while creating with either `Bezier` or `Freehand` mode, enable any Snap option on Main Toolbar (the same one that controls transform manipulator snapping to surface). You may need to put the Manipulator into Move (W) mode to see full list of snap options.
