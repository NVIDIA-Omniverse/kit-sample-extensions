# Omni.UI Scene Sample Object Info Extension

<p align="center">
  <img src="readme-assets/hero_image.gif" width=100% />
</p>

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Interacting with the Solution](#interacting-with-the-solution)
- [Implementation Details](#implementation-details)
  - [Object Info Model](#object-info-model)
  - [Object Info Manipulator](#object-info-manipulator)
- [Development](#development)
  - [Understanding the Architecture](#understanding-the-architecture)
  - [Implementing Your Own Info Display](#implementing-your-own-info-display)
  - [Best Practices](#best-practices)
  - [Common Use Cases](#common-use-cases)
- [License](#license)
- [Contributing](#contributing)

## Overview
The Omni.UI Scene Sample Object Info extension demonstrates how to create custom manipulators that display information about selected objects in the viewport. This extension provides a practical example of implementing non-interactive manipulators that show object metadata with leader lines.

## Key Features

- **Object Information Display**: Shows object path and material assignment
- **Leader Line Visualization**: Connects information to the object's position
- **Camera-Facing Labels**: Text always faces the camera for readability
- **Real-time Updates**: Information updates with selection changes
- **USD Integration**: Seamless integration with USD stage and prims

## Interacting with the Solution

1. Launch your Omniverse application
2. Select any object in your scene
3. The manipulator will appear, showing:
   - A leader line from the object's top to the information
   - The object's USD path
   - The object's material assignment
4. The information updates automatically when:
   - A different object is selected
   - The object's material changes
   - The object's position changes

## Implementation Details

### Object Info Model
The extension implements a custom model that tracks object information:

```python
class ObjectInfoModel(sc.AbstractManipulatorModel):
    def __init__(self):
        super().__init__()
        self._prim = None
        self._current_path = ""
        self._material_name = ""
        self.position = ObjectInfoModel.PositionItem()

    def get_item(self, identifier):
        if identifier == "position":
            return self.position
        if identifier == "name":
            return self._current_path
        if identifier == "material":
            return self._material_name
```

### Object Info Manipulator
The manipulator provides visual representation of the information:

```python
class ObjectInfoManipulator(sc.Manipulator):
    def on_build(self):
        if not self.model or self.model.get_item("name") == "":
            return

        position = self.model.get_as_floats(self.model.get_item("position"))
        with sc.Transform(transform=sc.Matrix44.get_translation_matrix(*position)):
            with sc.Transform(look_at=sc.Transform.LookAt.CAMERA):
                # Leader lines and text labels
                sc.Arc(LEADER_LINE_CIRCLE_RADIUS, axis=2, color=cl.yellow)
                sc.Line([0, 0, 0], [0, LEADER_LINE_SEGMENT_LENGTH, 0],
                        color=cl.yellow, thickness=LEADER_LINE_THICKNESS)
                # Add text labels with object info
```

## Development

This sample extension demonstrates how to create custom manipulators for displaying object information. Here's how you can leverage and adapt it for your workflow:

### Understanding the Architecture

The extension is built on several key components:

1. **Model Layer** (`ObjectInfoModel`):
   - Tracks selected object information
   - Manages USD prim references
   - Handles selection changes
   - Computes object positions

2. **Manipulator Layer** (`ObjectInfoManipulator`):
   - Creates visual representation
   - Manages leader lines
   - Handles text layout
   - Ensures camera-facing display

3. **USD Integration**:
   - Tracks selection changes
   - Retrieves object properties
   - Computes bounding boxes
   - Monitors material assignments

### Implementing Your Own Info Display

1. **Create a Custom Model**:
```python
class MyInfoModel(sc.AbstractManipulatorModel):
    def __init__(self):
        super().__init__()
        self._prim = None
        self._current_path = ""
        self.position = MyInfoModel.PositionItem()
        self.custom_info = MyInfoModel.StringItem()

    def get_item(self, identifier):
        if identifier == "position":
            return self.position
        if identifier == "custom_info":
            return self._get_custom_info()
        return None

    def _get_custom_info(self):
        if not self._prim:
            return ""
        # Implement your custom info retrieval
        return "Custom Info"
```

2. **Implement the Manipulator**:
```python
class MyInfoManipulator(sc.Manipulator):
    def on_build(self):
        if not self.model:
            return

        position = self.model.get_as_floats(self.model.get_item("position"))
        with sc.Transform(transform=sc.Matrix44.get_translation_matrix(*position)):
            with sc.Transform(look_at=sc.Transform.LookAt.CAMERA):
                # Create your custom visualization
                sc.Line([0, 0, 0], [0, 20, 0], color=cl.yellow)
                with sc.Transform(transform=sc.Matrix44.get_translation_matrix(25, 20, 0)):
                    with sc.Transform(scale_to=sc.Space.SCREEN):
                        sc.Label(self.model.get_item("custom_info"))
```

### Best Practices

1. **Model Design**:
   - Keep models focused on data management
   - Implement efficient USD queries
   - Handle selection changes properly
   - Cache frequently accessed values

2. **Manipulator Implementation**:
   - Use clear visual hierarchy
   - Ensure text readability
   - Optimize geometry updates
   - Handle edge cases

3. **Visual Design**:
   - Use appropriate colors and thickness
   - Implement clear leader lines
   - Ensure proper text scaling
   - Consider viewport performance

4. **USD Integration**:
   - Monitor relevant USD changes
   - Handle missing or invalid prims
   - Implement proper cleanup
   - Use efficient bounding box calculations

### Common Use Cases

1. **Object Information**:
   - Display object metadata
   - Show material assignments
   - Indicate object states
   - Present custom properties

2. **Visual Indicators**:
   - Status indicators
   - Warning messages
   - Error states
   - Custom annotations

3. **Measurement Display**:
   - Object dimensions
   - Distance measurements
   - Angle indicators
   - Custom metrics

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
"omni.sample.ui_scene.object_info" = {}
```
