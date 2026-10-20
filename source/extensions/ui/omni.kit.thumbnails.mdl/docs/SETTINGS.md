```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Settings

## Settings Provided by the Extension
### exts."omni.kit.thumbnails.mdl".clearSelection
   - **Default Value**: True
   - **Description**: Controls whether the current selection is cleared when generating a material thumbnail.

### exts."omni.kit.thumbnails.mdl".usd.render_samples
   - **Default Value**: 8
   - **Description**: Specifies the number of samples the renderer should use when generating USD thumbnails.

### exts."omni.kit.thumbnails.mdl".usd.render_mode
   - **Default Value**: PathTracing
   - **Description**: Determines the rendering mode (e.g., PathTracing) applied during USD thumbnail generation.

### exts."omni.kit.thumbnails.mdl".usd.stdin
   - **Default Value**: /Root/Material_Standin
   - **Description**: Sets the stage prim path to which the USD material is bound when preparing a USD thumbnail.

### exts."omni.kit.thumbnails.mdl".usd.template_path
   - **Default Value**: 
   - **Description**: Provides the file path for the USD thumbnail template used during thumbnail generation.

### exts."omni.kit.thumbnails.mdl".mdl.render_samples
   - **Default Value**: 8
   - **Description**: Specifies the number of rendering samples to be applied when generating MDL thumbnails.

### exts."omni.kit.thumbnails.mdl".mdl.render_mode
   - **Default Value**: PathTracing
   - **Description**: Determines the rendering mode (e.g., PathTracing) to be used during MDL thumbnail generation.

### exts."omni.kit.thumbnails.mdl".mdl.stdin
   - **Default Value**: /Root/Material_Standin
   - **Description**: Sets the stage prim path to which the MDL material is bound when preparing an MDL thumbnail.

### exts."omni.kit.thumbnails.mdl".mdl.template_path
   - **Default Value**: 
   - **Description**: Provides the file path for the MDL thumbnail template used during thumbnail generation.

## Settings Used by the Extension but Provided by Another Extension
### /app/captureFrame/setAlphaTo1
   - **Description**: Controls whether the alpha channel is forced to 1 when capturing the viewport frame.

### /rtx/post/backgroundZeroAlpha/enabled
   - **Description**: Enables or disables the zero alpha post-process effect for background rendering during viewport capture.

### /rtx/post/backgroundZeroAlpha/backgroundComposite
   - **Description**: Determines if the background is composited during the zero alpha post-process effect for viewport captures.

### /rtx/post/backgroundZeroAlpha/outputAlphaInComposite
   - **Description**: Specifies whether the output composite should include an alpha channel in the zero alpha post-process effect.

### /app/viewport/grid/enabled
   - **Description**: Controls the visibility of the grid overlay in the viewport during thumbnail capture.
