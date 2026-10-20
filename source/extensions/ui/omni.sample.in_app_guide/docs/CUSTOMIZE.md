# Customizing the Guide

The guide system is built on a flexible data model that can be extended to support additional features.

## Omniverse Kit SDK Integration

First of all, it's important to note what Omniverse Kit SDK components the In-App Guide leverages:

- **omni.ui**: Core UI framework for building the guide interface and overlay
- **omni.kit.actions.core**: Action system for registering guide-related commands
- **omni.kit.menu.utils**: Menu integration for accessing the guide
- **omni.ui_query**: UI element querying and interaction
- **omni.kit.ui_test**: UI utilities for simulating user interactions
- **carb**: Core framework for events and input handling

## Levels of Complexity

Developers are encouraged play through *all the steps* in the sample and look at the [JSON data](../data/guide_data_latest.json)
that drives the functionality:

- A few steps merely describes a window.
- More complex steps locates a widget within a window and clicks on it.
- The more advanced steps activates a window, clicks a button, expands a collapsible frame, and finally scrolls to a widget within the frame.

It may take a combination of actions to reveal the UI element being described.

## Extending the Data Model

1. **Adding New Step Types**:
   - Create a new class inheriting from `_GuideStep` in `model.py`; for example, a `USDPrimStep` could be added for describing some geometry in a USD Stage.
   - Add handling in `GuideModel._load_data` to support the new type
   - Update the logic in `GuideStepWindow._update_ui` in `step_ui.py` for positioning the window in a certain way. You may want to add new function similar to `GuideStepWindow._position_for_widget`, for example: `GuideStepWindow._position_for_usd_prim`.

