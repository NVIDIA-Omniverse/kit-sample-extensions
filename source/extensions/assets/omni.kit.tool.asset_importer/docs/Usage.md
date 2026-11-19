# Usage

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Custom Importer Development](#custom-importer-development)
  - [Setup](#setup)
  - [Implementation](#implementation)
  - [Registration](#registration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Installation

Add the following to your extension's `extension.toml`:

```toml
[dependencies]
"omni.kit.tool.asset_importer" = {}
```

### Usage

The Asset Importer provides a user interface for importing 3D assets. To use it:

1. From the Omniverse application `File` menu, select `Import`
2. Select your source file(s)
3. Configure import options
4. Click "Import" to convert to USD

## Custom Importer Development

To build a custom importer extension, please follow these steps.

### Setup

1. Ensure your extension depends on `omni.kit.tool.asset_importer`
2. Add the dependency to your `extension.toml` as shown in the Installation section

### Implementation

To create a custom importer, you need to implement the `AbstractImporterDelegate` class. Here's a detailed example:

```python
import omni.kit.tool.asset_importer as ai
import omni.ui as ui
from typing import List, Union, Dict

class CustomAssetImporter(ai.AbstractImporterDelegate):
    """
    Custom importer implementation for specific file formats.
    """
    def __init__(self, name: str, filters: List[str], descriptions: List[str]) -> None:
        """
        Initialize the custom importer.

        Args:
            name: Display name of the importer
            filters: List of regex patterns for supported file extensions
            descriptions: List of descriptions for supported formats
        """
        self._name = name
        self._filters = filters
        self._descriptions = descriptions

    @property
    def name(self) -> str:
        """Return the importer's display name."""
        return self._name

    @property
    def filter_regexes(self) -> List[str]:
        """Return the list of supported file extensions."""
        return self._filters

    @property
    def filter_descriptions(self) -> List[str]:
        """Return the list of format descriptions."""
        return self._descriptions

    def build_options(self, paths: List[str]) -> None:
        """
        Build the UI options panel for the importer.

        Args:
            paths: List of selected file paths
        """
        with ui.VStack(height=0):
            # Add your custom UI elements here
            ui.Label("test option")
            ui.Label("test option2")
        return True

    async def convert_assets(self, paths: List[str]) -> Dict[str, Union[str, None]]:
        """
        Convert the selected assets to USD.

        Args:
            paths: List of file paths to convert

        Returns:
            Dictionary mapping source paths to converted USD paths
        """
        # Implement your conversion logic here
        return {}


# Example usage:
custom_importer = CustomAssetImporter(
    "My Custom Importer",
    [".*\\.custom1$", ".*\\.custom2$"],
    ["Custom Format 1", "Custom Format 2"]
)
```

### Registration

Register your custom importer when your extension starts:

```python
import omni.kit.tool.asset_importer as ai

# Register the importer
ai.register_importer(custom_importer)

# When your extension is disabled, remove the importer
ai.remove_importer(custom_importer)
```

## Best Practices

1. **Format Support**: Check if a format is already supported before registering:
   ```python
   if not ai.is_supported_format(".your_extension"):
       ai.register_importer(your_importer)
   ```
    __NOTE__: The importer call sequence is dependent on the register order. So if there are multiple importers that support the same extension, it will only call the first one found.

2. **Error Handling**: Implement proper error handling in your conversion logic
3. **UI Design**: Keep the options UI clean and intuitive
4. **Performance**: Optimize conversion for large files
5. **Documentation**: Document your custom importer's features and requirements

### Troubleshooting

Common issues and solutions:

1. **Importer not appearing in UI**
   - Verify the extension dependency is correctly set
   - Check if the importer is properly registered
   - Ensure file extensions match the filter patterns

2. **Conversion failures**
   - Verify file format compatibility
   - Check for proper error handling
   - Ensure all required dependencies are installed

3. **UI issues**
   - Verify UI elements are properly initialized
   - Check for proper cleanup in the `build_options` method

For additional support, please refer to the [Omniverse documentation](https://docs.omniverse.nvidia.com) or visit the [Omniverse Forums](https://forums.developer.nvidia.com/c/omniverse/300).