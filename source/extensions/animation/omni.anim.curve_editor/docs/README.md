# Animation Curve Editor [omni.anim.curve_editor]

Animation Curve Editor is the authoring tool to edit USD attribute's sparse animation key data.

The tool is based on the AnimationData schema defined in this repo https://gitlab-master.nvidia.com/omniverse/usd-ext-animation

Each scalar channel of a USD attribute corresponds to a list of animation keys which forms an animation curve. For example the xformOp:translate attribute can have at most three curves, e.g. xformOp:translate:x, xformOp:translate:y and xformOp:translate:z. Apart from the animation keys, there are also two tangents attached to each key, which also determins the interpolation types, e.g. linear interpolation, bezier curve interpolation, step next interpolation etc.. 

Animation Curve Editor allows users to adjust keys and key tangents and thus affect the animation curve shape on-the-fly. It works along with the animation Curve runtime(omni.anim.curve) such that the curve shape is instantly reflected in the USD attribute animation. 

## Animation Curve Editor Features

Just like other DCC tools, the animation curve editor allows users to
- List all curves of the selected prims
- Isolate curves by a single click
- Zoom in/out curves visualization
- Insert new keys into selected curves
- Delete existing keys
- Move existing keys
- Key's tangents value authoring
- Key's tangent type authoring
- Group selecting keys and manipulation against keys and tangents