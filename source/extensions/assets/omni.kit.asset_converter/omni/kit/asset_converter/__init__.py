import os

# Must be set before .impl imports asset_converter_native_bindings, which
# warns if a foreign pxr build was already loaded. This extension deliberately
# reuses the host's pxr, so the warning is expected noise here.
os.environ.setdefault("SUPPRESS_PXR_CONFLICT_WARNING", "1")

from .impl import *
