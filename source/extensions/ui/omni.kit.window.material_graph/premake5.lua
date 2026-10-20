local ext = get_current_extension_info()
project_ext (ext)

repo_build.prebuild_link {
    { "data", ext.target_dir.."/data" },
    { "docs", ext.target_dir.."/docs" },
    { "icons", ext.target_dir.."/icons" },
    { "omni/kit/window/material_graph/scripts", ext.target_dir.."/omni/kit/window/material_graph/scripts" },
    { "omni/kit/window/material_graph/tests", ext.target_dir.."/omni/kit/window/material_graph/tests" },
}

repo_build.prebuild_copy {
    { "omni/kit/window/material_graph/__init__.py", ext.target_dir.."/omni/kit/window/material_graph"},
}

-- C++ Carbonite plugin for texture info
local plugin_name = "omni.kit.window.material_graph.textureUtils"
project_ext_plugin(ext, plugin_name..".plugin")
    kind "SharedLib"
    staticruntime "Off"
    exceptionhandling "On"
    rtti "On"
    language "C++"

    includedirs {
        "plugins/"..plugin_name,
        "%{target_deps}/omni_client_library/include",
        "%{target_deps}/rtx_plugins/include",
    }

    add_files("impl", "plugins/"..plugin_name)
    add_files("iface", "include/omni/kit/window/material_graph/textureUtils/**")

-- Python bindings for texture info plugin
project_ext_bindings {
    ext = ext,
    project_name = "omni.kit.window.material_graph.textureUtils.python",
    module = "_textureUtils",
    src = "bindings/python/textureUtils",
    target_subdir = "omni/kit/window/material_graph"
}
    includedirs {
        "plugins/"..plugin_name
    }

-- C++ GraphCanvas — custom ImGui-style canvas for fast graph rendering.
-- Built as a shared library (NOT a Carbonite plugin). The output is named
-- *.widget.dll instead of *.plugin.dll so it is not picked up by the
-- [[native.plugin]] glob in extension.toml.
local widget_plugin_name = "omni.kit.window.material_graph.graphCanvas"
project_ext_plugin(ext, widget_plugin_name..".widget")
    kind "SharedLib"
    staticruntime "Off"
    exceptionhandling "On"
    rtti "On"
    language "C++"
    cppdialect "C++17"

    includedirs {
        "plugins/"..widget_plugin_name,
        "%{target_deps}/rtx_plugins/include",
        "%{target_deps}/boost-preprocessor",
        "%{kit_sdk}/dev/include",
    }

    libdirs {
        "%{kit_sdk}/dev/lib",
        extsbuild_dir.."/omni.ui/bin",
        "%{kit_sdk}/exts/omni.ui/bin",
    }

    links {
        "omni.ui",
    }

    add_files("impl", "plugins/"..widget_plugin_name)
    removefiles {
        "plugins/"..widget_plugin_name.."/NativeBuildScene.*",
        "plugins/"..widget_plugin_name.."/tests/**",
    }

    -- GCC false-positive in carb's SharedMemory.h (std::lock_guard<NamedSemaphore>
    -- inside carb::cpp::optional) trips -Werror=maybe-uninitialized via the omni.ui
    -- ImageProvider include chain. Demote to a warning for this target only.
    filter { "system:linux" }
        buildoptions { "-Wno-error=maybe-uninitialized" }
    filter {}

-- Fast native tests loaded by omni.kit.test in the extension's existing headless
-- test process. Keeping them in a separate test library prevents test code from
-- entering the production GraphCanvas widget.
local native_test_name = widget_plugin_name..".tests"
project_ext_tests(ext, native_test_name)
    language "C++"
    cppdialect "C++17"

    files {
        "plugins/omni.kit.window.material_graph.graphCanvas/tests/GraphCanvasNativeTests.cpp",
        "plugins/"..widget_plugin_name.."/SugiyamaLayoutNative.cpp",
    }

    includedirs {
        "plugins/"..widget_plugin_name,
    }

    externalincludedirs {
        "%{target_deps}/doctest/include",
    }

    defines {
        "DOCTEST_CONFIG_TREAT_CHAR_STAR_AS_STRING",
        "DOCTEST_CONFIG_SUPER_FAST_ASSERTS",
    }

-- Python bindings for GraphCanvas (includes the canvas C++ source).
project_ext_bindings {
    ext = ext,
    project_name = widget_plugin_name..".python",
    module = "_graphCanvas",
    src = "bindings/python/graphCanvas",
    target_subdir = "omni/kit/window/material_graph"
}
    local p = "plugins/"..widget_plugin_name.."/"
    files {
        p.."*.h",
        p.."GraphCanvasWidget.cpp",
        p.."GraphCanvasResources.cpp",
        p.."GraphCanvasNodeDraw.cpp",
        p.."GraphCanvasBreadcrumb.cpp",
        p.."GraphCanvasInlineEdit.cpp",
        p.."GraphCanvasOverlays.cpp",
        p.."GraphCanvasTooltip.cpp",
        p.."SugiyamaLayoutNative.cpp",
        p.."NativeBuildScene.cpp",
    }
    includedirs {
        "plugins/"..widget_plugin_name,
        "bindings/python/graphCanvas",
        "%{target_deps}/rtx_plugins/include",
        "%{target_deps}/boost-preprocessor",
        "%{kit_sdk}/dev/include",
    }
    libdirs {
        "%{kit_sdk}/dev/lib",
        extsbuild_dir.."/omni.ui/bin",
        "%{kit_sdk}/exts/omni.ui/bin",
    }
    links {
        "omni.ui",
    }

    -- Same carb SharedMemory.h false-positive as the .widget target above; these
    -- bindings compile the same graphCanvas sources, so demote it here too.
    filter { "system:linux" }
        buildoptions { "-Wno-error=maybe-uninitialized" }
    filter {}
