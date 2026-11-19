# Minimap Extension

A minimap extension that generates top-down views of your stage with navigation capabilities.

## Key Features

- Automatic minimap generation from stage geometry
- Custom floor/ceiling bounds definition
- Waypoint visualization and navigation
- Tile-based rendering with configurable resolution
- Real-time navigation and orientation tracking
- Mouse Control:
  - Teleport: LMB Double-click anywhere on the minimap
  - Rotate: Drag camera FOV icon to rotate the camera
  - Pan: LMB Drag to pan the minimap view
  - Zoom: Mouse wheel to zoom in/out of the minimap

## Performance Optimization

### Developer Mode (DEV-mode)

The extension includes `DEV` warning logger, this is especially useful for:
- Identifying excessive update calls
- Diagnosing UI lag or stuttering
- Optimizing refresh rates during navigation
- Ensuring zero updates when camera is stationary

**To enable:**
1. Open `omni/sample/minimap/settings.py`
2. Set `DEV_MODE = True` or click on `DEV` button in minimap settings
3. Launch the extension and watch the console

**What to look for:**
- When camera is **STATIONARY**: `UI refresh frequency` should be `0.0 calls/sec`
- When camera is **NAVIGATING**: Should be < 10 calls/sec (typically 1-3 calls/sec)
- If either condition is violated, check the call chain for missing throttling or caching

**See the comprehensive documentation in `settings.py` for detailed optimization strategies.**