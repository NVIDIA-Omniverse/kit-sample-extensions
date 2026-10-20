-- Use folder name to build extension name and tag. Version is specified explicitly.
local ext = get_current_extension_info()

project_ext (ext)
    repo_build.prebuild_link { "docs", ext.target_dir.."/docs" }
    repo_build.prebuild_link { "icons", ext.target_dir.."/icons" }
    repo_build.prebuild_link { "data", ext.target_dir.."/data" }
    repo_build.prebuild_link { "python/tests", ext.target_dir.."/omni/kit/mesh/raycast/tests" }

project_ext_plugin(ext, "omni.kit.mesh.raycast.plugin")
    add_files("impl", "plugins/omni.kit.mesh.raycast")
    add_files("iface", "include")

    -- carb deprecated warnings trigger fatal compile warnings, so we disable them
    removeflags { "FatalCompileWarnings" }

    includedirs {
        "include",
        "%{target_deps}/physx/include",
        "%{target_deps}/usd/%{config}/include",
        "%{target_deps}/gsl/include",
        "%{target_deps}/python/include",
        "%{target_deps}/rtx_plugins/include",
        "%{target_deps}/usd_ext_physics/%{config}/include",
        "%{root}/_build/%{platform}/%{config}/kit/dev/include",
        "%{target_deps}/spline_curve/include",
        "%{root}/_build/%{platform}/%{config}/kit/dev/fabric/include",
    }

    -- Needed for USD notice handler
    rtti "On"

    filter { "system:linux" }
        removeflags { "UndefinedIdentifiers" }
        exceptionhandling "On"
        includedirs {
            "%{target_deps}/python/include",
        }
    filter {}

    -- omni.physx and physx deps
    physx_target_deps = root.."/_build/target-deps"
    local physx = dofile(root.."/tools/premake/physx-build.lua")
    physx.add_dependencies(physx_target_deps.."/physx", "checked")

    if physxDev then
        defines {  "PHYSX_DEV=1" }
    else
        defines {  "PHYSX_DEV=0" }
    end

    links {
        "PhysXExtensions_static_64",
        "PhysXCooking_static_64",
        "PhysXCommon_static_64",
        "PhysXFoundation_static_64",
    }

    -- Linux-specific compile information
    filter { "system:linux" }
        exceptionhandling "On"
        removeflags { "UndefinedIdentifiers" }
        includedirs {
            target_deps.."/usd/%{config}/include",
            target_deps.."/python/include/python3.12",
            target_deps.."/rtx_plugins/include",
            target_deps.."/gsl/include",
        }
        buildoptions { "-pthread" }
        links { "dl", "pthread", "rt" }
        libdirs {
            target_deps.."/cuda/lib64",
            target_deps.."/realm4kit/%{config}/lib64",
        }
    filter {}

    -- Windows specific compile information
    filter { "system:windows" }
        libdirs {
            target_deps.."/cuda/lib/x64",
            target_deps.."/realm4kit/%{config}/lib",
        }
    filter {}

    filter { "system:windows", "platforms:x86_64", "configurations:debug" }
        libdirs {
            target_deps.."/physx/bin/win.x86_64.vc142.md/debug",
            target_deps.."/usd_ext_physics/%{config}/lib",
        }
        defines {  "PX_PHYSX_STATIC_LIB", "_DEBUG" }
    filter {}

    filter { "system:windows", "platforms:x86_64", "configurations:release" }
        libdirs {
            target_deps.."/physx/bin/win.x86_64.vc142.md/checked",
            target_deps.."/usd_ext_physics/%{config}/lib",
        }
        defines {  "PX_PHYSX_STATIC_LIB", "NDEBUG" }
    filter {}

    filter { "system:linux", "platforms:x86_64", "configurations:debug" }
        buildoptions { "-Wno-invalid-offsetof" }
        defines {  "PX_PHYSX_STATIC_LIB", "_DEBUG" }
        libdirs {
			target_deps.."/physx/bin/linux.x86_64/debug",
			target_deps.."/usd_ext_physics/%{config}/lib",
		}
    filter {}

    filter { "system:linux", "platforms:x86_64", "configurations:release" }
        buildoptions { "-Wno-invalid-offsetof" }
        defines {  "PX_PHYSX_STATIC_LIB", "NDEBUG" }
        libdirs {
            target_deps.."/physx/bin/linux.x86_64/checked",
            target_deps.."/usd_ext_physics/%{config}/lib",
        }
    filter {}

    libdirs {
        "%{target_deps}/usd/%{config}/lib",
        "%{kit_sdk_bin_dir}/plugins",
        extsbuild_dir.."/omni.usd.core/bin/",
        "%{target_deps}/python/libs",
    }

    -- Link dependencies
    links {"omni.usd"}

    includedirs {
        "include",
        "%{root}/_build/%{platform}/%{config}/kit/dev/include",
        "%{root}/_build/%{platform}/%{config}/kit/dev/fabric/include",
    }

    add_python()

    -- begin OpenUSD
    extra_usd_libs = {
        "usdUtils",
        "usdGeom",
        "work"
    }

    add_usd(extra_usd_libs)
    -- end OpenUSD

    filter "configurations:Release"
        defines { "NDEBUG" }
        optimize "On"
    filter {}

    filter "configurations:Debug"
        defines { "CARB_DEBUG" }
    filter {}

project_ext_bindings {
    ext = ext,
    project_name = "omni.kit.mesh.raycast.python",
    module = "_meshraycast",
    src = "bindings/python/omni.kit.mesh.raycast",
    target_subdir = "omni/kit/mesh/raycast"
}
    includedirs {
        "include",
        "%{root}/_build/%{platform}/%{config}/kit/dev/include",
        "%{root}/_build/%{platform}/%{config}/kit/dev/fabric/include",
    }

    add_python()
    -- begin OpenUSD
     extra_usd_libs = {
        "usdUtils",
        "usdGeom",
        "work"
    }

    add_usd(extra_usd_libs)
    -- end OpenUSD

    filter "configurations:Release"
        defines { "NDEBUG" }
        optimize "On"
    filter {}

    filter "configurations:Debug"
        defines { "CARB_DEBUG" }
    filter {}
