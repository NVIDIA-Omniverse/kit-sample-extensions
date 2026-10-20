# Changelog

## [1.21.0] - 2026-09-02
### Changed
- Update `usd-validation-nvidia` Python dependency to `1.21.0`.
- Expose the `instance_prototypes` validation option from the Kit engine.
- Keep validation process workers disabled in the Kit extension.

## [1.20.2] - 2026-07-27
### Fixed
- Update USD Validation NVIDIA documentation links to GitHub Pages.

## [1.20.1] - 2026-07-02
### Fixed
- Fix log supression on async execution.

## [1.20.0] - 2026-07-02
### Changed
- Update `usd-validation-nvidia` Python dependency

## [1.19.7] - 2026-06-24
### Changed
- Update `usd-validation-nvidia` Python dependency

## [1.19.6] - 2026-06-15
### Changed
- Remove SimReady documentation from the published docs.

## [1.19.5] - 2026-06-11
### Added
- Re-export requirement protocol types from `usd-validation-nvidia`

### Changed
- Update `usd-validation-nvidia` Python dependency

## [1.19.4] - 2026-05-20
### Changed
- Remove duplicated `source/python` tests and the standalone repo test suite

## [1.19.3] - 2026-05-19
### Changed
- No core changes

## [1.19.2] - 2026-05-15
### Added
- Add security policy documentation

### Changed
- Remove internal GitLab badge links from the root README

## [1.19.1] - 2026-05-12
### Fixed
- Update requirements override compatibility test for `usd-validation-nvidia` registry semantics

## [1.19.0] - 2026-05-11
### Changed
- Update `usd-validation-nvidia` Python dependency to `1.19.0`

## [1.18.1] - 2026-04-29
### Added
- `FormatDependencyId` exported from `omni.asset_validator.core`
### Changed
- Update Python dependency 1.18.1

## [1.18.0] - 2026-04-27
### Added
- `AssetFormat` protocol and registry for non-USD asset formats
- `CheckFormatDependency` callback and `FormatDependency` context object
- `basename` and `relative_uri` methods on `UriResolver` protocol

### Changed
- Remove SimReady validators from core
- Update Python dependency 1.18.0

## [1.17.0] - 2026-04-17
### Added
- `UriResolver` protocol with `parent_uri` and `join_uri`, extracted from `ValidationEngine`
### Changed
- Update Python dependency 1.17.0

## [1.16.0] - 2026-04-14
### Changed
- Update Python dependency 1.16.0

## [1.15.1] - 2026-03-24
### Changed
- Update Python dependency 1.15.1

## [1.15.0] - 2026-03-22
### Changed
- Update Python dependency 1.15.0

## [1.14.0] - 2026-03-16
### Changed
- Update Python dependency 1.14.0

## [1.13.0] - 2026-03-10
### Changed
- Update Python dependency 1.13.0

## [1.12.0] - 2026-02-26
### Fixed
- `is_omni_path`: Add `OmniverseKitViewportCameraMesh` as path name.
### Changed
- Update Python dependency 1.12.0

## [1.11.2] - 2026-02-25
### Changed
- Update Python dependency 1.11.2

## [1.11.1] - 2026-02-17
### Changed
- Update Python dependency 1.11.1

## [1.11.0] - 2026-02-11
### Changed
- Update Python dependency 1.11.0

## [1.10.8] - 2026-02-08
### Changed
- Update Python dependency 1.10.8

## [1.10.7] - 2026-02-06
### Changed
- Update Python dependency 1.10.7

## [1.10.6] - 2026-01-27
### Changed
- Update Python dependency 1.10.6

## [1.10.5] - 2026-01-15
### Changed
- Update Python dependency 1.10.5

## [1.10.4] - 2026-01-14
### Changed
- Update Python dependency 1.10.4

## [1.10.3] - 2026-01-09
### Changed
- Update Python dependency 1.10.3.

## [1.10.2] - 2026-01-09
### Changed
- Update Python dependency 1.10.2.

## [1.10.1] - 2026-01-08
### Changed
- Update Python dependency 1.10.1.

## [1.10.0] - 2026-01-06
### Changed
- Requirements: Use the new Requirements enumeration.
- Update Python dependency 1.10.0.

## [1.9.2] - 2025-12-11
### Changed
- Update Python dependency 1.9.2.

## [1.9.1] - 2025-12-10
### Changed
- Update Python dependency 1.9.1.

