local ext = get_current_extension_info()

-- change name of plugins here
local namespace = "omni/anim/curve/core"

-- lines below can be copied for other plugins
local python_source_path = "python"
local plugin_source_path = "plugins"

ext.group = "animation"

local ogn = get_ogn_project_information(ext, namespace)
project_ext_ogn( ext, ogn )

project_ext (ext)

-- Build Carbonite plugin to be loaded by extension. This plugin implements omni::ext::IExt interface to be automatically
-- started by extension system.
project_ext_plugin(ext, "omni.anim.curve.core.plugin")

    add_files("impl", "plugins")
    add_files("iface", "%{root}/include/"..namespace)
    add_files("ogn", "nodes")

    rtti "On"
    filter {}
    includedirs {
        "%{root}/source/extensions/animation/omni.anim.curve.core/include/build",
        "%{target_deps}/gsl/include",
       "%{target_deps}/usd/%{config}/include",
       "%{kit_dev_dir}/fabric/include",
       "%{target_deps}/omni_client_library/include" ,
       "%{target_deps}/usd_ext_animation/%{config}/include",
       extsbuild_dir.."/usdrt.scenegraph/include",
       "%{target_deps}/pybind11/include",
       "%{target_deps}/python/include"
    }

    libdirs {
        "%{target_deps}/usd/%{config}/lib",
        "%{target_deps}/usd_ext_animation/%{config}/lib"
    }
    links {"usd_ar","usd_vt", "usd_gf", "usd_pcp", "usd_sdf", "usd_arch", "usd_usd", "usd_tf", "usd_trace", "usd_usdUtils", "usd_usdGeom", "usd_usdSkel", extsbuild_dir.."/omni.usd.core/bin/omni.usd", "animationSchemaTools", "animationSchema"}


    filter { "system:linux" }
            exceptionhandling "On"
            removeflags { "FatalCompileWarnings", "UndefinedIdentifiers" }
            includedirs { "%{kit_sdk_bin_dir}/python/include/python3.12" }
		    includedirs { target_deps.."/AnimX/%{config}/include" }
		    libdirs { target_deps.."/AnimX/%{config}"}

			defines { "MAYA_64BIT_TIME_PRECISION"}
			links{"AnimX"}
    filter {}

    filter { "system:windows" }
	    includedirs { target_deps.."/AnimX/%{config}/include" }
	    libdirs { "%{target_deps}/AnimX/%{config}/lib"}
	    links {"AnimX"}
	    defines { "MAYA_64BIT_TIME_PRECISION" }
        disablewarnings {"4307"}
    filter {}
    if os.target() == "windows" then
        -- Windows also builds with AnimX so copy that dll to a findable location
        repo_build.prebuild_copy {
            { target_deps.."/AnimX/%{config}/bin/AnimX.dll", ext.target_dir.."/bin" },
        }
    else
        repo_build.prebuild_copy {
            { target_deps.."/AnimX/%{config}/libAnimX.so", ext.target_dir.."/bin" },
        }
    end

    add_ogn_dependencies(ogn)

-- python bindings
project_ext_bindings {
    ext = ext,
    project_name = "omni.anim.curve.core.python",
    module = "_animcurve",
    src = "bindings",
    target_subdir = namespace.."/bindings"
}
    add_usd()
    filter { "configurations:debug" }
        defines { "TBB_USE_DEBUG=1" }
    filter  { "configurations:release" }
        defines { "TBB_USE_DEBUG=0" }
    filter {}
    includedirs {
        "%{root}/source/extensions/animation/omni.anim.curve.core/include/build",
		"%{target_deps}/usd_ext_animation/%{config}/include",
		"%{target_deps}/AnimX/%{config}/include",
		}
    filter { "system:linux" }
        removeflags { "FatalCompileWarnings"}
    filter{}

repo_build.prebuild_copy {
    { "python/*.py", ext.target_dir.."/"..namespace },
}

repo_build.prebuild_link {
    { "python/scripts", ext.target_dir.."/"..namespace.."/scripts" },
}
repo_build.prebuild_link {
    { "python/tests", ext.target_dir.."/"..namespace.."/tests" },
}

repo_build.prebuild_link {
    {"docs/", ext.target_dir.."/docs"},
}

repo_build.prebuild_link {
    {"data/", ext.target_dir.."/data"},
}
