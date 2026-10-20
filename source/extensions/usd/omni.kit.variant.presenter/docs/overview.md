# Variant Presenter

The Variant Presenter provides a menu to view and manage variants and variant groups. There are two display modes that can be accessed from the top of the panel, Prims and Groups.

Once enabled, the Variant Presenter can be accessed by selecting **Tools > Variants > Variant Presenter**.

## Prims Tab

The Prims Tab of the Variant Presenter displays prims that utilize variant sets, allowing quick access to the variant properties of those prims.

![](images/ext_variant_presenter_prims_tab.png)

| Feature | Result |
|---|---|
| View All | Displays a list all prims with variant sets in the scene. |
| View Selected | Displays a list of variant sets for all currently selected prims. |
| Search | Filters the list to include only prims and variant sets that match or contain the provided string. |
| Set Current Variant | The current variant can be set for a given variant set using the combo box. |
| Lock Variant | Disables/Enables ability to set the current variant from the Variant Presenter. |
| Edit Variant ![](images/ext_variant_presenter_edit_variant.png) | Opens the Variant Editor to edit Variant Set in the current authoring layer. |
| Locate File | Navigates to the source file in the Content Browser. This option will be available as a sub-option of "Edit Variant" if the prim is a reference or payload. |
| Refresh | Manually refreshes the list. |

Right-clicking on a prim or variant set in the list will provide the following options:

| Option | Result |
|---|---|
| Edit Variant | Opens the Variant Editor to edit Variant Set in the current authoring layer. |
| Select Prim In Stage | Selects the given prim in the stage or the parent prim of the given variant set. |

## Groups Tab

The Groups Tab of the Variant Presenter displays variant sets organized by customizable groups. Variant sets can selected and moved between groups as desired for ease of access.

![](images/ext_variant_presenter_groups_tab.png)

| Feature | Result |
|---|---|
| Add Group | Creates a new group in the list and a corresponding USD collection. |
| Remove All | Deletes all groups and their corresponding USD collection and returns to a flat list of variant sets. |
| Search | Filters the list to include only groups and variant sets that match or contain the provided string. |
| Set Current Variant | The current variant can be set for a given variant set using the combo box. |
| Lock Variant | Disables/Enables ability to set the current variant from the Variant Presenter. |
| Remove Group | When hovered over, a group will display a red 'X' on the right side that deletes the group and corresponding USD collection if pressed. |
| Rename Group | Double-clicking on a group will provide a text field to rename the group. |
| Remove Variant from Group | When hovered over, a variant set will display a grey 'X' on the right side that will remove that variant set from its current group and place it into "Ungrouped Variants." |
| Refresh | Manually refreshes the list. |

> **Note:** Any variant sets contained within a group that is deleted will be moved to "Ungrouped Variants."

### Drag and Drop

- Variant sets can be moved into, out of, and between groups by dragging and dropping them onto the desired group.
- Multiple variant sets can be selected and moved simultaneously.

Right-clicking on a variant set will provide the following options:

| Option | Result |
|---|---|
| Edit Variant | Opens the Variant Editor to edit Variant Set in the current authoring layer. |
| Select Prim In Stage | Selects the parent prim of the given variant set. |
| Remove From Group | Removes variant set from current group and places it into "Ungrouped Variants." |

Additionally, right-clicking on a group or variant set will provide the following options:

| Option | Result |
|---|---|
| Create Group | Creates a new group in the list and a corresponding USD collection. |
| Delete Group | Deletes the group and returns any child variant sets to "Ungrouped Variants." |
| Rename Group | Pops up a menu to rename the group. |

## Related Variant Features

- Variant Editor
- Variants section of the Property Panel
- USD Python Snippets for Variant sets

## Variant OmniGraph Nodes

- HasVariantSet
- GetVariantSetNames
- GetVariantNames
- GetVariantSelection
- SetVariantSelection
- ClearVariantSelection

## Features Supported

- Works with all prim types, including instanceable, referenced, and payloads.
- Supports undo and redo of operations (see limitations below.)
- Locked variants can be saved to the stage and retained between sessions.

## Limitations

- Undo and redo operations on actions that change a variant set's group membership do not trigger a stage event, so the list will not automatically reload and must be manually refreshed.
- Since the order of variant set items in each group is managed by the USD collection, variant sets cannot be freely reordered. The most recently added item will always be placed at the bottom of the list.
- Currently, groups cannot be added to other groups.
- In large scenes, USD Collections operations (adding, removing, renaming, etc) will cause a momentary hitch in performance.
