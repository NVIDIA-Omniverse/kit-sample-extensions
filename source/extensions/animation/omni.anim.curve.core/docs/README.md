# Animation Curve Runtime [omni.anim.curve.core]

The Animation Curve runtime serves as the backend of various sparse animation key authoring tools. It is the animation engine to do the interpolation over the authored sparse animation keys and animate the USD attributes who has those attached animation data.

The USD animation data schema is defined in this repo https://gitlab-master.nvidia.com/omniverse/usd-ext-animation The animation curve runtime is a consumer of the USD animation data schema.  Currently it is the backend of various authoring tool including:
- Curve Editor
- Animation Timeline
- Property Widget's Animation Data context menu

It offers some basic animation commands, e.g. SetAnimCurveKeys, RemoveAnimCurveKeys, and RemoveAnimData, which server as public interfaces for any extensions who want to author animation keys.  Although users can use the animation data schema to directly manipulate the animation data, those commands greatly simplified the authoring process and offer a middle layer such that the schema changes won't affect the authoring API. The Animation Curve runtime also provide an event stream such that the users would know when a key is added, deleted etc.
