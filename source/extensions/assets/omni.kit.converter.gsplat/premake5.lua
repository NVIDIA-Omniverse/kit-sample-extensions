-- Use folder name to build extension name and tag. Version is specified explicitly.
local ext = get_current_extension_info()

local gsplat_module = ext.target_dir .. "/omni/kit/converter/gsplat"

-- Kit copies these paths into the staged extension. If a new top-level python/*.py is added
-- for the extension, append its name here or the build will keep an older tree and hot-reload
-- will not pick up the new module.
local gsplat_python_files = {
    "__init__.py",
    "__main__.py",
    "asset_importer_filters.py",
    "asset_importer_hooks.py",
    "cli.py",
    "extension.py",
    "gsplat_asset_importer_delegate.py",
    "gsplat_importer_ui.py",
}

local gsplat_python_copies = {}
for _, name in ipairs(gsplat_python_files) do
    table.insert(gsplat_python_copies, { "python/" .. name, gsplat_module .. "/" .. name })
end

project_ext (ext)
    repo_build.prebuild_link {
        { "data", ext.target_dir .. "/data" },
        { "docs", ext.target_dir .. "/docs" },
        { "python/tests", gsplat_module .. "/tests" },
        { "vendor/usd_convert_gsplat", ext.target_dir .. "/pip_prebundle/usd_convert_gsplat" },
        -- { "python", ext.target_dir .. "/python" }
    }
    repo_build.prebuild_copy(gsplat_python_copies)
