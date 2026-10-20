# Changelog

Omniverse Kit UsdShade Editor

## [2.3.4] - 2026-10-19
### Fixed
- Resolve Kit extension build dependencies through the selected kernel or SDK layout.

## [2.3.3] - 2026-10-17

### Changed

- Republish through the verified Windows signing path with signed package metadata.

## [2.3.2] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: use the current glyph interface and preserve graph position and notification handling.

## [2.3.1] - 2026-08-28

### Fixed

- MDL concrete and polymorphic ports now use the same implicit-conversion policy, allowing scalar `float` outputs to connect to compatible `Float2` and `Float3` constructor inputs (NVBug 6683949).
- Single-input polymorphic constructor families are kept separate from multi-input constructors that share an MDL base name, preserving the `x`, `y`, and `z` connections on component constructors.
- Connection regression coverage now spans every supported built-in type direction, all concrete/unresolved endpoint permutations, and every input on the affected `Float2` and `Float3` constructors.

## [2.3.0] - 2026-08-19

### Fixed

- MaterialX terminal semantics such as EDF and VDF now author valid USD token ports instead of raising invalid-type command errors.
- Failed port creation no longer leaves `NodeGraphNodeAPI` partially applied to the shader prim.
- Missing shader identifiers, source assets, and subidentifiers keep the graph open and render an actionable validation state on the affected node.
- Connection rewires, node creation, grouping, ungrouping, renaming, and solo operations now preserve exact USD state across failure and undo/redo.
- Texture validation, stage listeners, command result propagation, shutdown cleanup, and test discovery are hardened against silent failures and resource leaks.
- Catalog context and text filters now notify the UI when visibility changes inside an otherwise visible group.
- Malformed compound file-save events are contained instead of escaping the catalog listener.
- Material Graph Python coverage is scoped in the extension test configuration for direct coverage runs.
- Fast headless native tests use Kit's standard doctest library integration to cover GraphCanvas scene building, layout, cycles, disconnected graphs, port colors, and rendering-data defaults.
- USD precision-suffixed type names such as `color3f` and `matrix4d` now contribute their correct dimension to port colors.
- Malformed self-connected nodes remain visible during automatic GraphCanvas layout.
- Position, port, connection, solo, and node-creation commands now mutate the model's owning USD stage in non-default contexts.
- Failed prim creation and compound import now restore the exact edit layer, including partial specs that do not compose to a valid prim.
- Invalid texture-shader catalog metadata is reported through the graph error UI instead of escaping the drop callback.
- Native GraphCanvas tests now live alongside the plugin implementation under its `tests` directory.
- Unused performance tracing, native snapshot extraction and indexing, legacy SDR modules, obsolete controller helpers, and dead layout analysis have been removed.
- MaterialX identifier-upgrade checks now remain actionable on Kit 109 hosts whose older MaterialX library leaves legacy identifiers unchanged.
- Graph validation errors and warnings are shown in the widget banners without treating invalid authored material data as an extension runtime failure.
- Fast semantic UI smoke workflows now cover graph opening, catalog visibility, render-context switching, unresolved identifiers, and nested graph navigation.
- Startup, shutdown, background tasks, external UI callbacks, validation collectors, and native scene fallbacks now contain and trace unexpected exceptions through the Material Graph logging channel.

## [2.2.3] - 2026-08-14

### Fixed

- MaterialX upgrade checks safely handle MaterialX-context `UsdPreviewSurface` terminals with authored inputs (NVBug 6575961).
- MaterialX upgrade tests now use deterministic SDR identifier resolution across Kit versions and platforms.

## [2.2.2] - 2026-08-13

### Fixed

- MaterialX identifier repairs now use Kit-provided Python APIs, avoiding native USD ABI coupling across Kit versions.

## [2.2.1] - 2026-08-03

### Added

- Expanded the developer documentation with corrected API examples.

### Changed

- The Help action now opens the public Material Graph guide, and the extension package no longer contains a separately generated user guide.

### Fixed

- Unresolved ID-authored shaders remain visible in the Universal context so their USD-authored fallback ports and missing-definition errors can be displayed instead of being misreported as outside the current graph.

