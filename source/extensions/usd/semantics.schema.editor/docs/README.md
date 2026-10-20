# Semantics Schema Editor

This is a simple python Kit extension to quickly edit semantics data on USD prims.

## Automatic tag application on entire stage

1. Enter a comma separated list of prim types that are allowed to be labeled.
2. Enter a comma separated list of names to match and apply the matching class type to. e.g. If "table" is in the list, all objects that match the allowed prim types and contain "table" in the name will have the semantic tag with the the "class" type and "table" data automatically applied.
3. Click the "Generate Labels" button.

## Manual tag application

1. Select one or more objects in the stage browser. The object name and semantic data (if any) will be populated in the UI.

### Add a new tag

1. Enter the type and data values at the top of the frame.
2. Click "Add New Value" to add the new type and data to the corresponding selected object.
3. Or click on the "Add Entry On All Selected Prims" to add the new type and data to each selected object.

### Update existing tags

1. Modify the type and data fields of the selected prims and click the "Update" button.

### Removing tags

NOTE: USD does not provide a way to remove schemas once they are added to prims because USD is supposed to be additive. This means that removing a Semantic tag will clear the type and data fields and hide it from the UI, but the instance of the tag still exists on the object.

1. Click the 'X' button for the type and data pair that should be cleared.