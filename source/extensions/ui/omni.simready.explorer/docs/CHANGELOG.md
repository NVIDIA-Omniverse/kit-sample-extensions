Changelog
=========

This document records all notable changes to ``omni.simready.explorer`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [1.1.4] - 2025-09-23
### Changed
- OMPE-64544: Use temp directory when renaming for DGXC test failure

## [1.1.3] - 2025-04-01
### Changed
- Expose additional classes and functions to allow for easier subclassing and extension.

## [1.1.2] - 2025-01-09
### Changed
- OMPE-27665: Add python API document.

## [1.1.1] - 2024-08-28
- Updated version to 1.1.1 for publishing

## [1.1.0-alpha.6] - 2024-03-21
- OM-122420: Replace deprecated API from omni.kit.UsdContext.get_layers to omni.kit.usd.layers.

## [1.1.0-alpha.5] - 2023-08-08
- OM-90785: Added "Refresh Assets" command to Options menu.

## [1.1.0-alpha.4] - 2023-06-29
- OM-95538: Don't turn off the instanceable attribute on assets with PhysicsVariant set to RigidBody when drag-and-dropping them into the stage

## [1.1.0-alpha.3] - 2023-06-28
- OM-96886: Update screenshot used in extension registry

## [1.1.0-alpha.02] - 2023-06-02
- OM-95406: Set default physics behavior of all assets to "RigidBody"
- OM-96886: Update badge on SimReady asset thumbnails, and scfreenshot used in Extension Manager

## [1.1.0-alpha.01] - 2023-05-18
- Version update
- OM-95406: Setting default physics on assets to "RigidBody". This can be done through the "/exts/omni.simready.explorer/default_physics" setting in extension.toml
