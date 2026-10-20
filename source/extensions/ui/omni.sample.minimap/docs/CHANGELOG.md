# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.1.0] - 2026-02-19
### Added
- Unit and integration test suite for extension, generator, and window modules
- API documentation

### Fixed
- DEV_MODE accessor and toggle routing through `carb.settings`
- Silent exception swallowing in `_on_stage_opened`

### Changed
- Code style and formatting aligned with repository conventions
- Extracted `TOOLTIP_STYLE` constant, minor type annotation and import cleanup

## [1.0.2] - 2025-10-23
### Added
- Camera FOV handle can be scaled via UI, also added devmode toggle
- Improved locked navigation, stage can be "dragged" under the camera
- Improved unlocked navigation, camera now teleports while stage stays
- Markup mode automatically disables when camera is moved / teleported
- UI refresh throttling to limit UI refreshes 10 calls/sec for navigation
- UI refresh frequency logging to diagnose excessive updates
- Improved out of bounds recovery and teleportation

### Technical Improvements
- Added `wp.synchronize()` before GPU-to-CPU transfer (for Linux CUDA)
- Waypoints and markups now update in minimap based on viewport settings
- Implemented throttled update mechanism in `SimpleModel._on_update()`
- Added window flags to prevent deferred rendering from freezing minimap
- Position threshold checks to prevent updates when camera moves < 10cm
- Minimap camera indicator no longer updates when stationary (0.0 calls/sec)
- Reduced refresh calls from 50/s to ~0.3/s during typical use

### Developer Experience
- DEV_MODE flag in settings.py for performance monitoring
- Detailed performance optimization guide in settings.py module
- Clear examples of before/after optimization metrics
- Actionable strategies for identifying performance issues

## [1.0.1] - 2025-10-17
### Added
- Minimap tiles now transfer immediatelly to RAM after generation
- Increased zoom out from 5000 to 50000 for better scene overview
- Configurable build delay to prevent black tiles during generation

### Technical Improvements
- Enhanced MapTile class with proper GPU cleanup
- Improved async task management across all modules

### Developer Experience
- Streamlined codebase with more concise and readable code structure

## [1.0.0] - 2025-07-17
### Changed
- Initial Release
