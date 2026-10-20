# Kit Rendering service

Allows the triggering of a render within Kit via a service request.
The idea of this service is to enable it within an existing application such as Create.
It will then be able to use all capabilities that Create has to do the render of the scene.

The render options available are taken from `omni.kit.capture.CaptureOptions` and `omni.kit.capture` is used to trigger the rendering of the frames.