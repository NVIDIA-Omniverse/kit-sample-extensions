"""Test suite for the Material Graph Window extension (omni.kit.window.material_graph).

This package contains all tests for the extension. The suite is organized by layer and responsibility:
api (plugin/config/versioning), commands (USD and kit command execution), config (paths and catalog),
context (material context manager and switching), conventions (logging policy), fixtures (shared stubs),
interaction (graph delegates, menus, hit testing), models (catalog, isolation, connections, sync),
plugins (manager core, MDL, catalog build), preferences (path lists), settings (persistence and UI),
startup/shutdown (extension lifecycle and window creation), ui (window, toolbar, catalog, drop handlers),
utils (color, cache, export, texture, async, command result), and visual (graph/backdrop/error UX).

Tests are discovered by importing each subpackage; the root __init__ re-exports subpackages so that
running the tests package or a subfolder runs the corresponding test modules."""

from .api import *  # noqa: F401,F403,E402
from .commands import *  # noqa: F401,F403,E402
from .config import *  # noqa: F401,F403,E402
from .context import *  # noqa: F401,F403,E402
from .conventions import *  # noqa: F401,F403,E402
from .interaction import *  # noqa: F401,F403,E402
from .materialx_upgrade import *  # noqa: F401,F403,E402
from .models import *  # noqa: F401,F403,E402
from .native import *  # noqa: F401,F403,E402
from .plugins import *  # noqa: F401,F403,E402
from .preferences import *  # noqa: F401,F403,E402
from .settings import *  # noqa: F401,F403,E402
from .shutdown import *  # noqa: F401,F403,E402
from .startup import *  # noqa: F401,F403,E402
from .ui import *  # noqa: F401,F403,E402
from .utils import *  # noqa: F401,F403,E402
from .validation import *  # noqa: F401,F403,E402
from .workflows import *  # noqa: F401,F403,E402
