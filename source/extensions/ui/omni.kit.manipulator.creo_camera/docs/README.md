# Creo Camera Manipulator [omni.kit.manipulator.creo_camera]

Creo-style camera manipulation extension for NVIDIA Omniverse Kit with visual feedback.

## Overview

This extension provides Creo CAD-style camera controls for Omniverse viewports, offering intuitive camera manipulation similar to PTC Creo Parametric. All gestures include visual feedback with diamond-shaped markers that show interaction points and movement state.

## Features

### Gesture Controls

All gestures use the **middle mouse button** with keyboard modifiers and provide **visual feedback**:

- **Rotation** (MMB): Rotate camera around raycast point
  - Horizontal movement: rotate around camera Y axis
  - Vertical movement: rotate around camera X axis
  - **Visual**: Single diamond marker at rotation center (red → green when moving)

- **Pan** (Shift + MMB): Pan camera while keeping clicked 3D point under cursor
  - Tracks mouse movement in screen space
  - Maintains 3D point at cursor position throughout pan
  - **Visual**: Two diamond markers connected by red line:
    - World space marker follows the raycast point
    - Screen space marker stays fixed at initial click position
    - Inner squares turn green when panning, red when at start position

- **Zoom** (Ctrl + MMB): Zoom toward/away from clicked point
  - Vertical mouse movement controls zoom
  - Camera moves along view direction (forward/backward)
  - Automatically pans to keep target point at initial screen position
  - Smoothly handles zooming past target point
  - **Visual**: Two diamond markers with red line (screen marker moves only in Y axis)

- **Scroll Zoom** (Mouse Wheel): Discrete zoom toward cursor
  - Each scroll event raycasts at current mouse position
  - Updates focus point with every scroll
  - Uses same zoom math as drag zoom for consistency
  - Speed adjusts based on viewport scale

### Visual Feedback System

Each marker consists of 3 nested diamond-shaped squares:
- **40px black outer** (z=0)
- **30px white middle** (z=2)
- **20px inner** (z=4) - Color indicates state:
  - **Red**: No movement or returned to start position
  - **Green**: Active movement detected

Z-offsets prevent visual artifacts from overlapping geometry.

### Technical Implementation

#### Raycast-Based Interaction

All gestures perform asynchronous raycasts to determine the 3D point under the cursor:
- On gesture start, raycast determines the target point
- Mouse movement accumulates while raycast completes
- Gesture executes with accumulated movement once raycast finishes

#### Zoom Mathematics

The zoom implementation maintains screen-space consistency:

1. **Forward Movement**: Camera moves along its view direction (no rotation)
2. **Pan Compensation**: Calculates screen-space error and applies X/Y pan to restore target position
3. **Behind Camera Handling**: When target goes behind camera, continues along average movement direction
4. **State Tracking**: Drag zoom tracks cumulative movement from gesture start for smooth continuous zoom

Scroll zoom is stateless - each scroll event is independent with a new raycast.

#### Model Initialization

The extension properly initializes the camera manipulator model by:
- Calling parent `_on_began` to read transform from USD
- Computing `ndc_scale` for proper speed calculation
- Setting up USD context for undo operations

## Architecture

```
CreoCameraManipulator (extends ViewportCameraManipulator)
├── Gestures
│   ├── CreoGestureBase (base class with raycast support)
│   │   ├── CreoRotateGesture + CreoRotateVisualizer
│   │   ├── CreoPanGesture + CreoPanVisualizer
│   │   └── CreoZoomGesture + CreoZoomVisualizer
│   ├── CreoScrollZoomGesture (extends sc.ScrollGesture)
│   └── Orthographic variants (CreoOrthoPanGesture, CreoOrthoZoomGesture, etc.)
├── Visualizers
│   ├── CreoVisualizerBase (shared rendering and color management)
│   │   ├── CreoRotateVisualizer (single world marker)
│   │   ├── CreoPanVisualizer (two markers + line)
│   │   └── CreoZoomVisualizer (two markers + line, Y-only)
│   └── CreoVisualizerModelBase (shared model structure)
└── Utilities
    ├── creo_zoom_math.py (shared zoom calculations)
    └── creo_gesture_manager.py (perspective/ortho gesture prevention)
```

## Usage

The extension automatically registers itself with all viewports and disables the default Kit camera manipulator on startup.

No additional setup required - simply enable the extension and the Creo camera controls become active.

## Key Bindings

| Action | Binding |
|--------|---------|
| Rotate | Middle Mouse Button |
| Pan | Shift + Middle Mouse Button |
| Zoom (drag) | Ctrl + Middle Mouse Button |
| Zoom (scroll) | Mouse Wheel |

## Implementation Notes

- Extends `omni.kit.manipulator.camera.ViewportCameraManipulator`
- Uses `omni.kit.viewport.registry.RegisterScene` for automatic viewport registration
- Disables default camera manipulator to prevent conflicts
- Integrates with Kit's USD camera system for proper undo/redo support
- Async raycasts ensure responsive interaction even with complex scenes
