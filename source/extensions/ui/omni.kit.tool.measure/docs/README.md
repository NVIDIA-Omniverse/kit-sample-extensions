## Measure Tool [omni.kit.tool.measure]

Measure Tool is a viewport authoring tool for creating measurements between prims within a USD stage. It supports live collaboration, meaning measurements made in a shared session are replicated to other users.

### Measure Sub-Tools

Measure provides a set of sub-tools, each designed for a specific type of measurement:

| Sub-Tool | Description |
|:---|:---|
| **Point-to-Point** | Measures the distance between 2 points. |
| **Multi-Point** | Strings together multiple Point-to-Point dimensions sharing anchor points, with an aggregate sum result. |
| **Angle** | Measures the angle defined by three user-placed points. |
| **Diameter** | Measures the diameter of circular shapes using two points. |
| **Area** | Measures the area of a user-defined region on a flat plane. Requires a minimum of three points. |
| **Measure Selected** | Measures a point-to-point distance between two selected prims using Minimum, Maximum, or Center distance. |

### Common Controls

- **Left-Click** creates a new anchor point.
- **Right-Click**, **Enter**, or the on-screen **Complete** button finalizes measurements with an arbitrary number of points (Multi-Point, Area).
- **Escape** cancels the current measurement at any time.
- **Delete** removes the currently selected measurement.
- Measurements with a fixed number of anchor points (Point-to-Point, Angle, Diameter) complete automatically when the required points are placed.

### Accessing the Tool

Measure can be opened from the main menu under **Tools > Measure**, or from the Navigation bar at the bottom of the viewport in USD Explorer.

### UI Panels

The Measure Tool window is organized into the following panels:

| Panel | Description |
|:---|:---|
| **Sub-Tool Selector** | Toolbar of available measurement sub-tools. Also contains the **Selected Mode** dropdown for Measure Selected (Min, Max, Center). |
| **Placement** | Controls for snapping and constraint options. Only visible when a sub-tool is active. |
| **Display** | Configuration for measurement appearance: units, precision, label size, axis display, and color. |
| **Manage** | Lists all measurements in the scene with controls for visibility, renaming, navigation, and deletion. |

The **Placement**, **Display**, and **Manage** panels are collapsible. Their initial collapsed state can be configured via the `startup_ui_collapsed` setting.

### Placement Parameters

The Placement panel controls how measurement points are placed in the viewport. Only one snap mode can be active at a time.

#### Snap To

Selects between **Custom** snapping modes and **Perpendicular** mode. Perpendicular mode locks a point along the surface normal of the first selection and is available only for the Point-to-Point sub-tool. Selecting Perpendicular automatically enables Surface snap.

#### Snap Modes

| Snap Mode | Description |
|:---|:---|
| **Surface** | Snaps the point to the surface hit by the raycast. |
| **Vertex** | Snaps the point to the nearest vertex of the hit surface. |
| **Mid Point** | Snaps the point to the midpoint of the nearest edge of the hit surface. |
| **Center** | Snaps to the bounding box center of the hit object. |
| **Edge** | Snaps the point to the nearest edge of the hit surface. |
| **Pivot** | Snaps the point to the pivot of the hit object. |

> **Note:** Vertex, Edge, and Mid Point snap modes require the `/rtx-transient/scenedb/useUniformsReindexing` setting to be `true` (enabled by default in the extension).

#### Constrain To (Area sub-tool only)

Constrains measurement points to a plane defined by the selected axis:

| Constraint | Description |
|:---|:---|
| **X** | Constrain to the X axis plane. |
| **Y** | Constrain to the Y axis plane. |
| **Z** | Constrain to the Z axis plane. |
| **Stage Up** | Constrain to the stage up-axis plane (default). |
| **Dynamic** | Determines the constraint plane from the first 3 points placed. |

### Display Parameters

The Display panel configures how measurements are rendered in the viewport.

| Option | Description |
|:---|:---|
| **Display XYZ** | Shows World or Local axis dimensions alongside the measurement. Local is based on the first selection's transform. Point-to-Point only. |
| **Units** | Sets the display unit for measurement values. Options: Centimeters, Millimeters, Decimeters, Meters, Kilometers, Inches, Feet, Miles. |
| **Precision** | The number of decimal places to display before rounding. Options range from integer (0) to hundred-thousandths (5). |
| **Label Size** | Font size for measurement labels. Options: Small, Medium, Large, Extra Large. |
| **Line Color** | The color of the measurement line and points. Must be set before placing the first point of a measurement. |

