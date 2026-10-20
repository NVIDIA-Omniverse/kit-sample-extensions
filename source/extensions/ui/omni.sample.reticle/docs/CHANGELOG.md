# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.5.0] - 2025-12-03
### Added
- Type hints and docstrings for all public APIs
- Technical documentation for CompositionGuidelines enum and safe area constants

### Changed
- Use RegisterViewportLayer for viewport overlay with both UI widgets and scene graphics
- Updated copyright headers to SPDX-FileCopyrightText format (2025)
- Updated tests to match new architecture

### Removed
- Legacy viewport support code

### Fixed
- Reticle now correctly renders in its own viewport when multiple viewports are open

## [1.4.0] - 2025-06-10
### Changed
- Refactored from omni.example.reticle to omni.sample.reticle
- Updated all references, documentation, and configuration files

## [1.3.1] - 2022-09-09
### Changed
- Fixed on_window_changed callback for VP2

## [1.3.0] - 2022-09-09
### Changed
- Fixed bad use of viewport window frame for VP2
- Now using ViewportAPI.subscribe_to_render_settings_change() to update reticle on resolution changes.

## [1.2.0] - 2022-06-24
### Changed
- Refactored to omni.example.reticle
- Updated preview.png
- Cleaned up READMEs

### Removed
- menu.png

## [1.1.0] - 2022-06-22
### Changed
- Refactored reticle.py to views.py
- Fixed bug where Viewport Docs was being treated as viewport.
- Moved Reticle button to bottom right of viewport to not overlap axes decorator.

### Removed
- All mutli-viewport logic.

## [1.0.0] - 2022-05-25
### Added
- Initial add of the Sample Viewport Reticle extension.