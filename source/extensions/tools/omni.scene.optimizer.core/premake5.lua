-- Build file for the extension.
ext = get_current_extension_info()

-- Put this project into the simulation IDE group
ext.group = "extensions"

project_ext( ext )

-- Set up the location names for the plugin
local namespace = "omni/scene/optimizer/core"
local interface_source_path = "interface"

so_build = require("tools/premake/scene-optimizer-build")

-- ----------------------------------------------------------------------
-- The main plugin is what implements the functionality
project_ext_plugin( ext, "omni.scene.optimizer.core.plugin" )

    -- Sort out the files into rough correspondence with the file tree
    add_files("impl", interface_source_path)
    add_files("config", "config")
    add_files("iface", "%{root}/include/"..namespace)

    -- Add RC info file for windows
    filter { "system:windows" }
    files("%{root}/_build/scene-optimizer.rc")
    filter {}

    repo_build.prebuild_link {
        { "data", ext.target_dir.."/data" },
        { "docs", ext.target_dir.."/docs" },
        -- Deploy the usd_optimize python package (bindings + pure-python core) from the external
        -- package onto the extension's python path so the extension's `from usd_optimize.impl.core
        -- import *` resolves. This brings the _usd_optimize_impl_core binding too. We intentionally
        -- do NOT deploy the package's omni.scene.optimizer back-compat shim, which would hijack the
        -- Kit-registered omni.scene.optimizer.* extension modules.
        { usd_optimize_dir.."/python/usd_optimize", ext.target_dir.."/usd_optimize" },
    }

    -- Standard way of building in Omniverse
    exceptionhandling "On"
    rtti "On"
    language "C++"
    staticruntime "Off"

    -- Define the runtime to match the build configuration
    filter { "configurations:debug" }
        runtime "Debug"
    filter  { "configurations:release" }
        runtime "Release"
    filter {}

    filter { "system:windows" }
        -- Given we compile all our plugins with the exact same compiler as the
        -- core library, every time, we disable this in order to simplify some
        -- code. For example, in the OmniOperation derived classes, this lets us
        -- simplify some code instead of hacking around dll boundary issues.
        disablewarnings { "4251" } -- (warning C4251: needs to have a dll-interface)
    filter {}

    -- Deploy the usd_optimize runtime next to this extension's plugin: the core lib, its runtime
    -- sibling libs (autouv/omnimesh) that Kit does not provide, the prebuilt operation plugins
    -- (in an operations/ subdir) and operation_mapping.json. The core lib discovers operations and
    -- the mapping relative to its own location, so this layout must be preserved.
    so_build.deploy_usd_optimize_runtime(ext.bin_dir)

    -- Linux-specific compile information
    filter { "system:linux" }
        exceptionhandling "On"
        removeflags { "UndefinedIdentifiers" }
        linkoptions { "-Wl,--disable-new-dtags" }
    filter {}

    -- Specifies the external libraries required by the nodes
    -- USD
    so_build.use_usd()

    -- Link the usd_optimize core library. We do NOT link mesh_tools / omnimesh directly: this plugin
    -- doesn't reference their symbols, and they are internal dependencies of libusd_optimize.core.so
    -- (mesh_tools is static/baked in; libomnimesh_ops*.so lives in the package lib dir that use_usd_optimize
    -- already puts on the link path and is deployed beside the core lib at runtime).
    so_build.use_usd_optimize()

-- ----------------------------------------------------------------------
-- Python support and scripts
project_ext_bindings {
    ext = ext,
    project_name = "omni.scene.optimizer.python",
    module = "_omni_scene_optimizer_core",
    src = "bindings",
    target_subdir = ext.target_dir.."/"..namespace.."/bindings"
}
    so_build.use_usd()
    so_build.use_usd_optimize()

    repo_build.prebuild_copy {
        { "python/__init__.py", ext.target_dir.."/"..namespace },
    }

    repo_build.prebuild_link {
        { "python/scripts", ext.target_dir.."/"..namespace.."/scripts" },
    }

    -- Kit extension tests.
    local ext_tests = ext.target_dir.."/"..namespace.."/tests"
    repo_build.prebuild_copy {
        { "python/tests/*.py", ext_tests },
    }