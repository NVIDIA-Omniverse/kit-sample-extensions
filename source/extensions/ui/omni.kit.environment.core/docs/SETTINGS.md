```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Settings

## Settings Provided by the Extension
### app/sunstudy/currentSkyType
- **Default Value**: (empty)
- **Description**: Specifies the type of sky currently active in sun study mode (for example, dynamic, static, or none).

### app/sunstudy/currentSkyPath
- **Default Value**: (empty)
- **Description**: Stores the file or USD prim path of the sky asset that is currently used for sun study.

### app/sunstudy/loop
- **Default Value**: False
- **Description**: Determines whether the sun study playback should loop continuously through its timeline.

### app/sunstudy/rate
- **Default Value**: 1
- **Description**: Specifies the playback speed rate for the sun study simulation.

### app/sunstudy/enable
- **Default Value**: True
- **Description**: Enables or disables the sun study functionality within the application.

### app/sunstudy/playing
- **Default Value**: False
- **Description**: Indicates whether the sun study simulation is currently active (playing) or not.

### exts."omni.kit.environment.core".ground.path
- **Default Value**: (empty)
- **Description**: Defines the path for the ground asset in the environment, used when setting up the ground prim.

### exts."omni.kit.environment.core".extraMdlParam
- **Default Value**: False
- **Description**: Controls whether extra MDL parameters are processed for environment materials when binding or updating material properties.

### exts."omni.kit.environment.core".rtx.light.warning
- **Default Value**: True
- **Description**: Toggles the display of warnings related to extra RTX light configurations during environment updates.

### exts."omni.kit.environment.core".rtx.ground.subId
- **Default Value**: (empty)
- **Description**: Holds a sub-identifier string for the RTX ground material, used to distinguish material variants.

### exts."omni.kit.environment.core".rtx.ground.material
- **Default Value**: ${omni.kit.environment.core}/data/Ground.mdl
- **Description**: Specifies the default MDL material file used for creating the RTX ground asset in the environment.

### exts."omni.kit.environment.core".rtx.ground.enable
- **Default Value**: False
- **Description**: Determines whether the RTX ground features are enabled in the current environment setup.

### exts."omni.kit.environment.core".rtx.env.defaultUrl
- **Default Value**: http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Skies/Dynamic/ClearSky.usd
- **Description**: Specifies the default URL for the RTX environment sky asset that is used when no other environment is set.

### exts."omni.kit.environment.core".rtx.env.auto
- **Default Value**: False
- **Description**: Enables the automatic application of the RTX environment based on the specified default URL.

## Settings Used by the Extension but Provided by Another Extension
### /rtx/rendermode
- **Description**: Defines the current render mode (for example, 'rt' for raytraced lighting or 'pt' for path tracing) used by the RTX rendering engine.

### /exts/omni.usd/mdl/populateInputsOnLoaded
- **Description**: Ensures that MDL material inputs are automatically populated when a USD stage is loaded, facilitating proper material configuration.

### /persistent/app/stage/northOrientation
- **Description**: Stores the north orientation value used to align environmental elements with the stage’s coordinate system.
