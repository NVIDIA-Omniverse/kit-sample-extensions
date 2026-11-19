# 3d Text [omni.kit.text3d]

### Description

This extension provides UI to place a 3d text Prim, along with a set of default letter meshes. It adds a Text entry to the Create menu. This menu will insert an Xform Prim in the stage which contains a PointInstancer along with letter meshes to display the indicated text on the stage.

### Details

The generated Prim contains an OmniGraph that manages the instancer based on the value of /World/Text/ActionGraph/generate_3d_text.inputs:text. This graph runs all the time.

### Performance

Note that if there are many Text elements on the stage it may be worth copying the text_generator.usda asset out of this extension's data folder and referencing it multiple times instead of creating copies via the menu. This will reduce the total number of Prims on the stage.

### Settings

/exts/omni.kit.text3d/menus/enable can be used to disable the Create/Text menu from being added.
