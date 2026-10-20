# USD Collections Extension (Preview)

## Extensions

This consists of 3 extensions:

- omni.kit.widget.collection - the collection widget
- omni.kit.property.collection - the collection Property Panel
- omni.kit.window.collection - the Window


## The USD Collection Widget

![](images/ext_usdcollections.png)

This is similar to, but simpler than the Stage Widget. It contains a tree which shows (by default) all prims which contain collections, and their parents

For each collection, it shows its content, which can be any or all of

- Prims which were directly added, or added indirectly by adding other collections
- Child prims of those prims (if the Collections expansion rule is set to "ExpandPrims")
- Properties of those prims (if the Collections expansion rule is set to "ExpandPrimsAndProperties")

You can drag and drop Prims or Collections into a Collection, from either the Stage Widget or the Collection Widget itself.

There are also various filters you can use to change what you see in the tree (see the Filter Icon to the right of the search menu)

> **Note:** A Collections can be created under A Prim from the Stage Widget (Right Click on a Prim and choose "Create->Create Collection")

There are a number of Context menu options available for Collections and their contents


## USD Collection Property Panel

The Collection Widget shows an "expanded" or "baked" view of the Collection, whereas the Property Panel shows the explicitly included or excluded content of the collection

![](images/ext_usd-collection-property.png)

You can use the Property panel to set expansion Rules, and include (or not) the root prim

What you see is very close to what will get serialized to a USD file


## The USD Collection Window

An omni.ui window which hosts the widget


## Materials

USD supports assignment of materials to collections, and Kit-based apps also support this functionality

![](images/ext_collection-materials1.png)


## References

Collections are a somewhat subtle topic, it's best to read up on the fundamentals to understand them well, see:

- Glossary <https://graphics.pixar.com/usd/docs/USD-Glossary.html#USDGlossary-Collection>
- Collection API <https://graphics.pixar.com/usd/docs/api/class_usd_collection_a_p_i.html>
- Collection-based Material Assignment <https://graphics.pixar.com/usd/docs/UsdShade-Material-Assignment.html#UsdShadeMaterialAssignment-BasicProposalforCollection-BasedAssignment>


## Caveats

This is a preview/beta suite of extensions which are still being developed, there are some known limitations with them, and they may change considerably between now and their next release
