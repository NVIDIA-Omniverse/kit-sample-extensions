import omni.asset_validator.core
from pxr import Usd


@omni.asset_validator.core.registerRule("MyCategory")
class MyRule(omni.asset_validator.core.BaseRuleChecker):
    def CheckPrim(self, prim: Usd.Prim) -> None:
        pass


for rule in omni.asset_validator.core.ValidationRulesRegistry.rules(category="MyCategory"):
    print(rule.__name__)