## [1.9.0] - 2025-12-09
### Changed
- UsdzPackageValidator: Use the new UsdzPackageValidator from Pixar.
- Updated Python dependency 1.9.0.

## [1.8.0] - 2025-11-20
### Fixed
- PedestrianCapabilityChecker: Fix mesh bound calculation.

## [1.7.1] - 2025-11-11
### Changed
- Fix IssueGroupBy requirement to index by requirement code, as requirement can be non hashable.
- Updated Python dependency 1.7.0.

## [1.7.0] - 2025-11-06
### Changed
- Updated Python dependency 1.7.0.

## [1.6.0] - 2025-10-20
### Changed
- Update Python dependency.

## [1.5.0] - 2025-10-10
### Changed
- Update Python dependency.

## [1.4.3] - 2025-10-01
### Changed
- Update Python dependency.

## [1.4.2] - 2025-09-24
### Changed
- MaterialUsdPreviewSurfaceChecker updated for 25.08+ compatibility after the removal of Ndr.

## [1.4.1] - 2025-09-19
### Changed
- Updated documentation on features.
- Update Python dependency.

## [1.4.0] - 2025-09-15
### Added
- add_registry_requirement_callback: Expose from Python package.
### Changed
- Update Python dependency.

## [1.3.1] - 2025-09-01
### Changed
- Update Python dependency.

## [1.3.0] - 2025-08-21
### Fixed
- SubdivisionSchemeChecker: reduce scope - only validate that subdivisionScheme is defined.
### Added
- NormalsExistChecker: Checker for existence of normals.

## [1.2.1] - 2025-08-19
### Added
- Updated documentation.

## [1.2.0] - 2025-08-18
### Added
- HierarchyHasRootChecker: SimReady validator.
- RootPrimXformableChecker: SimReady validator.
- AssetOriginPositioningChecker: SimReady validator.

## [1.1.6] - 2025-08-07
### Changed
- Change OS for PyPi package

## [1.1.5] - 2025-08-04
## Changed
- Bug when enabling rule and requirements.

## [1.1.4] - 2025-07-30
### Changed
- Fix CLI import error.
- Add Requirements documentation.
- Allow rules and requirements to run in a single engine.

## [1.1.3] - 2025-07-29
### Changed
- Hyphens are not allowed in component_name.

## [1.1.2] - 2025-07-29
### Changed
- Use JFrog CLI to publish to PyPi.

## [1.1.1] - 2025-07-28
### Fixed
- AlmostExtremeExtentChecker: Missing documentation
- PointsPrecisionErrorChecker, PointsPrecisionWarningChecker: Missing documentation
- Pypi: Fixing License. Fixing script. Fixing Python version.

## [1.1.0] - 2025-07-23
### Added
- Features: An additional class to Requirements, Capabilities and Profiles
- ContainsMeshChecker: SimReady validator.
- UpAxisZChecker: SimReady validator.
- MetersPerUnit1Checker: SimReady validator.
### Changed
- DefaultPrimChecker: Add requirements information.
- ProfileRegistry: Supports versioning.

### Changed
- Update License to Apache 2

## [1.0.0] - 2025-07-16
### Changed
- OAV used in production should be marked as 1.0.0.
- Updates in documentation.

## [0.31.0] - 2025-07-15
### Fixed
- Capabilities: Support for versioned capabilities.
- Updated documentation

## [0.30.1] - 2025-07-14
### Fixed
- Deprecation messages going to logging warnings.

## [0.30.0] - 2025-07-10
### Fixed
- Documentation: Update testing documentation.
- Documentation: Update contribution guidelines.

## [0.29.1] - 2025-07-03
### Fixed
- Requirements: Expose Requirement.

## [0.29.0] - 2025-06-30
### Added
- Requirements: Expose Capability and Profile.
- Requirements: Allow to override requirements in `register_requirements`.
### Fixed
- Documentation: Performance rules were missing.
- Documentation: Update CLI.
- Requirements: Allow to hash external requirements.

## [0.28.1] - 2025-06-19
### Fixed
- Missing definitions in omni.asset_validator.core.tests (used in downstream extensions).
- Fixed conditions in new kit sdk not fixed in previous kit sdk.

## [0.28.0] - 2025-06-18
### Added
- Support for Kit 108

## [0.27.1] - 2025-05-30
### Fixed
- No updates.

