# Remove Unused Tool [omni.kit.tool.remove_unused.core]

This is a tool for optimizing stages in Omniverse by removing unused prims.

## Tool Functionality

The Remove Unused Tool contains a total of three functions that can be used to conduct operations on a given stage to remove unused prims.  At present time the only prims covered are materials but the scope of the tool could expand in the future for other similar operations.

`get_excess_materials(stage)`: If this funciton is called it will iterate through all of the prims in a stage, identify materials, and determine whether or not those materials are currently bound to a prim in the stage.  It returns a list of all prims that are not currently bound.  The require argument for this function is a `stage` reference.

`delete_mats(mat_list)`: If this function is called it will delete all the prims provided in the argument `mat_list` using the omni.kit.command "Delete Prims".  As a result, this process can be reversed with an `Undo` operation.

`find_and_delete_mats(cls, stage)`: If this function is called it will execute the previous two functions in sequence.  The required arguments for this function are a reference to the class itself `RemoveUnusedCore` and a reference to the `stage` to be operated on.