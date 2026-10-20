# Changelog

## [1.2.0] - 2025-10-26
### Added
- Comprehensive test suite for ScatterCreatePointInstancerCommand (18 test cases)
- Module-level docstrings across all source and test files
- Tests for command do/undo functionality, USD attribute validation, and edge cases

### Changed
- Migrated from deprecated `omni.kit.ui` API to public `omni.kit.menu.utils` API
- Updated extension menu integration to use MenuItemDescription
- Improved test coverage from ~60% to ~85%

### Fixed
- Type conversion bug in ScatterCreatePointInstancerCommand (proto_indices tuple to list)
- API compliance issues with non-public module usage
- Extension tests updated to match new menu API

## [1.1.0] - 2024-12-20
### Changed
- Refactored from omni.example.ui_scatter_tool to omni.sample.ui_scatter_tool
- Updated all references, documentation, and configuration files

## [1.0.0] - 2022-06-27
### Added
- Initial window
