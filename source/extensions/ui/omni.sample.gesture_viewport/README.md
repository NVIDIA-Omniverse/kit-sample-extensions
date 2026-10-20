# Omni.UI Gestures for Viewport Extension

<p align="center">
  <img src="readme-assets/hero_image.gif" width=100% />
</p>

## Overview
The Omni.UI Gestures for Viewport extension is a sample extension that demonstrates how to implement basic gesture interactions in the Omniverse viewport using the `omni.ui.scene` framework. This extension provides a simple example of a line manipulator that can be interacted with using mouse gestures.

## Table of Contents
- [Key Features](#key-features)
- [Interacting with the Solution](#interacting-with-the-solution)
- [Implementation Details](#implementation-details)
  - [Gesture Manager](#gesture-manager)
  - [Custom Drag Gesture](#custom-drag-gesture)
  - [Line Manipulator](#line-manipulator)
- [Development](#development)
  - [Building Blocks](#building-blocks)
  - [From Basic to Complex](#from-basic-to-complex)
  - [Advanced Implementation Examples](#advanced-implementation-examples)
- [License](#license)
- [Contributing](#contributing)

## Key Features

- **Line Manipulator**: A simple line shape that can be:
  - Clicked to change color to green
  - Double-clicked to change color back to beige
  - Clicked and dragged to move
- **Gesture Management**: Demonstrates how to:
  - Implement custom gesture managers
  - Handle gesture prevention and conflicts
  - Create custom drag gestures
- **Scene UI Integration**: Shows how to:
  - Create and manipulate shapes in the viewport
  - Add labels and text
  - Use transforms for positioning

## Interacting with the Solution

1. Launch your Omniverse application
2. The extension will register a "Line Gesture" scene manipulator
3. In the viewport, you'll see a beige line with a label
4. Interact with the line using:
   - Click to change color to green
   - Double-click to change color back to beige
   - Click and drag to move the line

## Implementation Details

### Gesture Manager
The extension implements a custom `GestureManager` that controls how gestures interact with each other:
```python
class Manager(sc.GestureManager):
    def should_prevent(self, gesture: AbstractGesture, preventer: AbstractGesture) -> bool:
        if gesture.name == "SelectionDrag" and preventer.state == sc.GestureState.BEGAN:
            return True
        if gesture.name == "SelectionClick" and preventer.name == "color_change":
            return True
```

### Custom Drag Gesture
The extension includes a custom `Move` gesture that inherits from `DragGesture`:
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

### Line Manipulator
The main manipulator class creates a line with attached gestures:
```python
class LineManipulator(sc.Manipulator):
    def on_build(self) -> None:
        transform = sc.Transform()
        with transform:
            sc.Line(
                [-50, 0, 0],
                [50, 0, 0],
                color=ui.color.beige,
                thickness=10,
                gestures=[
                    sc.ClickGesture(...),
                    sc.DoubleClickGesture(...),
                    Move(transform, manager=manager),
                ],
            )
```

## Development

This sample provides a foundation for implementing custom gesture interactions in the Omniverse viewport. Here's how you can progress from basic to complex interactions:

### Building Blocks

1. **Understanding the Core Components**
   ```python
   # 1. Basic Gesture Manager - Controls gesture behavior
   class Manager(sc.GestureManager):
       def should_prevent(self, gesture: AbstractGesture, preventer: AbstractGesture) -> bool:
           # Your prevention logic here
           return True/False

   # 2. Custom Gesture - Defines interaction behavior
   class CustomGesture(sc.DragGesture):
       def on_changed(self):
           # Your gesture handling here
           pass

   # 3. Manipulator - Combines visuals and gestures
   class CustomManipulator(sc.Manipulator):
       def on_build(self) -> None:
           # Your UI building here
           pass
   ```

2. **Progression Path**
   - Start with single gesture (like the line's drag)
   - Add multiple gestures (click + drag)
   - Implement gesture combinations (click + drag + scale)
   - Create complex gesture chains (select → transform → apply)

### From Basic to Complex

1. **Step 1: Single Object Manipulation**
   ```python
   class BasicManipulator(sc.Manipulator):
       def on_build(self) -> None:
           transform = sc.Transform()
           with transform:
               # Basic shape with single gesture
               sc.Rectangle(
                   width=100,
                   height=100,
                   gestures=[Move(transform, manager=manager)],
               )
   ```

2. **Step 2: Multiple Gestures**
   ```python
   # Custom manager to handle gesture prevention
   class EnhancedManager(sc.GestureManager):
       def should_prevent(self, gesture: AbstractGesture, preventer: AbstractGesture) -> bool:
           # Prevent click gesture when drag is active
           if gesture.name == "click" and preventer.name == "drag":
               return True
           # Prevent drag gesture when click is active
           if gesture.name == "drag" and preventer.name == "click":
               return True
           return False

   class EnhancedManipulator(sc.Manipulator):
       def on_build(self) -> None:
           transform = sc.Transform()
           with transform:
               # Shape with multiple gestures
               sc.Rectangle(
                   width=100,
                   height=100,
                   gestures=[
                       Move(transform, manager=EnhancedManager(), name="drag"),
                       sc.ClickGesture(
                           self.on_click,
                           manager=EnhancedManager(),
                           name="click"
                       ),
                       sc.DoubleClickGesture(
                           self.on_double_click,
                           manager=EnhancedManager(),
                           name="double_click"
                       ),
                   ],
               )

       def on_click(self, sender):
           # Only called when click gesture isn't prevented
           print("Click gesture activated")

       def on_double_click(self, sender):
           # Only called when double click gesture isn't prevented
           print("Double click gesture activated")
   ```

3. **Step 3: Complex Interactions**
   ```python
   # Advanced manager for complex gesture interactions
   class ComplexManager(sc.GestureManager):
       def should_prevent(self, gesture: AbstractGesture, preventer: AbstractGesture) -> bool:
           # Prevent scale during rotation
           if gesture.name == "scale" and preventer.name == "rotate":
               return True
           # Prevent rotation during scale
           if gesture.name == "rotate" and preventer.name == "scale":
               return True
           # Allow move with any other gesture
           if gesture.name == "move":
               return False
           # Prevent click during any transform gesture
           if gesture.name == "click" and preventer.name in ["move", "scale", "rotate"]:
               return True
           return False

   class ComplexManipulator(sc.Manipulator):
       def on_build(self) -> None:
           transform = sc.Transform()
           with transform:
               # Shape with complex gesture system
               sc.Rectangle(
                   width=100,
                   height=100,
                   gestures=[
                       Move(transform, manager=ComplexManager(), name="move"),
                       Scale(transform, manager=ComplexManager(), name="scale"),
                       Rotate(transform, manager=ComplexManager(), name="rotate"),
                       sc.ClickGesture(
                           self.on_click,
                           manager=ComplexManager(),
                           name="click"
                       ),
                   ],
               )

       def on_click(self, sender):
           # Only called when no transform gestures are active
           print("Click gesture activated")

   # Custom Scale gesture implementation
   class Scale(sc.DragGesture):
       def __init__(self, transform: sc.Transform, **kwargs):
           super().__init__(**kwargs)
           self.__transform = transform
           self.__initial_scale = 1.0

       def on_began(self):
           # Store initial scale when gesture starts
           self.__initial_scale = self.__transform.transform.get_scale()[0]

       def on_changed(self):
           # Calculate scale based on drag distance
           drag_distance = self.sender.gesture_payload.moved[0]
           new_scale = self.__initial_scale + (drag_distance * 0.01)
           # Apply scale transform
           self.__transform.transform = sc.Matrix44.get_scale_matrix(new_scale)

   # Custom Rotate gesture implementation
   class Rotate(sc.DragGesture):
       def __init__(self, transform: sc.Transform, **kwargs):
           super().__init__(**kwargs)
           self.__transform = transform
           self.__initial_rotation = 0.0

       def on_began(self):
           # Store initial rotation when gesture starts
           self.__initial_rotation = self.__transform.transform.get_rotation()[2]

       def on_changed(self):
           # Calculate rotation based on drag distance
           drag_distance = self.sender.gesture_payload.moved[0]
           new_rotation = self.__initial_rotation + (drag_distance * 0.1)
           # Apply rotation transform
           self.__transform.transform = sc.Matrix44.get_rotation_matrix(0, 0, new_rotation)
   ```

### Advanced Implementation Examples

1. **Light Manipulator Approach**
   - Start with basic light position manipulation
   - Add color picker gesture
   - Implement intensity control
   - Add direction handles
   ```python
   class LightManipulator(sc.Manipulator):
       def on_build(self) -> None:
           transform = sc.Transform()
           with transform:
               # Light representation
               sc.Sphere(radius=10, color=ui.color.yellow)
               # Direction handle
               sc.Line([0,0,0], [0,50,0],
                   gestures=[DirectionDrag(transform, manager=manager)])
               # Color picker
               sc.Rectangle(width=20, height=20,
                   gestures=[ColorPickerGesture(self.on_color_change)])
   ```

2. **Object Info Approach**
   - Begin with selection gesture
   - Add property display on gesture
   - Implement context menu
   - Add property editing gestures
   ```python
   class ObjectInfoManipulator(sc.Manipulator):
       def on_build(self) -> None:
           transform = sc.Transform()
           with transform:
               # Selection area
               sc.Rectangle(
                   width=100, height=100,
                   gestures=[SelectGesture(self.on_select)])
               # Info display
               sc.Label("Object Info",
                   gestures=[InfoDisplayGesture(self.on_info_display)])
   ```

## License

Development using the Omniverse Kit SDK is subject to the licensing terms detailed [here](https://docs.omniverse.nvidia.com/install-guide/latest/common/NVIDIA_Omniverse_License_Agreement.html).

This project will download and install additional third-party open source software projects. Review the license terms of these open source projects before use.

## Contributing

We provide this source code as-is and are currently not accepting outside contributions.
