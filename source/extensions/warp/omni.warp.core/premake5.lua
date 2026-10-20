-- Build pipeline executed via running `repo.sh build`:
--
-- 1. Fetch Native Dependencies
--    Uses `repo_build.fetch.packman_target_files_to_pull` in `repo.toml` to pull in the dependencies
--    listed in `deps/warp-build-deps.packman.xml` that are required for building the library.
--
-- 2. Fetch Python Dependencies
--    Uses `repo_build.fetch.pip.files_to_pull` in `repo.toml` to pull in the Python dependencies
--    listed in `deps/warp-build-pip.toml` that are required for executing the build script.
--
-- 3. Initialize Git Submodule
--    Uses `repo_build.fetch.after_pull_commands` in `repo.toml` to clone/update the Git submodule
--    representing the library located at `source/extensions/warp/omni.warp.core/warp`.
--
-- 4. Build Library
--    Uses `repo_build.pre_build.commands` in `repo.toml` to trigger the build of the Warp library
--    using the script at `source/extensions/warp/omni.warp.core/build.py`.
--
-- 5. Finalize Extension
--    Uses this `premake5.lua` file to symlink the necessary files for the extension.
--
--
-- Note: The library build could in theory be defined here as a `prebuildcommands` directive.
--       However, OmniGraph's build script duplicates that directive's content for the other Warp extension
--       that uses `project_ext_ogn()`. To avoid this, the build is triggered once from `repo.toml` instead.

local ext = get_current_extension_info()

project_ext(ext)

    repo_build.prebuild_link {
        { "data", ext.target_dir .. "/data" },
        { "docs", ext.target_dir .. "/docs" },
        { "omni", ext.target_dir .. "/omni" },
        { "warp/warp", ext.target_dir .. "/warp" },
    }
