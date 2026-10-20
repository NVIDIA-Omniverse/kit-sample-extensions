```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

# Overview

The **omni.kit.tool.teleport** extension provides an interactive mechanism to reposition the viewport camera using a visual teleport widget. It processes user inputs such as mouse movements and clicks to calculate new camera positions and orientations based on ray query hit results. This tool enhances scene navigation by offering visual feedback and customizable interaction for efficient repositioning within complex scenes.

## Concepts

- The extension revolves around a [Teleport](omni.kit.tool.teleport/omni.kit.tool.teleport.Teleport) class, which encapsulates the logic for interactive teleportation. It uses ray query results to determine valid destinations in the scene.
- It provides a singleton instance via the [get_instance](omni.kit.tool.teleport/omni.kit.tool.teleport.get_instance) API, ensuring that a single, consistent teleport tool instance manages all teleport behavior.
- The tool integrates camera repositioning with interactive widget updates, making it easier for users to control the viewport navigation dynamically.

## Functionality

- Processes mouse events to compute and update new camera positions in the viewport.
- Calculates appropriate camera orientation and focus distance derived from ray query hit results.
- Offers interactive methods—such as on_moved, on_drag, end_drag, and on_clicked—to manage the teleportation workflow and visual feedback.
- Provides methods to enable or disable picking and to customize the teleport widget by setting a specific USD file for visual representation.

## Key Components

- **[Teleport](omni.kit.tool.teleport/omni.kit.tool.teleport.Teleport)**: The primary class responsible for handling teleport interactions. Its methods manage the teleport logic from processing input events to updating the camera’s transform.
- **[get_instance](omni.kit.tool.teleport/omni.kit.tool.teleport.get_instance)**: A static method that returns the singleton instance of the [Teleport](omni.kit.tool.teleport/omni.kit.tool.teleport.Teleport) class, ensuring unified state management across the interface.
- Customization methods, like set_widget_usd_file and unbind_widget_material, allow users to adjust the visual appearance and behavior of the teleport widget.

## Settings

The extension offers settings that adjust its operational parameters, such as:
- The teleport eye height, controlling the vertical offset used during teleportation.
- Widget scale and ring manipulator options (visibility, fixed size, scale, min/max sizes) that govern the appearance and interactivity of the teleport widget.
- A flag for showing position information, allowing further customization of the tool’s display characteristics.

## Relationships

- Uses the viewport pick query (`request_query`) to find the surface under the cursor and detect valid teleport destinations.
- Leverages **omni.ui** and **omni.ui.scene** for constructing and managing the interactive components of the teleport widget.
- Compatible with viewport-related dependencies like **omni.kit.viewport.utility** and **omni.kit.viewport.registry** to ensure consistent behavior within the viewport environment.

