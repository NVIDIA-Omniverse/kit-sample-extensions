```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Overview

The **omni.kit.window.modifier.titlebar** extension modifies the main window's title bar to provide a customized visual appearance in Windows only. It adjusts key aspects such as the title string, icons, font attributes, and background colors. The extension uses formatted tokens to dynamically generate title text and apply consistent styling across the title bar.

```{image} ../../../../source/extensions/ui/omni.kit.window.modifier.titlebar/icons/preview.png
---
align: center
---
```


## UI Components

This extension manages the title bar's look by altering several visual elements. It formats the title string using a customizable pattern that supports dynamic tokens for text, version, and file information. The extension also sets default font properties — including family, size, and color — to ensure the title text meets design standards. In addition, it configures separators and border settings to segment different regions of the title bar, enhancing clarity and visual appeal.

## Configuration

Users can tailor the title bar appearance via several settings exposed by the extension. The key configuration options include:
- "titleFormatString": Defines the layout of the title text with embedded tokens for elements such as application name and version.
- "showFileFullPath": Controls whether the file's full path is displayed in the title text.
- "changeWindowRegion": Determines if the title bar region should be modified based on custom settings.
- "respondOnMouseUp": Sets the behavior for mouse interactions when updating the title bar.

In addition, the default font parameters (name, size, and color) as well as separator and border properties (color and width) are configurable. These options allow precise control over the title bar's typography and overall style.

## Relationships

The extension builds upon components from **omni.kit.window.title** and **omni.kit.uiapp**. It leverages these dependencies to integrate its custom title bar modifications into the broader Omniverse Kit environment, ensuring a consistent and responsive user interface.
