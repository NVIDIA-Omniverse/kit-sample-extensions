import omni.asset_validator.core
from pxr import Usd


class MyRule(omni.asset_validator.core.BaseRuleChecker):
    def Callable(self, stage: Usd.Stage, location: Usd.Prim) -> None:
        raise NotImplementedError()

    def CheckPrim(self, prim: Usd.Prim) -> None:
        if prim.GetPath() == "/Hello/World":
            self._AddFailedCheck(
                message="Goodbye!",
                at=prim,
                suggestion=omni.asset_validator.core.Suggestion(
                    message="Avoids saying goodbye!",
                    callable=self.Callable,
                ),
            )


stage = Usd.Stage.CreateInMemory("tutorial.usda")
stage.DefinePrim("/Hello/World", "Xform")

engine = omni.asset_validator.core.ValidationEngine(init_rules=False)
engine.enable_rule(MyRule)
result = engine.validate(stage)

fixer = omni.asset_validator.core.IssueFixer(asset=stage)
result = fixer.fix(result.issues())
print(result)
