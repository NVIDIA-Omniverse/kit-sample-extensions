# Omni.UI Scene Sample Slider Extension

<p align="center">
  <img src="readme-assets/hero_image.gif" width=100% />
</p>

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Interacting with the Solution](#interacting-with-the-solution)
- [Implementation Details](#implementation-details)
  - [Slider Model](#slider-model)
  - [Slider Manipulator](#slider-manipulator)
- [Development](#development)
  - [Understanding the Architecture](#understanding-the-architecture)
  - [Implementing Your Own Slider](#implementing-your-own-slider)
  - [Best Practices](#best-practices)
  - [Common Use Cases](#common-use-cases)
- [License](#license)
- [Contributing](#contributing)

## Overview
The Omni.UI Scene Sample Slider extension demonstrates how to create interactive manipulators that allow users to adjust object properties directly in the viewport. This extension provides a practical example of implementing a slider manipulator that can modify the scale of selected objects through drag gestures.

## Key Features

- **Interactive Slider Control**: Drag-based manipulation of object properties
- **Real-time Visual Feedback**: Dynamic slider visualization with value display
- **Hover Effects**: Visual feedback when interacting with the slider
- **Custom Gesture System**: Implementation of drag gestures with priority handling
- **USD Integration**: Seamless integration with USD stage and prims

## Interacting with the Solution

1. Launch your Omniverse application
2. Select any object in your scene
3. The slider manipulator will appear above the object, showing:
   - A horizontal slider bar
   - A draggable handle
   - The current value display
4. Interact with the slider by:
   - Dragging the handle to adjust the object's scale
   - Hovering over the handle to see visual feedback
   - Viewing the current value above the handle

## Implementation Details

### Slider Model
The extension implements a custom model that tracks object properties:

```python
class SliderModel(sc.AbstractManipulatorModel):
    def __init__(self):
        super().__init__()
        self.scale = SliderModel.ValueItem()
        self.min = SliderModel.ValueItem()
        self.max = SliderModel.ValueItem(1)
        self.position = SliderModel.PositionItem()

    def get_item(self, identifier):
        if identifier == "value":
            return self.scale
        if identifier == "position":
            return self.position
        if identifier == "min":
            return self.min
        if identifier == "max":
            return self.max
```

### Slider Manipulator
The manipulator provides interactive control:

```python
class SliderManipulator(sc.Manipulator):
    def on_build(self):
        if not self.model:
            return

        value = float(self.model.get_as_floats(self.model.get_item("value"))[0])
        value_normalized = (value - _min) / (_max - _min)
        position = self.model.get_as_floats(self.model.get_item("position"))

        with sc.Transform(transform=sc.Matrix44.get_translation_matrix(*position)):
            # Draw slider track
            sc.Line([line_from, 0, 0], [line_to, 0, 0], 
                    color=cl.darkgray, thickness=self.thickness)
            
            # Draw slider handle
            with sc.Transform(transform=sc.Matrix44.get_translation_matrix(
                    circle_position, 0, 0)):
                sc.Arc(radius, axis=2, color=cl.gray, gestures=gestures)
                
                # Draw value label
                with sc.Transform(look_at=sc.Transform.LookAt.CAMERA):
                    sc.Label(f"{value:.1f}")
```

## Development

This sample extension demonstrates how to create interactive manipulators for adjusting object properties. Here's how you can leverage and adapt it for your workflow:

### Understanding the Architecture

The extension is built on several key components:

1. **Model Layer** (`SliderModel`):
   - Tracks object properties
   - Manages value ranges
   - Handles selection changes
   - Computes positions

2. **Manipulator Layer** (`SliderManipulator`):
   - Creates visual representation
   - Implements drag gestures
   - Handles user interaction
   - Updates visual feedback

3. **Gesture System**:
   - Custom drag gesture implementation
   - Gesture priority management
   - Event handling
   - Value calculation

### Implementing Your Own Slider

1. **Create a Custom Model**:
```python
class MySliderModel(sc.AbstractManipulatorModel):
    def __init__(self):
        super().__init__()
        self.value = MySliderModel.ValueItem()
        self.min = MySliderModel.ValueItem()
        self.max = MySliderModel.ValueItem(1)
        self.position = MySliderModel.PositionItem()

    def get_item(self, identifier):
        if identifier == "value":
            return self.value
        if identifier == "position":
            return self.position
        return None
```

2. **Implement the Manipulator**:
```python
class MySliderManipulator(sc.Manipulator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._width = 100
        self._thickness = 5
        self._radius = 5

    def on_build(self):
        if not self.model:
            return

        value = self.model.get_as_floats(self.model.get_item("value"))[0]
        position = self.model.get_as_floats(self.model.get_item("position"))

        with sc.Transform(transform=sc.Matrix44.get_translation_matrix(*position)):
            # Create your custom slider visualization
            sc.Line([-self._width/2, 0, 0], [self._width/2, 0, 0], 
                    color=cl.darkgray, thickness=self._thickness)
            with sc.Transform(transform=sc.Matrix44.get_translation_matrix(
                    value * self._width - self._width/2, 0, 0)):
                sc.Arc(self._radius, axis=2, color=cl.gray)
```

### Best Practices

1. **Model Design**:
   - Keep models focused on data management
   - Implement proper value constraints
   - Handle selection changes efficiently
   - Cache frequently accessed values

2. **Manipulator Implementation**:
   - Use clear visual hierarchy
   - Implement smooth interactions
   - Optimize geometry updates
   - Handle edge cases

3. **Gesture Handling**:
   - Implement proper gesture priorities
   - Handle gesture state changes
   - Provide clear feedback
   - Consider performance

4. **Visual Design**:
   - Use appropriate colors and sizes
   - Implement clear visual feedback
   - Ensure proper value display
   - Consider viewport performance

### Common Use Cases

1. **Property Adjustment**:
   - Scale modification
   - Parameter control
   - Value ranges
   - Custom properties

2. **Interactive Controls**:
   - Slider widgets
   - Value pickers
   - Range selectors
   - Custom manipulators

3. **Visual Feedback**:
   - Value display
   - State indicators
   - Progress visualization
   - Custom annotations

## License

Development using the Omniverse Kit SDK is subject to the licensing terms detailed [here](https://docs.omniverse.nvidia.com/install-guide/latest/common/NVIDIA_Omniverse_License_Agreement.html).

This project will download and install additional third-party open source software projects. Review the license terms of these open source projects before use.

## Contributing

We provide this source code as-is and are currently not accepting outside contributions.

## Sample usage

### Setup
If using from a local path through the extension manager, add the path to the extension samples directory in your application `.kit` file via 

```toml
[settings.app.exts]
folders.'++' = [  # Search paths for extensions.
	"${app}/../exts",
	"${app}/../extscache/",
	"<full path to the extension samples source/extensions directory>"
]
```

If using from an extension registry add the extension to the application `.kit` file to the list of dependencies. 

```toml
[dependencies]
"omni.sample.ui_scene.slider_manipulator" = {}
```




