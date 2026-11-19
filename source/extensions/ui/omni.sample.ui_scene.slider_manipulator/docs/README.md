# Overview

We provide the End-to-End example that draws a 3D slider in the viewport overlay
on the top of the bounding box of the selected imageable. The slider controls
the scale of the prim. It has a custom manipulator, model, and gesture. When the
slider's value is changed, the manipulator processes the custom gesture that
changes the data in the model, which changes the data directly in the USD stage.

The viewport overlay is synchronized with the viewport using `Tf.Notice` that
watches the USD Camera.

![](../data/preview.png)

The extension name is `omni.example.ui_scene.slider_manipulator`.

## Manipulator

The manipulator is a very basic implementation of the slider in 3D space. The
main feature of the manipulator is that it redraws and recreates all the
children once the model is changed. It makes the code straightforward. It takes
the position and the slider value from the model, and when the user changes the
slider position, it processes a custom gesture. It doesn't write to the model
directly to let the user decide what to do with the new data and how the
manipulator should react to the modification. For example, if the user wants to
implement the snapping to the round value, it would be handy to do it in the
custom gesture.

## Model

The model contains the following named items:

 - `value` - the current value of the slider
 - `min` - the minimum value of the slider
 - `max` - the maximum value of the slider
 - `position` - the position of the slider in 3D space

The model demonstrates two main strategies working with the data.

The first strategy is that the model is the bridge between the manipulator and
the data, and it doesn't keep and doesn't duplicate the data. When the
manipulator requests the position from the model, the model computes the
position using USD API and returns it to the manipulator.

The first strategy is that the model can be a container of the data. For
example, the model pre-computes min and max values and passes them to the
manipulator once the selection is changed.

## Working with the main viewport

To display the manipulator, it should be parented to sc.SceneView object. It's
possible to create a new sc.SceneView object and overlay it with the viewport.
This way, it's necessary to synchronize the camera with the viewport.

Another way to put the manipulator to the viewport is to register it in the main
viewport `sc.SceneView`. This way, the manipulator's gestures can interact with
the gestures of the main transform manipulator. Use `RegisterScene` from
`omni.kit.viewport.registry` to register the manipulator with
`omni.kit.viewport.window`.

```python
from omni.kit.viewport.registry import RegisterScene

self._slider_registry = RegisterScene(SliderRegistry, "omni.example.ui_scene.slider_manipulator")
```

The viewport registry constructs the given class under the appropriate
`sc.SceneView` object. The given class `SliderRegistry` is a simple
class that creates a manipulator.

```python
class SliderRegistry:
    """
    Created by omni.kit.viewport.registry per viewport. Keeps the manipulator
    and some properties that are needed by the viewport.
    """

    def __init__(self, description: Optional[Dict[str, Any]] = None):
        self.__slider_manipulator = SliderManipulator(model=SliderModel(), gesture=SliderChangedGesture())

    def destroy(self):
        if self.__slider_manipulator:
            self.__slider_manipulator.destroy()
            self.__slider_manipulator = None
```

The manipulator shares the viewport's `sc.SceneView` with the camera transform,
object transform and rectangle selection manipulators. Their gestures participate
in the same gesture management, so the slider does not need to disable viewport
selection explicitly while dragging. Destroy the `RegisterScene` handle during
extension shutdown to unregister the slider.
