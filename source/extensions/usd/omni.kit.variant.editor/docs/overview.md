# Variant Editor

The Variant Editor provides an interface for adding, removing, and modifying variants in USD.

Once enabled, the Variant Editor can be accessed the following ways:

- Selecting **Tools > Variants > Variant Editor**.
- The "Edit Variant" button in the Variants section of the Property Panel.
- The "Edit Variant" button in the Variant Presenter.
- Right-clicking a prim in the stage or viewport and selecting **Add > Add Variant**.
- Right-clicking on an asset in the content browser and selecting **Create Variant Set**.

## Variant Editor Window

The Variant Set Prim Location can be set using the field at the top of the window. The **Variant Set List** on the left side of the window can then be used to manage variant sets on the Variant Set Prim. When a variant is selected from a variant set, the **Prim List** on the right side of the window will provide access to the properties being set by that variant.

![](images/ext_variant_editor_window.png)

| Feature | Result |
|---|---|
| Variant Set Prim Location | Sets the target prim on which variant sets will be edited. |

> **Note:** The Variant Set Prim Location field defaults to the prim that was selected when the editor was opened. If no prim was selected, it instead defaults to the stage root.

## Variant Set List

The list on the left side of the main window displays all variant sets on the Variant Set Prim. From this interface, variant sets and variants can be created and selected.

Selecting a variant from a variant set will make it the current variant for that set. That variant can then be edited from the **Prim List** on the right side of the main window.

![](images/ext_variant_editor_variant_set_list.png)

| Feature | Result |
|---|---|
| Add Variant Set | Adds a new variant set to the target prim. |
| Remove Variant Set | Removes the variant set and all child variants. |
| Add Variant | Adds a new variant to the variant set. |
| Remove Variant | Removes the variant from the variant set. |

Right-clicking a variant set will provide the following options:

| Option | Result |
|---|---|
| Remove | Removes the selected variant set and all child variants. |
| Rename | Provides a text field to rename the selected variant set. |
| Clear Variant Selection | Clears any selection for the selected variant set. |

Right-clicking a variant within a variant set will provide the following options:

| Option | Result |
|---|---|
| Remove | Removes the selected variant from the parent variant set. |
| Rename | Provides a text field to rename the selected variant. |
| Duplicate | Creates a copy of the selected variant within the parent variant set. |
| Clear Selection | Clears any selection for the parent variant set. |

## Prim List

The Prim List on the right side of the main window displays any prims being accessed by the variant currently selected in the **Variant Set List**.

From this interface, prims can be added to or removed from this variant. The properties of such prims can then be added, removed, and modified as needed. Prim properties being set by the variant are listed beneath their parent prim.

![](images/ext_variant_editor_prim_list.png)

| Feature | Result |
|---|---|
| Add Prim | Adds the target prim picked from the stage to the Prim List. |
| Remove Prim | Pressing the red 'X' in the top right corner of a target prim removes it and any of its properties from the current variant. |
| Add Property | Add a property from a list of valid properties for the target prim. |
| Remove Property | Pressing the grey 'X' on the right side of a property removes that property from the current variant. |
| Property Watcher ![](images/ext_variant_editor_property_watcher.png) | Watches a property to determine opinion hierarchy and, if pressed, clears local opinions. |

Right-clicking a target prim will provide the following option:

| Option | Result |
|---|---|
| Remove Prim | Removes the prim and any of its properties from the current variant. |

Right-clicking a property will provide the following option:

| Option | Result |
|---|---|
| Remove Property | Removes the property from the current variant. |

## Related Variant Features

- Variant Workflows
- Variant Presenter
- Variants section of the Property Panel
- USD Python Snippets for variant sets

## Variant OmniGraph Nodes

- HasVariantSet
- GetVariantSetNames
- GetVariantNames
- GetVariantSelection
- SetVariantSelection
- ClearVariantSelection

## Features Supported

- Works with all prim types, including instanceable, referenced, and payloads (see limitations below.)

## Limitations

- Variants contained within a reference or payload must be edited from the source file.
- Variants are subject to USD scene composition standards and as such, variant opinions can be overridden by local or inherited opinions.
- Variant Editor does not currently support Undo/Redo operations.
- The order of list items cannot be changed.
- Only variants in the current authoring layer can be modified in the Variant Editor.
