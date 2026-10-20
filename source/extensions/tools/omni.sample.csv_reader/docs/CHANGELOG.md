# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.2.0] - 2025-10-24

### Changed
- Updated to match Python API conventions and standards
- Improved test coverage with comprehensive unit and integration tests

## [1.1.0] - 2025-06-10

### Added

- Progress bar showing CSV processing progress with real-time updates
- Real-time status updates during generation
- CSV file validation with immediate feedback
- Row count display for loaded CSV files
- Asynchronous processing to keep UI responsive

### Changed
- Refactored from omni.csv.reader to omni.sample.csv_reader
- Renamed base classes for better clarity
- Updated comments for consistency
- Removed unnecessary imports
- Improved UI alignment code
- Improved error handling with specific error messages
- Better string formatting using f-strings
- Generate button now disabled during processing
- Enhanced user feedback with success/error indicators
- Processing now yields to UI every 10 rows for smooth progress updates
- Status indicators use color-coded text
- Improved code documentation with clear variable names and detailed comments
- Extracted magic numbers into named constants for better maintainability
- Added comprehensive docstrings and inline documentation
- Cleaner prim naming using generic 'prim_N' pattern instead of 'box_N'

### Fixed
- Scene preservation: Generate now adds to existing scene instead of clearing it
- File dialog now opens in current CSV file's directory

## [1.0.0] - 2022-07-01
### Known limitations
- CSV files must contains X,Y,Z and cluster columns
- nothing happens if no CSV file (not found/wrong type/etc...)
- for now, the scene is reset prior generating the overlay...to be updated in next version
