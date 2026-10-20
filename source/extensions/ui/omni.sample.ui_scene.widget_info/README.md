# Omni.UI Scene Sample Object Info with Widget Example Extension

<p align="center">
  <img src="readme-assets/hero_image.gif" width=100% />
</p>

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Interacting with the Solution](#interacting-with-the-solution)
- [Implementation Details](#implementation-details)
  - [Widget Info Model](#widget-info-model)
  - [Widget Info Manipulator](#widget-info-manipulator)
- [Development](#development)
  - [Understanding the Architecture](#understanding-the-architecture)
  - [Implementing Your Own Widget Display](#implementing-your-own-widget-display)
  - [Best Practices](#best-practices)
  - [Common Use Cases](#common-use-cases)
- [License](#license)
- [Contributing](#contributing)

## Overview
The Omni.UI Scene Sample Object Info with Widget Example extension demonstrates how to create custom manipulators that display interactive UI widgets in the viewport. This extension provides a practical example of implementing non-interactive manipulators that show object metadata with embedded UI controls.

## Key Features

- **Interactive Widget Display**: Shows object information with embedded UI controls
- **Real-time Updates**: Information updates with selection changes
- **Custom UI Elements**: Embedded sliders and labels
- **Viewport Integration**: Seamless integration with viewport selection
- **USD Integration**: Seamless integration with USD stage and prims

## Interacting with the Solution

1. Launch your Omniverse application
2. Select any object in your scene
3. The widget manipulator will appear, showing:
   - A custom UI panel with object information
   - Interactive slider control
   - Object name and type
4. Interact with the widget by:
   - Hovering over the panel to show controls
   - Adjusting the scale slider
   - Viewing object information

## Implementation Details

### Widget Info Model
The extension implements a custom model that tracks object information:

```python
class WidgetInfoModel(sc.AbstractManipulatorModel):
    def __init__(self):
        super().__init__()
        self.material_name = ""
        self.position = WidgetInfoModel.PositionItem()
        self._current_path = ""

    def get_item(self, identifier):
        if identifier == "position":
            return self.position
        if identifier == "name":
            return self._current_path
        if identifier == "material":
            return self.material_name
```

### Widget Info Manipulator
The manipulator provides visual representation with embedded UI:

```python
class WidgetInfoManipulator(sc.Manipulator):
    def _on_build_widgets(self):
        with ui.ZStack():
            ui.Rectangle(style={
                "background_color": cl(0.2),
                "border_color": cl(0.7),
                "border_width": 2,
                "border_radius": 4,
            })
            with ui.VStack(style={"font_size": 24}):
                # Add UI elements
                ui.Label("Hello world, I am a scene.Widget!")
                self._name_label = ui.Label("")
                self._slider_model = ui.SimpleFloatModel()
                ui.FloatSlider(self._slider_model)
```

## Development

This sample extension demonstrates how to create custom manipulators with embedded UI widgets. Here's how you can leverage and adapt it for your workflow:

### Understanding the Architecture

The extension is built on several key components:

1. **Model Layer** (`WidgetInfoModel`):
   - Tracks selected object information
   - Manages USD prim references
   - Handles selection changes
   - Computes object positions

2. **Manipulator Layer** (`WidgetInfoManipulator`):
   - Creates visual representation
   - Manages UI widget lifecycle
   - Handles widget updates
   - Ensures proper positioning

3. **UI Integration**:
   - Embedded UI widgets
   - Interactive controls
   - Real-time updates
   - Viewport integration

### Implementing Your Own Widget Display

1. **Create a Custom Model**:
```python
class MyWidgetModel(sc.AbstractManipulatorModel):
    def __init__(self):
        super().__init__()
        self._prim = None
        self._current_path = ""
        self.position = MyWidgetModel.PositionItem()
        self.custom_info = MyWidgetModel.StringItem()

    def get_item(self, identifier):
        if identifier == "position":
            return self.position
        if identifier == "custom_info":
            return self._get_custom_info()
        return None
```

2. **Implement the Manipulator with Widgets**:
```python
class MyWidgetManipulator(sc.Manipulator):
    def _on_build_widgets(self):
        with ui.ZStack():
            ui.Rectangle(style={
                "background_color": cl(0.2),
                "border_color": cl(0.7),
                "border_width": 2,
            })
            with ui.VStack():
                ui.Label("Custom Widget")
                self._info_label = ui.Label("")
                self._slider = ui.FloatSlider()

    def on_build(self):
        self._root = sc.Transform(visible=False)
        with self._root:
            with sc.Transform(scale_to=sc.Space.SCREEN):
                self._widget = sc.Widget(500, 150, 
                    update_policy=sc.Widget.UpdatePolicy.ON_MOUSE_HOVERED)
                self._widget.frame.set_build_fn(self._on_build_widgets)
```

### Best Practices

1. **Model Design**:
   - Keep models focused on data management
   - Implement efficient USD queries
   - Handle selection changes properly
   - Cache frequently accessed values

2. **Widget Implementation**:
   - Use clear visual hierarchy
   - Implement efficient updates
   - Handle widget lifecycle
   - Consider performance

3. **UI Design**:
   - Use appropriate styling
   - Implement clear feedback
   - Ensure proper layout
   - Consider viewport performance

4. **Viewport Integration**:
   - Handle selection properly
   - Manage widget visibility
   - Implement proper cleanup
   - Consider gesture conflicts

### Common Use Cases

1. **Object Information**:
   - Display object metadata
   - Show material assignments
   - Indicate object states
   - Present custom properties

2. **Interactive Controls**:
   - Property adjustment
   - Value pickers
   - Custom controls
   - Real-time updates

3. **Visual Feedback**:
   - Status indicators
   - Warning messages
   - Error states
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
"omni.sample.ui_scene.widget_info" = {}
```




