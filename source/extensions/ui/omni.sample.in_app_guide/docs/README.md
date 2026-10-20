# In-App Guide

![](in-app-guide.png)

# Overview
The In-App Guide is a sample of an interactive tutorial system designed to help users navigate through application features. It provides a step-by-step guide interface that highlights relevant UI elements and explains their functionality.

The extension can be added as-is to a USD Composer created from a Template in the [kit-app-template](https://github.com/NVIDIA-Omniverse/kit-app-template) project; however,
developers can customize it to their specific Kit application and needs.

See [Customizing the Guide](CUSTOMIZE.md) for more information on how to develop with this sample.

## Key Features

- **Interactive Step-by-Step Guidance**: Users can navigate through tutorial steps with next/previous controls and by revealing a list of all contents.
- **UI Element Highlighting**: Visual overlay highlights the relevant UI elements being explained
- **Smart Positioning**: Guide window automatically positions itself relative to the target UI element
- **Interactive Actions**: Supports clicking, expanding, and scrolling to reveal UI elements
- **Customizable Content**: Guide steps can be defined in a JSON configuration file
- **Non-Intrusive Design**: Guide window can be minimized and restored as needed

## Use Cases

- Onboarding new users to the application
- Introducing new features
- Providing context-sensitive help
- Creating interactive tutorials
- Guiding users through complex workflows
