# Scatter Tool (omni.sample.ui_scatter_tool)

## Overview

This Extension creates a new UI and function to `Scatter` a selected primitive along the X, Y, and Z axes. The user can set parameters for Object Count, Distance, and Randomization.

## Features

- **Multiple Scatter Modes**: Choose between Copy, Reference, or PointInstancer modes
- **Performance Optimization**: Automatic warnings and limits for large scatter operations
- **3D Control**: Independent control over X, Y, and Z axes
- **Randomization**: Add random positioning to create more natural distributions
- **Seed Control**: Reproducible results with seed values

## Usage

Once the extension is enabled in the `Extension Manager`, the `Scatter Window` will appear. You may dock this window or keep it floating in the viewport.

1. Select your primitive in the hierarchy that you want to scatter
2. Click the `S` button next to the `Source > Prim` field to set the selected primitive
3. Configure your scatter properties:
   - **Prim Path**: The target location for scattered objects
   - **Prim Type**: Choose between Copy, Reference, or PointInstancer (recommended for >100 objects)
   - **Seed**: Set a seed value for reproducible randomization
   - **Per-Axis Settings**:
     - Object Count: Number of objects to create along each axis
     - Distance: Spacing between objects
     - Random: Amount of random offset to apply
4. Click the `Scatter` button to create the scattered objects

## Performance Considerations

- For scattering **fewer than 100 objects**: Any mode works well
- For scattering **100-500 objects**: Use Reference mode or PointInstancer
- For scattering **more than 500 objects**: PointInstancer mode is required

The extension will automatically warn you about performance implications and block operations that would freeze Kit.

## Technical Details

This extension demonstrates:
- Omniverse UI framework usage
- USD scene manipulation
- PointInstancer creation for efficient object scattering
- Async processing for large operations
- Custom command implementation with undo support
