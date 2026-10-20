import omni.asset_validator.core
from pxr import Usd, UsdGeom

stage = Usd.Stage.CreateInMemory("tutorial.usda")
UsdGeom.Xform.Define(stage, "/World")

engine = omni.asset_validator.core.ValidationEngine()
print(engine.validate(stage))