## [0.27.0] - 2025-05-27
### Added
- AlmostExtremeExtentChecker: New rule.
- PointsPrecisionChecker: New rules with different severity.
### Fixed
- ComplianceChecker: Improve performance.

## [0.26.0] - 2025-05-27
### Added
- Infrastructure: ARM cloud front packages.
### Fixed
- ZeroAreaFaceChecker: Report errors as warnings.
- DefaultPrimChecker: Missing test case.

## [0.25.3] - 2025-05-13
### Fixed
- ARM builds.

## [0.25.2] - 2025-05-09
### Fixed
- ZeroAreaFaceChecker: Fix arithmetic stability error.

## [0.25.1] - 2025-05-07
### Fixed
- Hide requirements from documentation.

## [0.25.0] - 2025-05-06
### Added
- Add tags to Issue class.
### Fixed
- All rules: Use requirement field.
- AtomicAssetChecker: Add requirements.
- AtomicAssetChecker: Fix errors when run on empty stage.
- AtomicAssetChecker: Fix MDL portability warnings.
- WeldChecker: Fix error on condition.
- Physics rules: Add requirements.
- MaterialUsdPreviewSurfaceChecker: add support for sourceColorSpace, previously invalid values were permitted.
- MaterialUsdPreviewSurfaceChecker: validate connected inputs, previously they were skipped
- MaterialUsdPreviewSurfaceChecker: validate ouputs, previously they were skipped

## [0.24.0] - 2025-04-29
### Added
- AtomicAssetChecker: Added.
- StageMetadataChecker: Added requirements.
- add_registry_rule_callback: Get notifications of rule registration.
### Fixed
- Update Capabilities definitions

## [0.23.1] - 2025-04-22
### Fixed
- Added UsdPhysics rules

## [0.22.1] - 2025-04-13
### Fixed
- Fixing publishing process.

## [0.22.0] - 2025-04-11
### Added
- Support for OpenUSD 24.11 and 25.02.
### Fixed
- ValidationEngine: `enable_requirements` shown many results.
- ValidationEngine: Certain errors do not trigger progress.
- Command Line Interface: error get lost in summary.
- ManifoldChecker: Fix for non-manifold edges.

## [0.21.0] - 2025-04-01
### Added
- Add Capabilities to Command Line Interface.
- API compatibility checks.
### Fixed
- Fix crash when fixing prims on the asset validator anonymous session layer.

## [0.20.0] - 2025-03-18
### Added
- Associate requirements to Validators
- Document requirements implemented by Validators
- Link requirement to the Content Capabilities documentation
### Fixed
- Multiple fixes in documentation
- WeldChecker: Uncaught error index out of range.

## [0.19.0] - 2025-03-11
### Added
- Add content capabilities
- Add capabilities and requirements registry
- Add code and requirement attributes to Issue class
### Fixed
- GroundTruthCapabilityChecker: Updates checker to current specification

## [0.18.3] - 2025-02-27
### Fixed
- VehicleCapabilityChecker: Treat 'tank' and 'none' tokens as synonyms for vehicle steering
- UnusedMeshTopologyChecker: Supports for numpy.

## [0.18.2] - 2025-02-17
### Fixed
- Fix false positive GroundTruthCapabilityChecker validation issues when a prim's
`semantic:<instance_name>:params:semanticData` attribute is formatted as a QCode.
An example of a false positive validation message is:
"SemanticsAPI instance <instance_name> doesn't have expected semanticType value. Expected 'wikidata_qcode', found <value>."
- ManifoldChecker: Supports for numpy.
- IndexedPrimvarChecker: Supports for numpy.

## [0.18.1] - 2025-01-30
### Fixed
- Fix a bug when writing CSV file through the command line interface.
- Add missing legal headers to Python files.

## [0.18.0] - 2025-01-28
### Added
- Add numpy implementation for has empty faces.

## [0.17.0] - 2025-01-08
### Added
- Add MaterialOldMdlSchemaChecker to validate Shaders are not using the deprecated MDL schema and fix those that are.
- Add UnicodeNameChecker to warn users about ambiguous siblings and non-normalized paths
### Fixed
- Catch I/O errors on saving fixes.

## [0.16.2] - 2024-12-11
### Fixed
- Fix OmniSkelUpgradeChecker tests

## [0.16.1] - 2024-12-10
### Changed
- CSV report now includes the asset as the first column. It also adds a `Rule` column and renames `Info` to `Message`.
  Therefore, the updated CSV format is as follows:  `Asset, Rule, Message, Suggestion, Location, Fix Result`.

