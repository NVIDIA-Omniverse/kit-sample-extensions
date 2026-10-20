local ext = get_current_extension_info()

project_ext (ext)

repo_build.prebuild_link { "$root/_build/target-deps/pip_prebundle_services", ext.target_dir.."/pip_prebundle" }
repo_build.prebuild_link { "omni", ext.target_dir.."/omni" }
repo_build.prebuild_link { "docs", ext.target_dir.."/docs" }
repo_build.prebuild_link { "data", ext.target_dir.."/data" }
