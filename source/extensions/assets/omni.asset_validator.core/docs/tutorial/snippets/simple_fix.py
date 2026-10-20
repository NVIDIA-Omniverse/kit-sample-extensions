import omni.asset_validator.core
from pxr import Usd, UsdGeom

stage = Usd.Stage.CreateInMemory("tutorial.usda")
UsdGeom.Xform.Define(stage, "/World")

fixer = omni.asset_validator.core.IssueFixer(asset=stage)
fixer.fix([])