### Fixed
- Improve LayerSpecChecker performance

## [0.16.0] - 2024-12-03
### Added
- Add OmniSkelUpgradeChecker to validate skinning method (Available from Kit 107)

### Fixed
- Fixed ShaderImplementationSourceChecker to respect default "id" implementationSource


## [0.15.0] - 2024-11-20
### Added
- Add ShaderImplementationSourceChecker rule to verify Shader implementationSource

### Fixed
- Updating omni-docs changes to api docs
- Fix incorrect tooltips
- Add omni.kit.material.library to demo app to help resolver to find builtin materials
- Implement suite option to SimReady CLI tool
- Implement functions for JSON and CSV
- Fixed exception when trying to use non-existent "allowedTokens" metadata

## [0.14.2] - 2024-10-17
### Fixed
- Release for UI extension

## [0.14.1] - 2024-10-16
### Fixed
- Update to kit 106.2

## [0.14.0] - 2024-10-15
### Added
- Added validation of vehicle specific attribute types, allowed values and time variability.
- Add fixer for UnusedMeshTopologyChecker.
- KindChecker autofix.
- Identifiers contains a reference to the variant selection.

### Fixed
- Formatting docstrings.
- Fix a bug in KindChecker.
- Suggestion bug for representation of partial functions.

## [0.13.3] - 2024-09-10
### Fixed
- Issue and Fix accept any first class OpenUSD schema.
- Change CLI so no fixes are default.
- TextureCheckers prevent validating material templates.
- GroundTruthValidator: reports missing semantics more than once for same prim
- VehicleCapabilityChecker: Use wheel component transform to determine wheel alignment.

## [0.13.2] - 2024-08-29
### Fixed
- Support multiple OpenUSD stock flavors.
- Include simready packages.
- Remove restrictions on preview surface.
- Texture checker ignore ies files on lights.
- Setup default rules for simready validator cli.
- Remove material binding api requirements when query geomsubsets.
- Build and publish simready package.
- Make omni.asset_validator.simready module executable.

## [0.13.1] - 2024-08-20
### Fixed
- Compute Extents fix fail.
- Add checks for component rules to detect Xformable default prim
- Use normalize_url in identifiers.
- Add `--init-rules`, `--disable-rules`, `--disable-category` to common CLI.
- VehicleCapabilityChecker: Update vehicle axis alignment validator
- VehicleCapabilityChecker: Ignore tasks and guides when checking semantic labels

## [0.13.0] - 2024-08-15
### Added
- Common registry between omni.asset_validator and omni.asset_validator.core
- Version can now be accessed in the module and CLI.
### Fixed
- Fix an error when nonvisual token array has only one invalid value
- Filter more int types to skip validation
- Fix bug in command line interfacec
- Fix diagnostics delegate release
- Fix disable rules
- Fix MaterialPathChecker bug when fixing.

## [0.12.0] - 2024-08-02
### Added
- Environment domain logic checker
- Traffic light validator
### Fixed
- Allow UPS shader without emissive opacity
- Use new names and types for non-visual sensors
- Move Material checkers to common `omni.asset_validator`
- Add __repr__ to IssuePredicate
- `omni.asset_validator` fix licenses
- Enable local extensions for validate.bat/validate.sh

## [0.11.8] - 2024-07-23
### Fixed
- Rename AVSimComponent category to Omni:SimReady
- Fix Layer Checker
- Check all material bindings regardless if material binding api is applied
- Progress shows 100 when checkers are still running
- Add most of the rules for the Kit less implementation
- Avoid calling UsdUtils.ComputeAllDependencies twice
- IsAnIssue representation
- Enable multiple arguments for IssuePredicates AND and OR

## [0.11.7] - 2024-07-17
### Added
- Scripts to use asset validator command line interface with Omniverse.
- Setup poetry for dependency management

## [0.11.6] - 2024-07-08
### Fixed
- ValidateTopologyChecker: Error when no points attribute on a mesh
- Update Kit 106
- `check_package` is skipped if the input stage is usdz format
- Remove `attrs` python dependency

### Added
- NonVisualSensorChecker for avsim
- Implement one or more validators to ensure that layer content is internally consistent
- Add GroundTruthCapabilityChecker for avsim validators
- Kit-less asset validator with basic rules implemented.

