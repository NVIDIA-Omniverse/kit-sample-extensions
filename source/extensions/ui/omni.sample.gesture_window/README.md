# Omni.UI Sample Gestures for omni.ui.Window Extension

<p align="center">
  <img src="data/preview.png" width=100% />
</p>

## Overview
The Omni.UI Sample Gestures for omni.ui.Window extension is a sample extension that demonstrates how to implement gesture interactions within an `omni.ui.Window`. This extension provides a practical example of handling various mouse gestures (click, double-click, hover, and drag) on UI elements within a window.

## Table of Contents
- [Key Features](#key-features)
- [Interacting with the Solution](#interacting-with-the-solution)
- [Implementation Details](#implementation-details)
  - [Gesture Manager](#gesture-manager)
  - [Custom Drag Gesture](#custom-drag-gesture)
  - [Gesture Window](#gesture-window)
- [Development](#development)
  - [Building Blocks](#building-blocks)
  - [From Basic to Complex](#from-basic-to-complex)
  - [Advanced Implementation Examples](#advanced-implementation-examples)
- [License](#license)
- [Contributing](#contributing)

## Key Features

- **Interactive UI Elements**: Two rectangles that respond to:
  - Click (changes color)
  - Double-click (changes color)
  - Hover (changes color)
  - Drag (moves the element)
- **Gesture Feedback**: Real-time display of active gestures
- **Gesture Management**: Custom gesture prevention system
- **Window Integration**: Seamless integration with `omni.ui.Window`

## Interacting with the Solution

1. Launch your Omniverse application
2. The extension will create a window with two interactive rectangles
3. Interact with the rectangles using:
   - Click to change color to blue/red
   - Double-click to change color back to beige/olive
   - Hover to change color to black
   - Click and drag to move the rectangles
4. Watch the label in the middle of the window to see which gesture is active

## Implementation Details

### Gesture Manager
The extension implements a custom `GestureManager` that controls gesture interactions:
```python
class Manager(sc.GestureManager):
    def should_prevent(self, gesture: AbstractGesture, preventer: AbstractGesture) -> bool:
        if gesture.name != "gesture_name" and preventer.state == sc.GestureState.BEGAN:
            return True
        return False
```

### Custom Drag Gesture
The extension includes a custom `Move` gesture for dragging:
```python
class Move(sc.DragGesture):
    def __init__(self, transform: sc.Transform, **kwargs):
        super().__init__(**kwargs)
        self.__transform = transform

    def on_changed(self):
        translate = self.sender.gesture_payload.moved
        current = sc.Matrix44.get_translation_matrix(*translate)
        self.__transform.transform *= current
```

### Gesture Window

The extension implements a custom window class that creates an interactive scene with gesture support:

```python
class GestureWindowExample(ui.Window):
    def __init__(self, title: str, **kwargs) -> None:
        super().__init__(title, **kwargs)
        self.label = None
        self.frame.set_build_fn(self._build_fn)

    def _build_fn(self):
        with self.frame:
            with ui.VStack():
                self.label = ui.Label("Sender: None\nAction: None",
                                    alignment=ui.Alignment.CENTER,
                                    size=16)
                proj = [0.5, 0, 0, 0, 0, 0.5, 0, 0, 0, 0, 2e-7, 0, 0, 0, 1, 1]
                scene_view = sc.SceneView(
                    sc.CameraModel(proj, 1),
                    aspect_ratio_policy=sc.AspectRatioPolicy.PRESERVE_ASPECT_FIT
                )
                with scene_view.scene:
                    transform = sc.Transform()
                    with transform:
                        sc.Rectangle(
                            2, 2,
                            color=ui.color.beige,
                            thickness=5,
                            gestures=[
                                sc.ClickGesture(
                                    lambda s: setcolor(s, ui.color.blue),
                                    manager=manager,
                                    name="gesture_name"
                                ),
                                sc.DoubleClickGesture(
                                    lambda s: setcolor(s, ui.color.beige),
                                    manager=manager,
                                    name="gesture_name"
                                ),
                                Move(transform, manager=manager, name="gesture_name"),
                                sc.HoverGesture(
                                    on_began_fn=self.handle_hover_begin,
                                    on_changed_fn=self.handle_hover_changed,
                                    on_ended_fn=self.handle_hover_end,
                                ),
                            ],
                        )
```

The window creates a scene view with two interactive rectangles, each supporting multiple gestures. The window includes a label that displays the current gesture state and source.

## Development

This sample extension demonstrates how to implement gesture interactions in an Omniverse Kit application. Here's how you can leverage and adapt it for your workflow:

### Adding Gesture Support to Your Windows

1. **Basic Window Setup**:
```python
class MyGestureWindow(ui.Window):
    def __init__(self, title: str, **kwargs) -> None:
        super().__init__(title, **kwargs)
        self.frame.set_build_fn(self._build_fn)

    def _build_fn(self):
        with self.frame:
            with ui.VStack():
                scene_view = sc.SceneView(
                    sc.CameraModel(proj, 1),
                    aspect_ratio_policy=sc.AspectRatioPolicy.PRESERVE_ASPECT_FIT
                )
```

2. **Adding Interactive Elements**:
```python
with scene_view.scene:
    transform = sc.Transform()
    with transform:
        sc.Rectangle(
            2, 2,
            color=ui.color.beige,
            gestures=[
                sc.ClickGesture(self.handle_click),
                sc.HoverGesture(
                    on_began_fn=self.handle_hover_begin,
                    on_ended_fn=self.handle_hover_end
                )
            ]
        )
```

### Implementing Custom Gestures

1. **Create a Custom Gesture Manager**:
```python
class MyGestureManager(sc.GestureManager):
    def should_prevent(self, gesture: AbstractGesture, preventer: AbstractGesture) -> bool:
        # Add your gesture prevention logic here
        return False
```

2. **Implement Custom Gesture Behavior**:
```python
class MyCustomGesture(sc.DragGesture):
    def __init__(self, target: sc.Transform, **kwargs):
        super().__init__(**kwargs)
        self.__target = target

    def on_changed(self):
        # Implement your custom gesture behavior
        pass
```

### Best Practices

1. **Gesture Management**:
   - Use a GestureManager to prevent conflicts between gestures
   - Name your gestures consistently for easier debugging
   - Consider gesture priority in your implementation

2. **Performance**:
   - Keep gesture handlers lightweight
   - Use transform operations for movement instead of recreating objects
   - Implement proper cleanup in shutdown methods

3. **User Experience**:
   - Provide visual feedback for all gesture states
   - Consider adding gesture hints or tooltips
   - Implement smooth transitions between states

### Common Use Cases

1. **3D Object Manipulation**:
   - Implement drag gestures for moving objects
   - Add rotation gestures for object orientation
   - Use scale gestures for resizing

2. **UI Interaction**:
   - Add hover effects for interactive elements
   - Implement click and double-click behaviors
   - Create custom gesture combinations

3. **Viewport Control**:
   - Add camera control gestures
   - Implement viewport navigation
   - Create custom view manipulation tools

## License

Development using the Omniverse Kit SDK is subject to the licensing terms detailed [here](https://docs.omniverse.nvidia.com/install-guide/latest/common/NVIDIA_Omniverse_License_Agreement.html).

This project will download and install additional third-party open source software projects. Review the license terms of these open source projects before use.

## Contributing

We provide this source code as-is and are currently not accepting outside contributions.
