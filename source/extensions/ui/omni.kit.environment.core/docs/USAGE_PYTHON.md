# Usage Examples

## Create SunStudy Player UI with Clock and Controls

```python
import omni.ui as ui
from omni.kit.environment.core import get_sunstudy_player, Clock, PlayButton, PlayRateButton, PlayLoopButton, SunstudyTimeSlider, CityComboBox

sunstudy_player = get_sunstudy_player()

# Create a window for the sun study controls
window = ui.Window("Sun Study Player", width=400, height=300)

with window.frame:
    with ui.VStack(spacing=10, height=0):
        with ui.HStack(spacing=10):
            ui.Spacer(width=20)
            ui.Label("City:", width=0)
            CityComboBox()
            ui.Spacer(width=20)
        time_slider = SunstudyTimeSlider()
        ui.Spacer(height=2)
        with ui.ZStack():
            with ui.HStack(height=20):
                ui.Spacer(width=24)
                PlayRateButton(width=16, height=16, image_width=14, image_height=14)
                PlayLoopButton(width=16, height=16, image_width=14, image_height=14)
                ui.Spacer()

            with ui.HStack(height=0):
                ui.Spacer()
                PlayButton(sunstudy_player, width=16, height=16, image_width=14, image_height=14)
                ui.Spacer()
        with ui.HStack(spacing=10):
            ui.Spacer(width=20)
            ui.Label("Time of Day:")
            Clock(time_slider.current_time_model)
            ui.Spacer(width=20)

```
### Screenshot:
```{image} ../../../../source/extensions/ui/omni.kit.environment.core/data/docs_images/sunstudy_player.png
---
align: center
---
```

---

## Create and Manage USD Property Models

```python
import omni.ui as ui
from omni.kit.environment.core import UsdModelBuilder, PropertyValueModel, SettingModel
from pxr import Sdf
import omni.usd

# Create USD model builder
usd_builder = UsdModelBuilder()

# Get current stage
stage = omni.usd.get_context().get_stage()
usd_builder.start(stage)

# Create property value models for environment properties
latitude_model = usd_builder.create_property_value_model(
    "/Environment.latitude",
    value_type=Sdf.ValueTypeNames.Float,
    default=51.426,
    min=-90.0,
    max=90.0,
    default_prim_type="Xform"
)

longitude_model = usd_builder.create_property_value_model(
    "/Environment.longitude",
    value_type=Sdf.ValueTypeNames.Float,
    default=-0.985,
    min=-180.0,
    max=180.0,
    default_prim_type="Xform"
)

# Create setting models for application settings
ground_enable_model = SettingModel("/persistent/exts/omni.kit.environment.core/rtx/ground/enable")

# Use the models with UI
window = ui.Window("Environment Settings", width=300, height=200)
with window.frame:
    with ui.VStack(spacing=5, height=0):
        with ui.HStack(spacing=5):
            ui.Label("Latitude:")
            ui.FloatDrag(latitude_model, min=-90, max=90)
        with ui.HStack(spacing=5):
            ui.Label("Longitude:")
            ui.FloatDrag(longitude_model, min=-180, max=180)
        with ui.HStack(spacing=5):
            ui.Label("Enable Ground When Stage Opened:")
            ui.CheckBox(ground_enable_model)

# Clean up when done
usd_builder.destroy()
```
### Screenshot:
```{image} ../../../../source/extensions/ui/omni.kit.environment.core/data/docs_images/create_and_manage_usd_property_models.png
---
align: center
---
```

---

## Import Environment

```python
import asyncio
import omni.client
from omni.kit.environment.core import import_environment, SkyType, SkyHelper
import omni.usd

# Create a new stage first to ensure we have a valid USD context
usd_context = omni.usd.get_context()

async def import_environment_example():
    await usd_context.new_stage_async()
    stage = usd_context.get_stage()

    sky_url = "omniverse://localhost/Users/test/sky.usd"

    # Detect environment file type only for valid file paths
    result, entry = omni.client.stat(sky_url)
    if result == omni.client.Result.OK:
        file_type = SkyHelper.get_env_file_type(sky_url)
        if file_type == SkyType.DYNAMIC:
            print("This is a dynamic sky file")
        elif file_type == SkyType.HDRI:
            print("This is an HDRI file")

        # Import the environment
        import_environment(file_type, sky_url)
    else:
        print("File does not exist, cannot detect type")

asyncio.ensure_future(import_environment_example())
```
---

## Manage Ground with GroundHelper

```python
from omni.kit.environment.core import GroundHelper, GroundType, ENVIRONMENT_PRIM_ROOT
import omni.usd
import omni.kit.commands
import asyncio

async def setup_ground_example():
    # Ensure we have a valid USD stage
    usd_context = omni.usd.get_context()

    # Create a new stage asynchronously
    await usd_context.new_stage_async()
    stage = usd_context.get_stage()

    # Create environment root prim if it doesn't exist
    if stage and not stage.GetPrimAtPath(ENVIRONMENT_PRIM_ROOT):
        stage.DefinePrim(ENVIRONMENT_PRIM_ROOT, "Xform")

    # Create ground helper instance
    ground_helper = GroundHelper()

    # Find existing ground in the scene
    ground_prim = ground_helper.find_ground()
    if ground_prim:
        print(f"Found ground: {ground_prim.GetPath()}")
    else:
        print("No ground found")

    # Set the ground prim
    ground_helper.ground_prim = ground_prim

    # Get current ground material
    ground_material = ground_helper.ground_material
    if ground_material:
        print(f"Current ground material: {ground_material}")

    # Only update ground material if we have a valid ground prim and stage
    if ground_prim and stage:
        # Create a simple material for demonstration
        material_path = "/Environment/Looks/NewGroundMaterial"

        # Create a basic material first
        omni.kit.commands.execute(
            "CreateMdlMaterialPrimCommand",
            mtl_url="OmniPBR.mdl",
            mtl_name="NewGroundMaterial",
            mtl_path=material_path,
        )

        # Update ground material
        ground_helper.update_ground_material(material_path)

    # Clean up when done
    ground_helper.destroy()

# Run the async function
asyncio.ensure_future(setup_ground_example())
```