## [0.11.5] - 2024-05-29
### Fixed
- OmniMaterialUsdPreviewSurfaceChecker failures are divided into multiple messages.
- Add checks for info:mdl:sourceAsset property for OmniMaterialPathChecker.

## [0.11.4] - 2024-05-13
### Added
- Added statistics per validation execution.
### Fixed
- Variant option was missing from command line arguments.
- Improve progress reporting for jobs that are processed slower.

## [0.11.3] - 2024-04-24
### Fixed
- Update for UI 0.11.3

## [0.11.1] - 2024-04-09
### Fixed
- IndexedPrimvarChecker: Do not report non-indexed simple array types.
- IndexedPrimvarChecker: Do not check usdSkel related primvars.
- OmniDefaultPrimChecker: Allow Scope type to be default prim.
- UsdAsciiPerformanceChecker: Skip if layer is anonymous.
- ValidationEngine: Added disableRule method.

## [0.11.0] - 2024-02-27
### Added
- OmniMaterialOutOfScopeChecker: Finds material bindings which target materials that are outside the payloads' hierarchy.
- MissingReferenceChecker: Missing reference checker now returns location of the problem.
### Fixed
- Performance improvements:
  - Logging: No logging side effects during validation.
  - Stage immutability: No rendering/UI side effects during validation.
  - Variants: Option to enable/disable checking all variants.
- WeldChecker: Change error level and message.

## [0.10.3] - 2024-02-15
### Fixed
- Tutorial content reviewed and tested to avoid incongruent output. Bugs fixed.
- Extents checker comparison using GfIsClose.
- Performance: Rules evaluating only assets (i.e. `CheckLayers`) do not evaluate prims.

## [0.10.2] - 2024-01-30
### Fixed
- NormalMapTextureChecker fails to compute a value from a connection to a material file input.
- Progress indicator implementation.
- Add a summary per rule and per severity in Command Line.


## [0.10.1] - 2023-12-15
### Fixed
- ZeroAreaFaceChecker: Fixed py37 source compatibility

## [0.10.0] - 2023-12-14
### Added
- ManifoldChecker: Counts the number of non-manifold edges and vertices.
- IndexedPrimvarChecker: Check optimization of indices for primvars.
- UnusedMeshTopologyChecker: Points which are not referenced by the indices can be removed.
- ZeroAreaFaceChecker: Faces with zero area can be removed.
- WeldChecker:  If attributes contain equal values they can be unified and the indices adjusted accordingly.
- ValidateTopologyChecker: Validate the topology of a mesh on all time samples.
- UnusedPrimvarChecker: Values which are not referenced by the indices in a primvar can be removed.
### Fixed
- SubdivisionSchemeChecker: remove "Normals should be defined when subdivision scheme is none".

## [0.9.5] - 2023-12-05
### Fixed
- Move OmniMaterialUsdPreviewSurfaceChecker for older USD releases.

## [0.9.4] - 2023-12-04
### Fixed
- Fix for Python 3.7 compatibility.
- Catch errors on class initialization.

## [0.9.3] - 2023-11-22
### Fixed
- Update kit-sdk, repo tools and packman.

## [0.9.2] - 2023-11-14
### Fixed
- Performance and stability issues with compliance checker async methods.

## [0.9.1] - 2023-11-01
### Fixed
- Fixed bug in `omni.asset_validator.core.ValidationRulesRegistry.deregisterRule` (OM-113568).
- Updated to latest Kit SDK 105.1

## [0.9.0] - 2023-10-12
### Added
- SubdivisionSchemeChecker: Check whether subdivision attribute is congruent with mesh attributes.
### Fixed
- Compliance checker, check and check_async methods added.
- Change GetWarnings, GetErrors, GetFailedChecks for GetIssues
- Issues and suggestions support Primvars.

## [0.8.1] - 2023-08-18
### Fixed
- Update for UI 0.8.1

## [0.8.0] - 2023-08-08
### Fixed
- SkelBindingAPIAppliedChecker added: Rule ensuring UsdSkel.BindingAPI is applied.
- Fix Location empty for anonymous layers.
- Type Checker should ignore /Render* prims.

## [0.7.6] - 2023-08-02
### Fixed
- Update Kit SDK.

## [0.7.5] - 2023-08-02
### Fixed
- Publishing process.

## [0.7.1] - 2023-08-01
### Fixed
- Crash when using OmniMaterialUsdPreviewSurfaceChecker
- PrimEncapsulationChecker: Add problem location.
- OmniDefaultPrimChecker: Change descriptions.
- NormalMapTextureChecker: Add problem location.

