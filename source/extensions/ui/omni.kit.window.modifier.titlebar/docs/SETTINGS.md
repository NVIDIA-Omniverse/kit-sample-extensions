```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Settings

## Settings Provided by the Extension
### exts."omni.kit.window.modifier.titlebar".colors.close_clicked
   - **Default Value**: 0x372FE8
   - **Description**: Specifies the titlebar's close button color when it is clicked.

### exts."omni.kit.window.modifier.titlebar".colors.minmax_clicked
   - **Default Value**: 0x777777
   - **Description**: Specifies the titlebar's minimize/maximize button color when it is clicked.

### exts."omni.kit.window.modifier.titlebar".colors.close
   - **Default Value**: 0x2311E8
   - **Description**: Specifies the titlebar's close button normal color.

### exts."omni.kit.window.modifier.titlebar".colors.minmax
   - **Default Value**: 0x636363
   - **Description**: Specifies the titlebar's minimize/maximize button normal color.

### exts."omni.kit.window.modifier.titlebar".colors.button
   - **Default Value**: 0xCCCCCC
   - **Description**: Specifies the default color for the generic titlebar buttons.

### exts."omni.kit.window.modifier.titlebar".colors.client
   - **Default Value**: 0xFFFF00
   - **Description**: Specifies the color of the client area in the titlebar.

### exts."omni.kit.window.modifier.titlebar".colors.caption
   - **Default Value**: 0x454545
   - **Description**: Specifies the caption text color in the titlebar.

### exts."omni.kit.window.modifier.titlebar".windowBorder.width
   - **Default Value**: 3
   - **Description**: Specifies the width of the window border in the titlebar modifier.

### exts."omni.kit.window.modifier.titlebar".windowBorder.color
   - **Default Value**: 0xFF
   - **Description**: Specifies the color of the window border in the titlebar modifier.

### exts."omni.kit.window.modifier.titlebar".separator.width
   - **Default Value**: 1
   - **Description**: Specifies the width of the separator in the titlebar.

### exts."omni.kit.window.modifier.titlebar".separator.color
   - **Default Value**: 0xA02020
   - **Description**: Specifies the color of the separator in the titlebar.

### exts."omni.kit.window.modifier.titlebar".defaultFont.color
   - **Default Value**: 0xA0A0A0
   - **Description**: Specifies the default font color used in the titlebar.

### exts."omni.kit.window.modifier.titlebar".defaultFont.size
   - **Default Value**: 18
   - **Description**: Specifies the default font size for the titlebar text.

### exts."omni.kit.window.modifier.titlebar".defaultFont.name
   - **Default Value**: Arial
   - **Description**: Specifies the default font name for the titlebar.

### exts."omni.kit.window.modifier.titlebar".respondOnMouseUp
   - **Default Value**: True
   - **Description**: Determines whether the titlebar should respond on mouse button release.

### exts."omni.kit.window.modifier.titlebar".changeWindowRegion
   - **Default Value**: False
   - **Description**: Determines whether the extension will change the window region of the application.

### exts."omni.kit.window.modifier.titlebar".showFileFullPath
   - **Default Value**: False
   - **Description**: A flag to control whether the titlebar displays the full file path.

### exts."omni.kit.window.modifier.titlebar".titleFormatString
   - **Default Value**: {text:OMNIVERSE, font_color=0xff00,bold=true, italic = true } {separator} Kit-Demo {verKey:/app/version, font_color=0xff00ff} {separator} {file}
   - **Description**: Specifies the format string for generating the window title, which may include tokens and attributes for styling.

## Settings Used by the Extension but Provided by Another Extension
### app/window/height
   - **Default Value**: 720
   - **Description**: Sets the application's window height.

### app/window/width
   - **Default Value**: 1080
   - **Description**: Sets the application's window width.

### /persistent/app/window/uiStyle
   - **Description**: Determines the overall UI style for the application window, influencing the default color settings applied to the titlebar elements.

### /privacy/externalBuild
   - **Description**: A flag used to determine if an external build is active, which affects the processing of the window title format string.
