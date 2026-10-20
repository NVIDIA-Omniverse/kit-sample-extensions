
# Public API for module usdex.core:

## Classes

- class ValidChildNameCache(_usdex_core.ValidChildNameCache)
  - def __init__(self)

## Functions

- def deprecated(version: str, message: str)
- def createStage(identifier: str, defaultPrimName: str, upAxis: str, linearUnits: float, authoringMetadata: str, fileFormatArgs: Optional[dict] = None, massUnits: Optional[float] = None) -> Optional[Usd.Stage]
- def createAssetPayload(stage: Usd.Stage, format: str = 'usda', fileFormatArgs: Optional[dict] = None) -> Optional[Usd.Stage]
- def addAssetContent(stage: Usd.Stage, name: str, format: str = 'usda', fileFormatArgs: Optional[dict] = None, prependLayer: bool = True, createScope: bool = True) -> Optional[Usd.Stage]
- def addAssetLibrary(stage: Usd.Stage, name: str, format: str = 'usdc', fileFormatArgs: Optional[dict] = None) -> Optional[Usd.Stage]

# Public API for module usdex.rtx:

No public API