## [0.7.0] - 2023-07-13
### Added
- OmniMaterialUsdPreviewSurfaceChecker added: Rule ensuring that UsdShadeShader prims conform to the UsdPreviewSurface specification.

## [0.6.2] - 2023-06-20
### Fixed
- Additional to filter issues by predicates, it is possible to group issues by different criteria. Updated documentation.

## [0.6.1] - 2023-05-25
### Added
- CLI: Added parameters for fixing issues and filter by predicate. Added documentation.

## [0.6.0] - 2023-05-19
### Added
- ExtentsChecker: Implements auto fixing.
- OmniDefaultPrimChecker: Filters out specific prims.
- Usd:Schema Rules: Auto fixing is scoped to the location of the issue.
### Fixed
- Regression in anonymous layers, test cases added.
- Asset Validation blocks when dealing with more than 100 files in async methods.

## [0.5.1] - 2023-05-10
### Fixed
- Fixing publishing of extension.

## [0.5.0] - 2023-05-10
### Fixed
- Restoring prim may lead to an uncaught error.
- GetDescription takes doc from class.
- Auto fixing, Rules can select which layers the fix should be applied first.
- Update documentation to reflect latest changes.
- Update to Kit 105

## [0.4.0] - 2023-04-27
### Added
- Auto fixing, adding the ability to fix a specific layer via API.
- Add test for missing types.

## [0.3.3] - 2023-03-28
### Added
- Enable pyCoverage.
- Add validation check + fix for dangling material bindings.
### Fixed
- Add missing lines to Tutorial scripts. Tutorial script samples must be self-sufficient.

## [0.3.2] - 2023-03-09
### Fixed
- Adjusted test data for new validation Warnings issued by USD 22.11

## [0.3.1] - 2023-03-07
### Fixed
- combine_urls changed behavior, use pathlib.Path instead.

## [0.3.0] - 2023-02-07
### Added
- Added a Rule to detect ASCII USD layers containing large array data.
- Added a new "Usd:Performance" category for optimization based rules.

## [0.2.4] - 2023-01-31
### Fixed
- Updated to build with Kit 104.2 by default
- Fixed unittests when running with Kit 104.2

## [0.2.3] - 2023-01-26
### Added
- Asset Validation Tutorial and updated documentation.

## [0.2.2] - 2023-01-23
### Added
- UsdGeomSubset and MaterialBindingAPI validators
- For Python 3.8 and newer add CARB_APP_PATH with os.add_dll_directory()

## [0.2.1] - 2022-11-21
### Fixed
- String representation of `Issue`

## [0.2.0] - 2022-10-28
### Added
- Rules can include `at` to describe the layer/prim/attribute that has been flagged for a particular Issue
- Rules can can include `suggestion` callables to fix layers/prims/attributes for one or more Issues
- Added Suggestions to fix non-relative MDL pathing issues
- Added Suggestions to fix some OmniDefaultPrimChecker issues
- Added a rule for UsdLux schema changes, with a Suggestion to create `inputs:` prefixed attributes matching all known UsdLux attributes.
  - For backwards compatibility with current/older USD libraries, the non-prefixed attributes will be maintained.
  - Note Assets already containing prefixed attributes (eg created in a modern USD application) will not be flagged or modified by this rule.
### Fixed
- Improved asynchronous logic to avoid blocking the primary application (eg Create) & to fix crashes on some larger stages
- Fixed KindChecker logic, which was previously flagging false issues with assemblies

## [0.1.2] - 2022-09-15
### Fixed
- Fixed documentation build & publish.

## [0.1.1] - 2022-09-14
### Fixed
- Updated extension registry details and documentation.

## [0.1.0] - 2022-09-13
### Added
- `ValidationEngine` runs a set of rules on a given USD layer file, folder/container URI, or live `Usd.Stage`
   - `Results` captures any `Issues` for post-processing
- `ValidationRulesRegistry` enables new rules to be registered with the engine
- `BaseRuleChecker` defines an interface to validate a `Usd.Stage`
    - Derived classes may be registered with the `ValidationEngine` via the `ValidationRulesRegistry`
- `IssueFixer` automatically fixes `Issues` where possible, using suggestions provided by the `BaseRuleChecker` classes.
- `ValidationRuleTestCase` (in the `tests` submodule) simplifies testing of individual rules
- Python script for initiating commandline validation runs
