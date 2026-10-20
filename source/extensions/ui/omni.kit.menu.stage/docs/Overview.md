```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Overview

The Kit Stage Menu Options extension provides additional menu options specifically tailored for USD Stage workflows. It enhances the integration between the content browser and the USD Stage, facilitating the addition of file-based assets through intuitive context menus. This extension is designed to work seamlessly within the Omniverse Kit SDK environment, ensuring that assets are placed appropriately based on the current selection or viewport parameters.

## Concepts

- **Content Browser Integration:**  
  The extension focuses on integrating menu options with the content browser. It listens for load and unload events, enabling the dynamic registration of context menus that allow users to add files as either references or payloads to their USD stage.

- **Context-Aware Placement:**  
  By computing positions based on selected USD prims or querying viewport parameters, the extension ensures that new prims are positioned appropriately—even when no selection is active.

## Functionality

- **Dynamic Menu Registration:**  
  The primary API exposed is the [ContentBrowserOptions](omni.kit.menu.stage/omni.kit.menu.stage.ContentBrowserOptions) class. This class manages the registration and unregistration of additional context menus in the content browser. It reacts to content browser events and adapts actions based on the current scene state.

- **Seamless Asset Integration:**  
  Through its startup and shutdown processes, the extension assists in integrating file-based assets into the stage. It abstracts the complexity of determining where and how assets should be added, allowing users to work more efficiently.

## Relationships

- **Dependencies:**  
  This extension has dependencies on several other Omniverse Kit SDK components, including:  
  - omni.kit.context_menu  
  - omni.kit.window.stage  
  - omni.kit.window.content_browser (optional)  
  - omni.kit.viewport.window (optional)  
  - omni.kit.window.viewport (optional)  
  - omni.usd  

  These dependencies ensure that the menu options are well-integrated within the overall stage and content management workflows of the Kit environment.

## Usage Examples

A typical usage pattern involves creating an instance of [ContentBrowserOptions](omni.kit.menu.stage/omni.kit.menu.stage.ContentBrowserOptions) and managing its lifecycle within your extension:

```python
from omni.kit.menu.stage import ContentBrowserOptions

# Create and start the content browser options integration
options = ContentBrowserOptions()
options.startup()

# ... your application logic continues ...

# When shutting down, ensure proper cleanup
options.shutdown()
```

## Considerations

- The extension is designed for internal use within the Omniverse Kit SDK environment, focusing on content management associated with USD Stage.
- It does not accept initialization parameters, relying instead on internal mechanisms to configure context menus based on the current scene state and viewport information.
- Integration with optional components like the content browser or viewport windows is supported, but the core functionality hinges on proper interaction with the USD Stage and context menus.