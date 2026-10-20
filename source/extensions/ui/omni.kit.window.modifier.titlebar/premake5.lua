-- Use folder name to build extension name and tag. Version is specified explicitly.
local ext = get_current_extension_info()

project_ext (ext)
    cppdialect "C++17"
    repo_build.prebuild_link { "icons", ext.target_dir.."/icons" }
    repo_build.prebuild_link { "data", ext.target_dir.."/data" }
    repo_build.prebuild_link { "docs", ext.target_dir.."/docs" }
    repo_build.prebuild_copy { "omni", ext.target_dir.."/omni" }


project_ext_bindings {
    ext = ext,
    project_name = "omni.kit.window.modifier.titlebar.python",
    module = "_modifier",
    src = "bindings",
    target_subdir = "omni/kit/window/modifier/titlebar/bindings"
}
