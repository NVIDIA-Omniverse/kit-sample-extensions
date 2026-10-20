# Sample CSV Reader Extension (omni.sample.csv_reader)

![CVS Reader UI and Result](../data/OV_CSVReader_WhatToExpect.png)

## Overview

The CSV Reader extension offers the possibility for users to populate the scene with some default shapes (Cubes or Spheres) at locations X, Y, Z found in the CSV file.


Colors are also added depending on the _cluster_ values given as well in the CSV file.

Column 0: name (string) - identifier for the data point
Column 1: x (float) - X coordinate in 3D space
Column 2: y (float) - Y coordinate in 3D space
Column 3: z (float) - Z coordinate in 3D space
Column 4: cluster (string/int) - cluster identifier for grouping

## Usage

### Prerequisites :
1) CSV Files place : either use the ones by default in the _data_ folder - or make sure to specify its place in the field of the UI
2) Note that the CSV file should contain X, Y, Z and cluster columns. Please look at examples provided in the _data_ folder

### Workflow using the extension:

Click on 'Generate' -> that will create elements here and there based on the info from the CSV file.

1. [Optional] : In the parameters UI window, select the location of your CSV, the type of shape, and if you want to be grouped by class/_cluster_...
2. If required : you can export/save the USD stage with the 'File->Save As...' option.
