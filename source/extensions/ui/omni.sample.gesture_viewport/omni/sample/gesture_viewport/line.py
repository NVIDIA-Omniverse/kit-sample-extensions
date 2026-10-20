# Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import omni.ui as ui
from omni.ui import scene as sc

# Gesture name constants to ensure consistent usage and prevent typos
GESTURE_SELECTION_DRAG = "SelectionDrag"
GESTURE_SELECTION_CLICK = "SelectionClick"
GESTURE_COLOR_CHANGE = "color_change"


def set_color(sender: sc.AbstractShape, color) -> None:
    """
    Sets the color of the scene shape.

    This function is used as a gesture callback, where the sender is the scene
    shape (e.g., sc.Line) that the gesture is attached to.

    Args:
        sender (sc.AbstractShape): The scene shape receiving the gesture event.
            Must have a writable `color` attribute (e.g., sc.Line).
        color: The color to assign to the shape. Can be a shade name string
            (e.g., ui.color.green, ui.color.beige) or an int from ui.color().
    """
    sender.color = color


class Manager(sc.GestureManager):
    """
    The object that controls batch processing and preventing of gestures.
    See more here: https://docs.omniverse.nvidia.com/kit/docs/omni.ui.scene/latest/omni.ui.scene/omni.ui.scene.GestureManager.html
    """

    def should_prevent(self, gesture: sc.AbstractGesture, preventer: sc.AbstractGesture) -> bool:
        """
        Called per gesture. Determines if the gesture should be prevented with another gesture.
        Useful to resolve intersections.

        Args:
            `gesture : AbstractGesture`
                Gesture that is occurring
            `preventer : AbstractGesture`
                Gesture preventing `gesture`

        Returns:
            bool: Whether or not the gesture should be prevented.
            If True gesture will be prevented otherwise the gesture will overtake the last gesture used.
        """
        if gesture.name == GESTURE_SELECTION_DRAG and preventer.state == sc.GestureState.BEGAN:
            return True
        if gesture.name == GESTURE_SELECTION_CLICK and preventer.name == GESTURE_COLOR_CHANGE:
            return True
        return False


class Move(sc.DragGesture):
    """
    Inherits from `DragGesture`, the gesture that provides a way to capture click-and-drag mouse event.
    See more here: https://docs.omniverse.nvidia.com/kit/docs/omni.ui.scene/latest/omni.ui.scene/omni.ui.scene.DragGesture.html
    """

    def __init__(self, transform: sc.Transform, **kwargs):
        """
        Construct the gesture to track mouse drags

        Args:
            `transform : sc.Transform` The transform parent of the shape.

            `kwargs : dict`
                See below

        ### Keyword Arguments:

            `mouse_button : `
                Mouse button that should be active to start the gesture.

            `modifiers : `
                The keyboard modifier that should be active to start the gesture.

            `check_mouse_moved : `
                The check_mouse_moved property is a boolean flag that determines whether the DragGesture should verify if the 2D screen position of the mouse has changed before invoking the on_changed method. This property is essential in a 3D environment, as changes in the camera position can result in the mouse pointing to different locations in the 3D world even when the 2D screen position remains unchanged.

        Usage
        When check_mouse_moved is set to True, the DragGesture will only call the on_changed method if the actual 2D screen position of the mouse has changed. This can be useful when you want to ensure that the on_changed method is only triggered when there is a genuine change in the mouse's 2D screen position.
        If check_mouse_moved is set to False, the DragGesture will not check for changes in the mouse's 2D screen position before calling the on_changed method. This can be useful when you want the on_changed method to be invoked even if the mouse's 2D screen position hasn't changed, such as when the camera position is altered, and the mouse now points to a different location in the 3D world.

            `on_began_fn : `
                Called if the callback is not set when the user clicks the mouse button.

            `on_changed_fn : `
                Called if the callback is not set when the user moves the clicked button.

            `on_ended_fn : `
                Called if the callback is not set when the user releases the mouse button.

            `name : `
                The name of the object. It's used for debugging.

            `manager : `
                The Manager that controls this gesture.
        """
        super().__init__(**kwargs)
        self.__transform = transform

    def on_changed(self):
        """
        Called when the user moves the clicked button. Moves the sender in the direction the mouse was moved.
        """
        translate = self.sender.gesture_payload.moved
        # Move transform to the direction mouse moved
        current = sc.Matrix44.get_translation_matrix(*translate)
        self.__transform.transform *= current


class LineManipulator(sc.Manipulator):
    """
    Class that holds a custom Manipulator. Inherits from omni.ui.scene.Manipulator class.
    See more here: https://docs.omniverse.nvidia.com/kit/docs/omni.ui.scene/latest/omni.ui.scene/omni.ui.scene.Manipulator.html
    """

    def __init__(
        self, desc: dict = None, line_size: float = 50, line_thickness: float = 10, up_axis: str = "Y", **kwargs
    ) -> None:
        """
        ### Arguments:
            `desc : dict`
                Description of the manipulator (passed by RegisterScene)

            `line_size : float`
                The size of the line. Defaults to 50.

            `line_thickness : float`
                The thickness of the line. Defaults to 10.

            `up_axis : str`
                The up axis for positioning the text label.
                Defaults to "Y".

            `kwargs : dict`
                See below

        ### Keyword Arguments:

            `gestures : `
                All the gestures assigned to this shape.

            `model : `
                The model of the class.
        """
        self.desc = desc
        self.line_size = line_size
        self.line_thickness = line_thickness
        self.text_translation = (0, self.line_thickness, 0) if up_axis == "Y" else (0, 0, self.line_thickness)
        self._manager = Manager()
        super().__init__(**kwargs)

    def on_build(self) -> None:
        """
        Builds the Scene UI.
        Consists of a beige line that stretches in the X-axis.
        Called when Manipulator is dirty to build the content. It's another way to build the manipulator's content on the case the user doesn't want to reimplement the class.
        """
        manager = self._manager
        transform = sc.Transform()
        with transform:
            sc.Line(
                [-self.line_size, 0, 0],
                [self.line_size, 0, 0],
                color=ui.color.beige,
                thickness=self.line_thickness,
                gestures=[
                    sc.ClickGesture(
                        lambda s: set_color(s, ui.color.green),
                        mouse_button=0,
                        name=GESTURE_COLOR_CHANGE,
                        manager=manager,
                    ),
                    sc.DoubleClickGesture(
                        lambda s: set_color(s, ui.color.beige),
                        mouse_button=0,
                        name=GESTURE_COLOR_CHANGE,
                        manager=manager,
                    ),
                    Move(transform, manager=manager),
                ],
            )
            with sc.Transform(transform=sc.Matrix44.get_translation_matrix(*self.text_translation)):
                sc.Label(
                    "Click and Drag the Line to Move me\nClick or Double Click to Change color",
                    size=18,
                    alignment=ui.Alignment.CENTER,
                    color=ui.color.blue,
                )
