import omni.asset_validator.core
from pxr import Sdf, Usd, UsdGeom

layer_stage = Usd.Stage.CreateInMemory("layer.usda")
UsdGeom.Sphere.Define(layer_stage, "/Hello/World")

stage = Usd.Stage.CreateInMemory("tutorial.usda")
stage.GetRootLayer().subLayerPaths.append(layer_stage.GetRootLayer().identifier)
sphere = UsdGeom.Sphere.Define(stage, "/Hello/World")
sphere.AddTranslateOp().Set((-250, 0, 0))

prim = stage.GetPrimAtPath("/Hello/World")

# We create the data model for the issue
def Callable(stage: Usd.Stage, location: Usd.Prim) -> None:
    raise NotImplementedError()


issue = omni.asset_validator.core.Issue(
    message="Goodbye!",
    at=prim,
    severity=omni.asset_validator.core.IssueSeverity.FAILURE,
    suggestion=omni.asset_validator.core.Suggestion(
        message="Avoids saying goodbye!",
        callable=Callable,
        at=[Sdf.Layer.FindOrOpen(layer_stage.GetRootLayer().identifier)],
    ),
)

# Inspect the fixing points for the suggestion
for fix_at in issue.all_fix_sites:
    layer_id = fix_at.layer_id
    path = fix_at.path
    print(layer_id, path)
