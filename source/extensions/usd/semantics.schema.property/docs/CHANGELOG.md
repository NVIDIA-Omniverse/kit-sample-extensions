# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.0.2] - 2026-06-03
### FIXED
- Updated message-bus subscription to use string-name `observe_event(event_name=..., on_event=...)` for additional changed path events

## [2.0.1] - 2025-05-20
### CHANGED
- Wrapped modifications, additions, and removals of semantics in an Sdf.ChangeBlock

## [2.0.0] - 2025-04-24
### CHANGED
- Updated to support new UsdSemantics schema

## [1.1.0] - 2025-03-05
### CHANGED
- Update to kit 107

## [1.0.5] - 2024-10-22
### CHANGED
- moved "omni.kit.test" dependency to test

## [1.0.4] - 2024-09-03
### CHANGED
- semantics import fix: `from pxr import Semantics` to `import Semantics`

## [1.0.3] - 2024-04-22
### FIXED
- Fix implicit dependency on semantics usd schema, make it explicit

## [1.0.2] - 2023-11-13
### ADDED
- Add red border to input field when it contains an invalid entry
- Add unit tests to property extension

## [1.0.1] - 2023-11-09
### FIXED
- Fixed a typo in the extension description

### CHANGED
- Don't allow ":" characters or blank entries when modifying semantics

## [1.0.0] - 2023-10-27
### ADDED
- Initial implementation of the Semantics property widget
    - Allow viewing of semantics on selected prims
    - Allow simple edits to semantic data on selected prims
