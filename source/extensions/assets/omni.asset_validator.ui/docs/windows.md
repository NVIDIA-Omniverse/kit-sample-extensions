# Windows

The Asset Validator panel can be opened via the *Window > Utilities > Asset Validator* submenu.
Click this menu item to open or close the _Asset Validator Window_.

![Asset Validator Window](../data/docs/asset-validator-callouts.png)

| #  | Option                   | Description                                                                                                                                        |
|----|--------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | Asset Mode               | Switches between **URI**, **Stage** and **Prim**.                                                                                                  |
| 2  | Asset Description        | Describes the selected mode. In URI this should be the fully qualified URI, in Stage the description of the asset and in Prim mode the Prim paths. |
| 3  | Asset URI Browser        | Click the button to launch a _File Picker_ and select any USD layer or folder. Only available in **URI** mode.                                     |
| 4  | Options Enable/Disable   | These buttons toggle all options within each category.                                                                                             |
| 5  | Options Checkboxes       | These checkboxes will enable/disable individual Rules or Requirements.                                                                             |
| 6  | Options Labels           | Hover on the labels to reveal a tooltip description for each Rule or Requirement.                                                                  |
| 7  | Options Settings         | Menu to select options settings.                                                                                                                   |
| 8  | Action Analyze           | Click this to analyze the current asset with the enabled Rules or Requirements.                                                                    |
| 9  | Action Fix Selected      | Click this to fix selected issues. Runs validation after fixing.                                                                                   |
| 10 | Action Clear Results     | Clears out the information produced when analyzing or fixing errors.                                                                               |
| 11 | Search field             | Search for a specific rule or requirement.                                                                                                         |
| 12 | Search filters           | Filters the rules or requirements based on the search query.                                                                                       |
| 13 | Search settings          | Group the rules or requirements.                                                                                                                   |
| 14 | Results panel            | Displays the results of the validation.                                                                                                            |

## Using the Stage Window

To validate the current stage (i.e. the entire layer stack), right click on the empty space (with no prims
selected) in the *Stage Window* and a context menu ``Validate Stage`` will be available (1):

![Launch from Stage Window](../data/docs/asset-validator-stageWindow.png)

This will launch the _Asset Validator Window_, preset to **Stage** mode and point to the current stage:

![Stage Mode](../data/docs/asset-validator-stageMode.png)


To validate a set of prims, right click on one or multiple prims in the *Stage Window* and a context menu
``Validate Prims`` will be available (1):

![Launch from Stage Window](../data/docs/asset-validator-primWindow.png)

This will launch the _Asset Validator Window_, preset to **Prim** mode and point to the selected prims:

![Prim Mode](../data/docs/asset-validator-primMode.png)

```{eval-rst}
.. caution::
    This is a live operation that will **not** alter the main stage. Any edits will create a session sublayer, which
    requires switching the authoring layer temporarily. This will not alter layers, so no need to save or lock
    the layers first. The authoring layer will be restored when validation completes.
```

## Using the Content Browser

To run the asset validation on files from the _Content Browser_, right click on a USD file and select
``Validate USD`` from the context menu (1):

![Launch from File in Content Browser](../data/docs/asset-validator-contentBrowser-file.png)

To validate a specified folder, right click and a context menu entry called
``Search for USD files and Validate`` will be available (1):

![Launch from Folder in Content Browser](../data/docs/asset-validator-contentBrowser-folder.png)

These actions will launch the _Asset Validator Window_ set to **URI Mode** and pointing to the file or folder
specified in the _Content Browser_.

## Using the Layer Window

To validate layers that are currently open, in the _Layer Window_ right click on any layer (except session layers)
to see the following related context menus (1,2). This will launch the _Asset Validator Window_ preset to either
**URI Mode** or **Stage Mode** and load to the requested assets to validate:

![Launch from Layer Window](../data/docs/asset-validator-layerWindow.png)

Layers will provide either ``Validate Layer (w/unsaved changes)`` (1) or ``Validate Layer (from file)`` (2)
entries, depending if there are currently unsaved changes to the layer. Both of these "live" options will operate
in **Stage Mode**, on a bespoke stage containing only that layer and its sublayers:

![Stage Mode launched from Layer Window](../data/docs/asset-validator-layer-stageMode.png)

```{eval-rst}
.. important::
    Any edits will occur on a session sublayer, so neither option will save or alter the selected layer.
    No need to lock the layer first.
```

Layers that are associated with a file (i.e are not anonymous) will also provide an entry called
``Validate Layer (from file)``. Use this entry to operate in **URI Mode** on the file, ignoring any changes
made in the application:

![URI Mode launched from Layer Window](../data/docs/asset-validator-layer-uriMode.png)