### Manage Panel

The Manage panel lists all measurements in the current scene and provides the following controls per measurement:

| Control | Description |
|:---|:---|
| **Visible** | Toggles the visibility of the measurement in the viewport. |
| **Go To** | Frames the measurement in the viewport camera. |
| **Name** | The name of the measurement. Double-click to rename. |
| **Value** | The current computed value of the measurement. |
| **Type** | The sub-tool type used to create the measurement. |
| **Delete** | Deletes the measurement. |

The list can be searched and filtered by measurement type using the controls at the top of the panel.

#### Export to CSV

Measurements can be exported to a `.csv` file:

1. Open the Manage panel.
2. Click the **Options** button in the upper right corner.
3. Select **Export to CSV**.
4. Choose a file path and press **Export**.

### Extension Configuration

The following settings can be configured in `extension.toml` under `[settings]` to customize the extension behavior per-application:

| Setting | Type | Default | Description |
|:---|:---|:---|:---|
| `startup_tool` | String (MeasureMode name) | `"NONE"` | The measurement sub-tool to activate when the Measure window is opened. Valid values: `NONE`, `POINT_TO_POINT`, `MULTI_POINT`, `ANGLE`, `DIAMETER`, `AREA`. |
| `startup_snap_type` | String (SnapMode name) | `"SURFACE"` | The snap mode to activate on startup. Valid values: `SURFACE`, `VERTEX`, `PIVOT`, `EDGE`, `MIDPOINT`, `CENTER`. |
| `startup_ui_collapsed` | Array of Strings | `[]` | Panel names to collapse on startup (e.g., `["Placement", "Display"]`). |
| `enable_hotkeys` | Boolean | `false` | Enables the hotkey system for the Measure Tool. |
| `enable_highlighting` | Boolean | `true` | Enables hover highlighting over measurements in the viewport. |

Example configuration:

```toml
[settings]
exts."omni.kit.tool.measure".startup_tool = "POINT_TO_POINT"
exts."omni.kit.tool.measure".startup_snap_type = "VERTEX"
exts."omni.kit.tool.measure".startup_ui_collapsed = ["Display", "Manage"]
exts."omni.kit.tool.measure".enable_hotkeys = true
exts."omni.kit.tool.measure".enable_highlighting = true
```

The `startup_tool` and `startup_snap_type` values defined in `extension.toml` are the application defaults. Users can override these per-setting through the **Preferences > Measure** panel by enabling the **Override** checkbox for each setting and selecting a value from the dropdown. When the override checkbox is disabled, the `extension.toml` default is used.

### Hotkeys

Hotkeys are disabled by default. Enable them by setting `enable_hotkeys = true` in the extension configuration. Once enabled, the following hotkeys are available when the Measure window is visible:

| Action | Default Key | Description |
|:---|:---|:---|
| Next Tool | `PAGE_UP` | Cycles forward through the measurement sub-tools. |
| Previous Tool | `PAGE_DOWN` | Cycles backward through the measurement sub-tools. |
| Next Snap | `ALT + S` | Cycles through the available snap modes. |
| Open | *(none)* | Opens the Measure Tool window. No default binding. |

Hotkey bindings can be overridden in the extension settings:

```toml
[settings]
exts."omni.kit.tool.measure".hotkeys.open = ""
exts."omni.kit.tool.measure".hotkeys."next-tool" = "PAGE_UP"
exts."omni.kit.tool.measure".hotkeys."previous-tool" = "PAGE_DOWN"
exts."omni.kit.tool.measure".hotkeys."next-snap" = "ALT + S"
```

### Registered Actions

| Action ID | Display Name |
|:---|:---|
| `omni.kit.tool.measure-open` | measure::open |
| `omni.kit.tool.measure-next-tool` | measure::next-tool |
| `omni.kit.tool.measure-previous-tool` | measure::previous-tool |
| `omni.kit.tool.measure-next-snap` | measure::next-snap |

### Viewport Display Toggle

Measurement visibility in the viewport can be toggled independently of the Measure Tool window through the viewport menubar under **Show By Type > Measurements**.
