# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.1] - 2026-10-23

- Require Kit 111.0 or later to prevent compatibility collisions with Kit 110.4 packages.

## [0.1.0] - 2026-04-29
### Added
- Initial release.
- Registers Metrics Assembler resolve rules for UsdGeomCamera scene-unit
  attributes (`focusDistance`, `clippingRange`) so that they are converted
  correctly when a USD layer with a different `metersPerUnit` is referenced,
  sublayered, or payloaded (NVBugs 5494562 / OMPE-61911).
