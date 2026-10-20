# omni.kit.property.collection

## Introduction

Collections are a way to group/organise prims and properties in USD. They are a set of properties which can be crated under any prim in the scene. Collections can be included in other collections (recursively)
Prims can be explicitly included in a collection (or excluded from it). Setting the appropriate expansion rule brings in their children (recursively) and their properties. Anything included can also be excluded.
See https://graphics.pixar.com/usd/docs/USD-Glossary.html#USDGlossary-Collection for more info

## This extension

This extension shows the 4 properties of collections in a single panel. You can add to the include or exclude list, set the expansionRules, or set the collection to includeRoot