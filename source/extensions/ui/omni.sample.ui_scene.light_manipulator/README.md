# Omni.UI Scene Sample For Manipulating Select Light Extension

<p align="center">
  <img src="readme-assets/hero_image.gif" width=100% />
</p>

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Interacting with the Solution](#interacting-with-the-solution)
- [Implementation Details](#implementation-details)
  - [Light Model](#light-model)
  - [Light Manipulator](#light-manipulator)
- [Development](#development)
  - [Understanding the Architecture](#understanding-the-architecture)
  - [Implementing Your Own Manipulator](#implementing-your-own-manipulator)
  - [Best Practices](#best-practices)
  - [Common Use Cases](#common-use-cases)
- [License](#license)
- [Contributing](#contributing)

## Overview
The Omni.UI Scene Sample For Manipulating Select Light extension demonstrates how to create custom manipulators for USD lights in Omniverse Kit. This extension provides a practical example of implementing interactive 3D manipulators that allow users to directly manipulate light properties in the viewport.

## Key Features

- **Interactive Light Manipulation**: Direct manipulation of light properties in the viewport
- **Custom Manipulator**: Visual representation of light dimensions and intensity
- **Real-time Updates**: Immediate visual feedback during manipulation
- **Undo/Redo Support**: All manipulations support undo/redo operations
- **USD Integration**: Seamless integration with USD stage and light prims

## Interacting with the Solution

1. Launch your Omniverse application
2. Select a RectLight in your scene
3. The manipulator will appear, showing:
   - Rectangle outline representing light dimensions
   - Arrows indicating intensity direction
   - Interactive handles for width, height, and intensity
4. Interact with the manipulator:
   - Drag horizontal edges to adjust width
   - Drag vertical edges to adjust height
   - Drag intensity arrows to adjust light intensity

## Implementation Details

### Light Model
The extension implements a custom model that tracks light attributes:

```python
class LightModel(sc.AbstractManipulatorModel):
    def __init__(self):
        super().__init__()
        self.prim_path = LightModel.StringItem()
        self.transform = LightModel.MatrixItem()
        self.intensity = LightModel.FloatItem()
        self.width = LightModel.FloatItem()
        self.height = LightModel.FloatItem()
```

### Light Manipulator
The manipulator provides visual representation and interaction:

```python
class LightManipulator(sc.Manipulator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._shape_xform = None

    def on_build(self):
        # Build the manipulator's visual representation
        # and attach gesture handlers
```

## Development

This sample extension demonstrates how to create custom manipulators for USD prims. Here's how you can leverage and adapt it for your workflow:

### Understanding the Architecture

The extension is built on several key components:

1. **Model Layer** (`LightModel`):
   - Manages the data state of the manipulator
   - Tracks USD prim attributes
   - Handles selection changes
   - Provides undo/redo support

2. **Manipulator Layer** (`LightManipulator`):
   - Creates visual representation
   - Handles user interaction
   - Manages gesture events
   - Updates USD prim attributes

3. **Gesture System** (`_DragGesture`):
   - Implements custom drag behavior
   - Handles transform calculations
   - Manages gesture state
   - Coordinates with USD updates

### Implementing Your Own Manipulator

1. **Create a Custom Model**:
```python
class MyPrimModel(sc.AbstractManipulatorModel):
    def __init__(self):
        super().__init__()
        # Track prim path
        self.prim_path = MyPrimModel.StringItem()
        # Track transform
        self.transform = MyPrimModel.MatrixItem()
        # Track your custom attributes
        self.my_attribute = MyPrimModel.FloatItem()

    def get_as_floats(self, item):
        """Get values from USD"""
        if item == self.transform:
            return self._get_transform(self._time)
        if item == self.my_attribute:
            return self._get_my_attribute(self._time)
        return None

    def set_floats_commands(self, item, value):
        """Update USD with undo/redo support"""
        if not self._current_path:
            return
        # Implement your attribute updates
        if item == self.my_attribute:
            prev_value = self.my_attribute.value
            if prev_value == value:
                return
            attr = self._prim.GetMyAttributeAttr()
            omni.kit.commands.execute('ChangeProperty',
                                    prop_path=attr.GetPath(),
                                    value=value,
                                    prev=prev_value)
```

2. **Implement the Manipulator**:
```python
class MyPrimManipulator(sc.Manipulator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._shape_xform = None

    def on_build(self):
        """Build the manipulator's visual representation"""
        model = self.model
        if not model or not model.prim_path.value:
            return

        # Create transform hierarchy
        self.__root_xf = sc.Transform(model.get_as_floats(model.transform))
        with self.__root_xf:
            self._x_xform = sc.Transform()
            with self._x_xform:
                self._shape_xform = sc.Transform()
                # Build your custom shape
                with self._shape_xform:
                    # Add your visual elements
                    shape = sc.Line((0, 0, 0), (1, 1, 1),
                                  thickness=1,
                                  color=cl.yellow)
                    # Add gesture handlers
                    shape.gestures = [
                        _DragGesture(self, [0], [1]),
                        sc.HoverGesture(
                            on_began_fn=lambda s: self._handle_hover_begin(s),
                            on_ended_fn=lambda s: self._handle_hover_end(s)
                        )
                    ]
```

3. **Implement Custom Gestures**:
```python
class _DragGesture(sc.DragGesture):
    def __init__(self, manipulator, orientation, flag):
        super().__init__()
        self._manipulator = manipulator
        self._previous_ray_point = None
        self.orientations = orientation
        self.flag = flag

    def on_began(self):
        """Initialize gesture state"""
        self._previous_ray_point = self.gesture_payload.ray_closest_point
        # Record initial values
        self.model = self._manipulator.model
        self.initial_value = self.model.get_as_floats(self.model.my_attribute)

    def on_changed(self):
        """Handle drag movement"""
        # Calculate movement
        current_point = self.gesture_payload.ray_closest_point
        moved = [a - b for a, b in zip(current_point, self._previous_ray_point)]

        # Transform to object space
        moved = self._manipulator._x_xform.transform_space(
            sc.Space.WORLD,
            sc.Space.OBJECT,
            moved + [0]
        )

        # Update values
        new_value = self.initial_value + moved[0] * self.flag[0]
        self.model.set_floats(self.model.my_attribute, new_value)

        self._previous_ray_point = current_point

    def on_ended(self):
        """Finalize changes with undo/redo support"""
        self.model.set_floats_commands(
            self.model.my_attribute,
            self.model.get_as_floats(self.model.my_attribute)
        )
```

### Best Practices

1. **Model Design**:
   - Keep models focused on data management
   - Implement proper USD attribute tracking
   - Support undo/redo operations
   - Handle selection changes efficiently
   - Cache frequently accessed values

2. **Manipulator Implementation**:
   - Use clear visual feedback
   - Implement intuitive gesture controls
   - Handle edge cases and error states
   - Optimize geometry updates
   - Use efficient transform operations

3. **Gesture Handling**:
   - Implement smooth drag operations
   - Provide visual feedback during interaction
   - Handle gesture conflicts appropriately
   - Support multiple gesture types
   - Implement proper cleanup

4. **Performance Optimization**:
   - Minimize geometry updates
   - Use efficient transform operations
   - Implement proper cleanup
   - Cache transform calculations
   - Batch USD updates

### Common Use Cases

1. **Property Manipulation**:
   - Direct manipulation of prim properties
   - Visual feedback for property changes
   - Multi-property coordination
   - Constrained value ranges
   - Custom property types

2. **Transform Control**:
   - Position and orientation control
   - Scale and dimension manipulation
   - Constrained transformations
   - Local vs. world space operations
   - Custom transform types

3. **Custom Visualization**:
   - Property-specific visual indicators
   - Interactive handles and controls
   - State-based visual feedback
   - Custom geometry representation
   - Dynamic visual updates

## License

Development using the Omniverse Kit SDK is subject to the licensing terms detailed [here](https://docs.omniverse.nvidia.com/install-guide/latest/common/NVIDIA_Omniverse_License_Agreement.html).

## Contributing

We provide this source code as-is and are currently not accepting outside contributions.