```python
# GuideStepWindow._update_ui
if guide_step.ui_type == 'window':
   asyncio.ensure_future(self._position_for_window(guide_step.target_ui_path))
   return
if guide_step.ui_type == 'widget':
   asyncio.ensure_future(self._position_for_widget(guide_step.parent_window_ui_path, guide_step.target_ui_path, guide_step.reveal_actions))
   return
# Added support for usd_prim
if guide_step.ui_type == 'usd_prim':
   asyncio.ensure_future(self.position_for_usd_prim(guide_step.parent_window_ui_path, guide_step.target_ui_path, guide_step.reveal_actions))
   return
```

   - Update the logic in `OverlayWindow._update_ui` in `overlay_ui.py` for highlighting the USD Prim, perhaps using a [custom manipulator](https://docs.omniverse.nvidia.com/kit/docs/omni.ui.scene/latest/Manipulator.html).

```python
# OverlayWindow._update_ui
...
if self.current_step.ui_type == 'window':
    ...
    return
if self.current_step.ui_type == 'widget':
    ...
    return
# Added support for usd_prim
if self.current_step.ui_type == 'usd_prim':
    # New implementation here...
```

2. **Extending the JSON Structure for step types**:

Here we add a new `ui_type` but new properties can be added as well - just remember to support them in the Model.

   ```json
   {
     "steps": [
       {
         "ui_type": "usd_prim", // Added type
         "target_ui_path": "/World/Cylinder",
         "title": "Cylinder",
         "description": "This is a cylinder USD Prim",
         "link": {
           "label": "Learn More",
           "url": "https://example.com"
         }
       }
     ]
   }
   ```

3. **Adding New Action Types**:
   - Create a new class inheriting from `_RevealAction` in `model.py`; for example, a `USDPrimAction` could be added for zooming in on the USD Prim with the camera in the RTX viewport.
   - Support the new action class in the new `USDPrimStep.__init__` class in the way that `WidgetGuideStep.__init__` parse for actions.
   - Update the logic in `GuideStepWindow._position_for_usd_prim` to support the `USDPrimAction` in the way that `GuideStepWindow._position_for_widget` supports actions.

4. **Extending the JSON Structure for action types**:

Here we add a new `action_type`:

   ```json
   {
     "steps": [
       {
         "ui_type": "usd_prim",
         "target_ui_path": "/World/Cylinder",
         "title": "Cylinder",
         "description": "This is a cylinder USD Prim",
         "link": {
           "label": "Learn More",
           "url": "https://example.com"
         },
         "reveal_actions": [
            {
                "action_type": "camera_zoom", // Added type
                "prim_path": "/World/Cylinder"
            }
        ]
       }
     ]
   }
   ```

To summarize, the model's flexibility allows developers to:
- Add new types of UI interactions
- Create custom step layouts
- Implement specialized behaviors
- Extend the data structure without modifying core functionality

## How to author UI for use with an In-App Guide

As you can see in this sample, `omni.ui_query.OmniUIQuery` is used to finding widgets using paths.
Looking at the supported [syntax](https://docs.omniverse.nvidia.com/kit/docs/kit-sdk/latest/source/extensions/omni.ui_query/docs/TUTORIAL.html) you can see how it will be easier to maintain an In-App Guide
if UI elements are named consistently from one version to the next:

```python
my_window = ui.Window("My Window")
with my_window.frame:
   with ui.VStack():
      ui.Button("Click Me", name="My Button")
```

The above UI can be queried using for example:

```python
widget = OmniUIQuery.find_widget("My Window//Frame/**/Button[*].name=='My Button'")
```
**NOTE:** The sample does provide two sets of JSON data [guide_data_106.5.json](./omni.sample.in_app_guide/data/guide_data_106.5.json) and [guide_data_107.0.json)](./omni.sample.in_app_guide/data/guide_data_107.0.json)
because there was an API breaking version change where additional UI elements were added in `107.0`. See `InAppGuideExtension._get_model` for checking Kit SDK version.

### Menu Items

For finding Menu Items or SubMenu Items there is a different approach to using `omni.ui_query.OmniUIQuery`. See the code below on how to find MenuItems

``` python
from omni.ui_query import OmniUIQuery
import omni.ui

# Grab the Menu Bar and its Menu Item
menu_bar = OmniUIQuery.find_menu_item("Create")
create_widget = None
for widget in OmniUIQuery.find_widgets("*", [menu_bar]):
	if isinstance(widget, omni.ui.Menu) or isinstance(widget, omni.ui.MenuItem):
		if widget.text == "Create":
         # Store Menu Widget
			create_widget = widget
			print(f"Found {widget.text}")

         # Going through all SubMenu items in the current Widget i.e. Create > Shapes or Create > Xform
			menu_item = [menu_item for menu_item in OmniUIQuery.find_widgets("**", [widget]) if isinstance(menu_item, omni.ui.MenuItem)]
			for item in menu_item:
				print(item.text)  # Submenu Item description
```

## Resources for creating custom UI behavior

- [omni.ui](https://docs.omniverse.nvidia.com/kit/docs/omni.ui/latest/omni.ui.html) is the Kit UI framework. Use this to customize the In-App Guide UI and to understand how to work with the application UI.
- [omni.ui_query](https://docs.omniverse.nvidia.com/kit/docs/kit-sdk/latest/source/extensions/omni.ui_query/docs/index.html) provides API to make `omni.ui` queries to find widgets using paths.
- [omni.kit.ui_test](https://docs.omniverse.nvidia.com/kit/docs/kit-sdk/latest/source/extensions/omni.kit.ui_test/docs/index.html) can be used for simulating user interactions.
- [omni.ui.scene](https://docs.omniverse.nvidia.com/kit/docs/omni.ui.scene/latest/Overview.html) is a framework for UI inside the RTX viewport rendering a USD Stage.

# Governing Terms
The software and materials are governed by the [NVIDIA Software License Agreement](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/) and the [Product-Specific Terms for NVIDIA Omniverse](https://www.nvidia.com/en-us/agreements/enterprise-software/product-specific-terms-for-omniverse/).

# Contributing

We provide this source code as-is and are currently not accepting outside contributions.