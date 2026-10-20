import omni.asset_validator.core
from pxr import Usd, UsdGeom


class MyRule(omni.asset_validator.core.BaseRuleChecker):
    def CheckPrim(self, prim: Usd.Prim) -> None:
        if prim.GetPath() == "/Hello/World":
            self._AddFailedCheck(
                message="Goodbye!",
                at=prim,
            )


stage = Usd.Stage.CreateInMemory("tutorial.usda")
UsdGeom.Xform.Define(stage, "/Hello/World")

engine = omni.asset_validator.core.ValidationEngine(init_rules=False)
engine.enable_rule(MyRule)
print(engine.validate(stage))
