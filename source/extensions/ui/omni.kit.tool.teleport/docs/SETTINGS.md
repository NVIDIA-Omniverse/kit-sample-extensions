```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Settings

## Settings Provided by the Extension
### exts."omni.kit.tool.teleport".ringManipulatorMaxSize
- **Default Value**: 100
- **Description**: Sets the maximum allowed size (in pixels) for the teleport ring manipulator, ensuring it does not exceed a predefined limit.

### exts."omni.kit.tool.teleport".ringManipulatorMinSize
- **Default Value**: 25
- **Description**: Specifies the minimum allowed size (in pixels) for the teleport ring manipulator, enforcing a lower boundary for its display scaling.

### exts."omni.kit.tool.teleport".ringManipulatorScale
- **Default Value**: 0.85
- **Description**: Determines the scaling factor applied to the teleport ring manipulator relative to its base size.

### exts."omni.kit.tool.teleport".ringManipulatorFixedSize
- **Default Value**: False
- **Description**: A boolean flag that indicates whether the teleport ring manipulator should maintain a fixed size regardless of screen scaling changes.

### exts."omni.kit.tool.teleport".ringManipulatorVisible
- **Default Value**: True
- **Description**: Controls the visibility of the ring manipulator within the teleport tool interface.

### exts."omni.kit.tool.teleport".keyWord
- **Default Value**: (empty string)
- **Description**: Provides a filter keyword used in the teleport tool settings and preferences.

### exts."omni.kit.tool.teleport".widgetScale
- **Default Value**: 1.0
- **Description**: Defines the uniform scaling factor for the teleport widget and its visual components.

### exts."omni.kit.tool.teleport".eyeHeight
- **Default Value**: 250
- **Description**: Sets the vertical offset applied when teleporting the camera, simulating a natural head (eye) height.

### exts."omni.kit.tool.teleport".showPosition
- **Default Value**: False
- **Description**: Determines whether the target position label is displayed in the teleport user interface.

### exts."omni.kit.tool.teleport".useWorldUp
- **Default Value**: False
- **Description**: When enabled, the teleport tool ignores the picked surface normal and orients to the world up vector, keeping the camera level and the teleport allowed over surfaces whose normals vary widely (e.g. point clouds rendered as spheres).

## Settings Used by the Extension but Provided by Another Extension
### /exts/omni.kit.tool.teleport/beamVisible
- **Description**: Controls the visibility of the teleport beam arc, toggling its display during teleport operations.

### /exts/omni.kit.tool.teleport/basicGizmo
- **Description**: A flag that selects between a basic and a standard teleport gizmo USD file, affecting the widget’s appearance based on user preference.

### /exts/omni.kit.tool.teleport/max_slope_angle
- **Description**: Specifies the maximum allowable slope angle for a valid teleportation surface, ensuring that the target area meets navigation constraints.

### /exts/omni.kit.tool.teleport/simple_camera
- **Description**: Determines if simple camera mode is active, which influences input handling for camera gestures during teleport operations.

### /persistent/exts/omni.kit.manipulator.camera/lookSpeed
- **Description**: Configures the camera look speed used for teleport tool camera manipulation, with its values inverted for appropriate directional control.

### /persistent/exts/omni.kit.manipulator.camera/flyViewLock
- **Description**: Locks the camera fly view after a teleport event to maintain a stable and controlled camera orientation.

### /rtx/sectionPlane/enabled
- **Description**: Enables or disables the section plane for raycasting, affecting how the teleport tool identifies valid surfaces.

### /rtx/sectionPlane/plane
- **Description**: Provides the configuration parameters for the section plane used during raycasting to determine valid teleport targets.
