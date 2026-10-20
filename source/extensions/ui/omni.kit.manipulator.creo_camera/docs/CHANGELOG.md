# Changelog

## [0.8.4] - 2026-04-02
- bump version to force release

## [0.8.3] - 2026-03-11

### Fixed
- Replaced invalid/corrupted placeholder PNG files (icon.png and preview.png) with proper PNG images
  - icon.png was 0 bytes (empty file, failed LFS checkout)
  - preview.png was 45-byte ASCII text "PNG placeholder - binary file would be needed"
  - Both now replaced with properly generated PNG images (icon: 256x256, preview: 512x512)

## [0.8.1] - 2025-10-03

### Added
- Orthographic gesture visualizers
  - CreoOrthoVisualizer: Dedicated visualizer for orthographic pan and zoom
  - Both markers use NDC positioning (simpler than perspective)
  - Fixed marker stays at initial click position
  - Moving marker follows cursor (both XY for pan, Y-only for zoom)

### Fixed
- Atomic position updates for orthographic visualizers
  - All visual elements (fixed marker, moving marker, line) update together
  - Prevents shaking/jittering during camera movement
  - Fixed and moving markers now properly positioned at line endpoints

### Changed
- Orthographic gestures now share CreoOrthoVisualizer instances
- Consolidated update logic to single function for consistency

## [0.8.0] - 2025-10-02

### Added
- Visual feedback for camera gestures
  - CreoPanVisualizer: Shows two diamond markers (world and screen space) connected by red line during pan
  - CreoZoomVisualizer: Shows two diamond markers (world space follows cursor, screen space Y-only) with red line during zoom
  - CreoRotateVisualizer: Shows single diamond marker at rotation center during rotation
- Nested square markers with depth separation
  - 40px black outer square (z=0)
  - 30px white middle square (z=2)
  - 20px inner square (z=4) with color state:
    - Red when no movement (at starting position)
    - Green when actively moving
- CreoVisualizerBase: Shared base class for all visualizers
  - Common nested squares rendering with Z-offset to prevent z-fighting
  - Common color management based on movement state
  - Common visibility control
- Smart movement detection
  - Tracks total accumulated movement from gesture start
  - Only updates visualization when state changes (prevents flickering)
  - Returns to red when user returns cursor to original position

### Changed
- All gestures now accept optional visualizer parameter
- Visualizers show immediately on gesture start (pan/zoom show screen marker, rotate waits for raycast)
- World markers appear after raycast completes for stable positioning

## [0.1.0] - 2025-10-02

### Added
- Orthographic camera support
  - CreoOrthoPanGesture: Pan in orthographic views
  - CreoOrthoZoomGesture: Drag zoom with aperture adjustment and pan compensation
  - CreoOrthoScrollZoomGesture: Scroll zoom with aperture adjustment around cursor
  - Orthographic fallback: When raycast misses in ortho, uses world origin plane intersection
- CreoGestureManager: Automatic perspective/orthographic gesture prevention
  - Detects camera mode from viewport_api.projection in real-time
  - Prevents conflicting gestures based on camera mode
  - Works before model initialization
- Configuration constants
  - LIMIT_SCROLL_ZOOM_BY_DISTANCE: Optional distance limiter for scroll zoom (default: True)
  - ORTHO_FALLBACK_TO_WORLD_ORIGIN_PLANE: Ortho raycast fallback to world plane (default: True)
- Rotation enabled in orthographic mode (matches Kit behavior for user cameras)

### Fixed
- Perspective scroll zoom: Refresh model from USD on every scroll to prevent jumps after focus
- Orthographic pan: Update both transform and initial_transform to maintain sync after focus
- Orthographic zoom: Use initial_aperture (refreshed from USD) to prevent zoom level resets
- Drag zoom initialization: Call super().on_began() before reading transform for correct USD values
- Model initialization: Proper ndc_scale calculation on first scroll

### Changed
- Orthographic zoom direction inverted to match standard CAD behavior

## [0.0.1] - 2025-10-01

### Added
- Initial release of Creo Camera Manipulator extension
- Rotation gesture (MMB): Rotate camera around raycast-determined point
  - Horizontal movement rotates around camera Y axis
  - Vertical movement rotates around camera X axis
- Pan gesture (Shift + MMB): Pan camera while keeping clicked 3D point under cursor
  - Screen-space tracking ensures clicked point stays under cursor
- Zoom gesture (Ctrl + MMB): Zoom toward/away from clicked point
  - Vertical mouse movement controls zoom distance
  - Camera moves forward/backward along view direction
  - Pan compensation keeps target at initial screen position
  - Smooth handling when zooming past target point
- Scroll zoom (Mouse Wheel): Discrete zoom with per-scroll raycast
  - Each scroll updates focus point at current cursor position
  - Stateless operation - no state carried between scrolls
  - Uses same zoom mathematics as drag zoom
- Raycast-based gesture system
  - Async raycasts determine 3D interaction points
  - Mouse movement accumulates during raycast
- Proper USD integration
  - Model initialization from USD camera transforms
  - Undo/redo support for camera movements
- Automatic viewport registration via RegisterScene API
- Clean extension lifecycle (startup/shutdown with state restoration)

### Technical Implementation
- Extends omni.kit.manipulator.camera.ViewportCameraManipulator
- Custom gesture base class (CreoGestureBase) with shared raycast logic
- Shared zoom math module (creo_zoom_math.py) for code reuse
- Proper model initialization including ndc_scale calculation
- Integration with Kit camera speed system (move_speed, world_speed)