## [2.2.0] - 2026-05-15
### Added
- Added MaterialX upgrade functionality.

### Fixed
- Shader input ports no longer disappear when USD authors a bare per-input `displayGroup` (e.g. `"Albedo"`); the `Inputs:`/`Outputs:` prefix is now re-applied after every metadata merge.

## [2.1.5] - 2026-05-13
### Fixed
- Slow startup times with large graphs.

## [2.1.4] - 2026-05-06
### Fixed
 - Startup screen now shows up when currently edited material is deleted from the stage.
 - Empty NodeGraphs keep the grid background and breadcrumbs visible after all nodes are deleted.
 - MDL polymorphic constructor catalog entries now collapse single-input overloads under result type names, while preserving explicit names for multi-input constructors.
 - MDL polymorphic candidate tooltips now show the correct MDL type names for user-defined struct types such as `::base::texture_return`.
 - MDL polymorphic connection validation now rejects incompatible struct connections while allowing valid `texture_return` inputs.
 - MDL polymorphic input resolution now permits `int` sources to resolve to `float` overloads when no exact `int` overload exists, while still preferring exact overload matches.
 - Schema-driven port group labels no longer accumulate repeated anchor prefixes after node sync, move, or page expansion.

## [2.1.3] - 2026-05-05
### Fixed
 - Fix issue where only every other catalog item could be selected.
 - Drag/drop catalog items into groups.
 - Clean up spacing in graph hamburger menu.
 - Cyclical nodegraphs cannot be created.
 - Renaming input and output ports.
 - Fix polymorphic connection propagation.
 - Renaming material no longer clears editor widget.

 ### Added
 - Right click delete menu for catalog items.
 - Added MDL-aware port type conversion validation with tests, while preserving stricter checks for unsupported and array/enum/struct cases.

## [2.1.2] - 2026-03-26
### Fixed
 - Changing the info attributes will now cause the graph to update.
 - Limit node tooltip hover region to the icon area of the node.
 - Fix force connect.
 - Noodle can be selected and deleted.
 - Clean up spacing graph menu.

## [2.1.1] - 2026-03-24
### Fixed
 - Improved texture preview.
 - Changing the colorNoodles setting now causes the graph to refresh.
 - Cleanup context visibility menu.
 - Procedural port coloring based on underlying property type.
 - Display active material in toolbar.
 - Improved error and warning state reporting.
 - Code cleanup and commenting passes.

## [2.1.0] - 2026-03-22
### Fixed
- Help URL on Linux.
- Catalog search field no longer affects context menu.
- Context menu items sorted alphabetically.
- Remove double connection noodles.
- Rename View menu entries.
- Update MDL logo.
- Selecting edit material on a prim without a material binding no longer results in an error.
- Update edit label on startup screen.
- Catalog items no longer display tooltip if tooltip is empty.
- Polymorphic cascading.
- Remove context drop down in favor of context buttons.
- Hide catalog widget if resized below threshold.

### Added
- Quicksearch support.
- Rewiring support, user can drag connection from one port to another port to re-connect.
- Ctrl+Shift+LMB will force connect.
- Setting for default backdrop color.
- Context soloing.
- Graph canvas and node widgets C++ implementations.

## [2.0.5] - 2026-03-02
### Fixed
- OMPE-83947: Fix Kit 109 DGXC test failures.
- OMPE-83955: Fix Kit 109 ETM test failures.
- Fix Python error caused by non-string value passed to Sdf.ValueTypeNames.Find.
- Reset selection when dropping catalog items.
- Right click context menu displays even if items are selected.

## [2.0.4] - 2026-02-25
### Added
- Initial version of Material Graph 2.0

## [2.0.3] - 2026-02-24
### Added
- Revert changes in 2.0.2
- Same as version 1.9.6

## [2.0.2] - 2026-02-02
### Added
- Initial version of Material Graph 2.0

## [2.0.1] - 2026-02-19
### Fixed
- Same as version 1.9.6

## [2.0.0] - 2026-02-19
### Fixed
- Skip: bad publish
 version 1.9.6
