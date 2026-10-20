# Overview

This extension exposes modules that contain all the user-facing elements of the Data2UI toolset for USD.

That includes:

- Un/Re-doable kit Commands to create UI Prims.
- Kit Actions to run those commands.
- Methods for creating and manipulating properties on prims that mirror omni.ui Widget properties, respecting inheritance.
- Menus for Creation of UI Prims ("Create"),
- Stage menus for Reordering UI Prims,
- Property menus for adding Style properties to UI Prims,
- A Data2UI USD Property Widget, enforcing custom behavior for some properties, like *_fn properties to actions/events.

This module does not present any useful public API currently, with the expectation that it is consumed via the UI.
It is currently representative of an MVP effort so consume the private API at your discretion.
