local m = {} -- The main module table

repo_build = require("omni/repo/build")
repo_build.setup_options()

include("scene-optimizer-options")
print("Building with usd_flavor="..USD_FLAVOR.." and usd_ver="..USD_VERSION.." and python_ver="..PYTHON_VERSION)


-- Common Global Variables
target_deps = target_deps or repo_build.target_deps_dir()

-- The external usd_optimize package (core lib + operations + python), pulled via packman.
-- See deps/target-deps.packman.xml. Layout: include/, lib/ (+ lib/operations, operation_mapping.json),
-- python/, extraLibs/.
-- Config-separated (release/debug) like USD, so a combined `--config release debug` build does not
-- collide the two variants in one dir (which would leave the release plugin linked against debug libs).
usd_optimize_dir = usd_optimize_dir or target_deps.."/usd_optimize/%{config}"


-- Convenience function to include USD headers and libs
function m.use_usd()

    externalincludedirs {
        target_deps.."/usd/%{config}/include",
    }

    libdirs {
        target_deps.."/usd/%{config}/lib",
    }

    -- The product layer only links a small USD surface: it forwards stages/paths to the
    -- usd_optimize core lib (which carries the heavy USD deps) and parses op args via Js.
    -- arch/tf/vt/gf are the foundational layer that sdf/usd inline code pulls in.
    add_usd {"arch", "tf", "vt", "gf", "sdf", "usd", "usdUtils", "js"}

    filter { "configurations:debug" }
        links {"tbb_debug"}
    filter  { "configurations:release" }
        links {"tbb"}
    filter {}

end


-- Build against the external usd_optimize core library (packman dep): headers from usd_optimize/include
-- (namespace usd_optimize, <usd_optimize/core/...>), linking libusd_optimize.core.
function m.use_usd_optimize()

    externalincludedirs { usd_optimize_dir.."/include" }
    libdirs { usd_optimize_dir.."/lib" }
    links { "usd_optimize.core" }

end


-- Deploy the usd_optimize runtime artifacts into a destination bin dir (the core extension's bin):
-- the operation plugins and operation_mapping.json sit next to the core lib, and the runtime sibling
-- libs (autouv, omnimesh) are alongside it for the loader.
function m.deploy_usd_optimize_runtime(dest_bin_dir)
    local lib = usd_optimize_dir.."/lib"

    -- The core lib plus its runtime sibling libs (autouv/omnimesh/mesh_tools). Shared-library naming is
    -- platform specific (lib*.so on linux, *.dll on windows), so select the names per target.
    if os.target() == "windows" then
        repo_build.prebuild_copy {
            { lib.."/usd_optimize.core.dll", dest_bin_dir },
            { lib.."/autouv-core.dll", dest_bin_dir },
            { lib.."/omnimesh_ops*.dll", dest_bin_dir },
            { lib.."/mesh_tools_lib.dll", dest_bin_dir },
        }
    else
        repo_build.prebuild_copy {
            { lib.."/libusd_optimize.core.so", dest_bin_dir },
            { lib.."/libautouv-core.so", dest_bin_dir },
            { lib.."/libomnimesh_ops*.so", dest_bin_dir },
            { lib.."/libmesh_tools_lib.so", dest_bin_dir },
        }
    end

    -- The operation mapping is platform independent.
    repo_build.prebuild_copy {
        { lib.."/operation_mapping.json", dest_bin_dir },
    }

    -- Operation plugins live under lib/operations: prebuilt C++ plugins and python-implemented
    -- operations (subdirectories with __init__.py, e.g. pythonScript). The core library loads them from
    -- an "operations" dir next to the core lib. Copy the whole directory recursively: an
    -- "operations/*" glob would only match the plugin libs and drop the python op subdirectories.
    repo_build.prebuild_copy {
        { lib.."/operations", dest_bin_dir.."/operations" },
    }
end


return m
