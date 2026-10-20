# omni.kit.viewport.navigation.camera_manipulator

Provides the camera navigation controls in the Viewport bottom menu bar: **Orbit**, **Look**, **Pan**, **Dolly**, and **Frame**.

## Features

- **Orbit** — tumble the camera around a focal point. Double-click any object to set a persistent orbit target; a visual indicator tracks the target while it is active.
- **Look** — rotate the camera in-place (first-person look-around).
- **Pan** — slide the camera parallel to the view plane.
- **Dolly** — move the camera along the view axis (scroll wheel or drag).
- **Frame** — fit the current selection (or the whole scene) into view.

## Orbit Target

Double-clicking an object sets an explicit **orbit target** at the hit position. Subsequent orbit gestures pivot around that point rather than the default 5 m center-of-interest. The target is cleared when you switch to Look mode or press A/D/Q/E while holding the right mouse button.

Section-plane awareness: if a section plane is active, only geometry in the non-sectioned region can become an orbit target.

## Settings

| Setting path | Default | Description |
|---|---|---|
| `exts/omni.kit.viewport.navigation.camera_manipulator/defaultOrbitDistance` | 500 cm | Focus distance used when no orbit target is set. |
| `/persistent/exts/omni.kit.viewport.navigation.camera_manipulator/orbitMaintainDistanceToFocal` | false | When `true`, re-targeting keeps the camera at the same distance from the hit point. |
| `exts/omni.kit.viewport.navigation.camera_manipulator/maxNavigationMagnitude` | 2000 | Maximum world-space speed magnitude for Pan and Dolly. |
| `exts/omni.kit.viewport.navigation.camera_manipulator/minCoiDistance` | 1.0 | Minimum center-of-interest distance; prevents navigation from stalling near geometry. |
