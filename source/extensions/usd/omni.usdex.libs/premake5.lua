-- Use folder name to build extension name and tag. Version is specified explicitly.
local ext = get_current_extension_info()
local library_dir = os.target() == "windows" and "bin" or "lib"

-- Create extension folder structure
project_ext (ext)

    repo_build.prebuild_link {
        -- Link extension data
        { "data", ext.target_dir.."/data" },
        { "docs", ext.target_dir.."/docs" },

        -- Link test python module
        -- TODO: Move to a "tests" folder
        { "omni", ext.target_dir.."/python/omni" },

        -- Link vendored includes folder for dependent C++ extensions
        -- Individually link "core" and "rtx" folders since we don't include "test" and "pybind" in the extension
        {"%{root}/_build/target-deps/usd-exchange/%{config}/include/usdex/core", ext.target_dir.."/include/usdex/core"},
        {"%{root}/_build/target-deps/usd-exchange/%{config}/include/usdex/rtx", ext.target_dir.."/include/usdex/rtx"},
    }

    repo_build.prebuild_copy {
        -- Copy vendored python modules
        -- Individually copy "core" and "rtx" python modules, we don't include "test" in the extension
        {"%{root}/_build/target-deps/usd-exchange/%{config}/python/usdex/core", ext.target_dir.."/python/usdex/core"},
        {"%{root}/_build/target-deps/usd-exchange/%{config}/python/usdex/rtx", ext.target_dir.."/python/usdex/rtx"},

        -- Copy vendored libraries
        {"%{root}/_build/target-deps/usd-exchange/%{config}/"..library_dir.."/${lib_prefix}*${lib_ext}", ext.target_dir.."/bin" },
    }
