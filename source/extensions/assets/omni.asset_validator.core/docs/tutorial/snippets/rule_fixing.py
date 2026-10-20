import omni.asset_validator.core
from pxr import Usd, UsdGeom

# Create a stage
stage = Usd.Stage.CreateInMemory("tutorial.usda")
UsdGeom.Xform.Define(stage, "/World")

# Detect issues
engine = omni.asset_validator.core.ValidationEngine(init_rules=False)
engine.enable_rule(omni.asset_validator.core.OmniDefaultPrimChecker)
result = engine.validate(stage)

# Fix issues
fixer = omni.asset_validator.core.IssueFixer(asset=stage)
fixer.fix(result.issues())
