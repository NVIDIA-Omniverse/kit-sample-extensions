# SimReady Explorer Developer Guide

## Overview

**SimReady Assets** are the building blocks of industrial virtual worlds. They are built on top of the Universal Scene Description (USD) platform and have accurate physical properties, behaviors, and connected data streams. They are comprised on multiple files such as USD layers, material description files (.mdl), textures, thumbnails, etc.

The **SimReady Explorer extension** allows for working with libraries of SimReady Assets, by enabling users to:
- Find assets by words matched against tags and asset names
- Configure asset behavior, appearance, etc in the browser, before they are assembled into a scene
- Assemble assets into virtual worlds through Omniverse applications such as USD Composer, DriveSim, Isaac Sim, etc.

Through the [**SimReady Explorer API**](./API.rst), developers can:
- Search for assets by matching search words against tags and asset names
- Configure various aspects of assets, as defined by the asset class
- Add the configured assets to a stage

## Finding assets
SimReady Assets have a name, tags, and labels. The labels are derived from the [Wiki Data](https://www.wikidata.org) database, and as such are backed by QCodes. Note that the labels and the QCode of an asset are also part of its list of tags. Both tags and labels can consist of multiple, space separated words.

Finding SimReady Assets is like querying a database. A list of search terms is each matched against the asset's name and tags. Partial matches of the search term in names, tags, and labels are also returned. For example, the search term "wood" would match names such as "recycledwoodpallete" and "crestwood_sofa".

```{eval-rst}
See the :doc:`find_assets() <omni.simready.explorer/omni.simready.explorer.find_assets>` API for details on how to programmatically search for assets.
```

## Configuring assets and adding them to a stage
The `find_assets()` API returns a list of `SimreadyAsset` objects, which can be added to the current stage with the desired behaviors enabled. The behaviors supported currently are the USD variant sets exposed by the asset.
When adding assets to a stage, they can be inserted at a given location, can be parented to another prim, or can be added at or even replace a list of prims.

```{eval-rst}
See the :doc:`add_asset_to_stage() <omni.simready.explorer/omni.simready.explorer.add_asset_to_stage>`, and the :doc:`add_asset_to_stage_using_prims() <omni.simready.explorer/omni.simready.explorer.add_asset_to_stage_using_prims>` APIs for details on how to programmatically add assets to the current stage.
```

# SimReady Explorer API Tutorial
The following code illustrates how to find assets, add them to the current scene, and even replace some of them with other assets. The code below can be executed from the Script Editor of any Omniverse application.

```{eval-rst}
.. literalinclude:: ../../../../source/extensions/ui/omni.simready.explorer/samples/simready_explorer_api_sample.py
   :language: python
   :start-after: example-begin simready_explorer_api_sample
   :end-before: example-end simready_explorer_api_sample
   :dedent:
```

## Future enhancements
The SimReady Explorer API will be extended in the near future to allow defining custom asset classes with specific behaviors.
