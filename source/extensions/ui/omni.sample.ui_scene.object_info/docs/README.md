# Omni.UI Scene Sample Object Info Extension

## Overview

This extension demonstrates how to leverage `ui.scene.Widget` to create 3D UI widgets in the viewport. It shows how to display object information with visual indicators (leader lines) that connect to selected objects in your scene.

## What It Does

When you select an object in the viewport, this extension:
- Displays the object's USD path
- Shows the assigned material name
- Draws a leader line connecting the information to the object
- Keeps text facing the camera for easy reading
- Updates in real-time as you select different objects

## Key Components

The extension is built on three main files:

1. **viewport_scene.py** - Sets up the viewport scene
2. **widget_info_manipulator.py** - Manages the visual presentation (leader lines, text labels)
3. **widget_info_model.py** - Connects the USD world data with the manipulator

## Architecture

- **Model Layer**: Tracks selected object information, USD prim references, and object positions
- **Manipulator Layer**: Creates the visual representation with leader lines and camera-facing text
- **USD Integration**: Monitors selection changes, retrieves object properties, and computes bounding boxes

## Setup

Add the extension to your application `.kit` file:

```toml
[dependencies]
"omni.sample.ui_scene.object_info" = {}
```

Or add the extension path if using from a local directory:

```toml
[settings.app.exts]
folders.'++' = ["<full path to the extension samples source/extensions directory>"]
```
