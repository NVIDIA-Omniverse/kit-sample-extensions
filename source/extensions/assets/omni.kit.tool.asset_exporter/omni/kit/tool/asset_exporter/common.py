# Kit 111 EA1 scope: omni.mdl.distill_and_bake is not supported (Kit 111 #1505 removed it), so MDL baking on export
# is disabled. Set to True to re-enable once a Kit ships the extension again (and restore the manifest dependency).
BAKE_MDL_SUPPORTED = False

BAKE_MDL_UNSUPPORTED_MESSAGE = (
    "Baking MDL materials on export is not supported in this Kit (omni.mdl.distill_and_bake is unavailable); "
    "exporting without baking."
)
