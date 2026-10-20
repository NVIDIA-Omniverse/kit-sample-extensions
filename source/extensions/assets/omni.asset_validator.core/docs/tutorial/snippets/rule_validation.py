import omni.asset_validator.core
from pxr import Usd, UsdGeom

stage = Usd.Stage.CreateInMemory("tutorial.usda")
UsdGeom.Xform.Define(stage, "/World")

engine = omni.asset_validator.core.ValidationEngine(init_rules=False)
engine.enable_rule(omni.asset_validator.core.OmniDefaultPrimChecker)
print(engine.validate(stage))
