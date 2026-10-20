"""Generate resource-only USD schemas with the repository's Kit USD dependency."""

import json
import os
import subprocess
from pathlib import Path


def usd_environment(root, config):
    usd_root = root / "_build" / "target-deps" / "usd" / config
    python_root = root / "_build" / "target-deps" / "python"
    python = python_root / ("python.exe" if os.name == "nt" else "bin/python3")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        str(path.resolve()) for path in (usd_root / "lib/python", root / "_build/target-deps/animation-schema-python")
    )
    library_paths = os.pathsep.join(str((usd_root / path).resolve()) for path in ("lib", "bin"))
    env["PATH"] = library_paths + os.pathsep + env.get("PATH", "")
    if os.name == "nt":
        env["PXR_USD_WINDOWS_DLL_PATH"] = library_paths
    else:
        env["LD_LIBRARY_PATH"] = library_paths + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    return python, usd_root, env


def generate_schema(root, config, input_file, output_dir):
    python, usd_root, env = usd_environment(root, config)
    output_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(python), str(usd_root / "bin/usdGenSchema"), str(input_file), str(output_dir)],
        check=True,
        env=env,
    )

    # Normalize the plugin paths, including previously staged compiled-schema metadata.
    # usdGenSchema preserves existing plugInfo fields on incremental builds.
    plug_info = output_dir / "plugInfo.json"
    content = plug_info.read_text(encoding="utf-8")
    data = json.loads("\n".join(line for line in content.splitlines() if not line.lstrip().startswith("#")))
    for plugin in data["Plugins"]:
        if plugin["Type"] != "resource":
            raise ValueError(f"{input_file} must declare skipCodeGeneration = true")
        plugin.update(LibraryPath="", ResourcePath="resources", Root="..")
    plug_info.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
    # usdGenSchema may leave identical output untouched. Both build outputs must be newer than the input.
    os.utime(output_dir / "generatedSchema.usda", None)


def setup_repo_tool(parser, config_dict):
    parser.add_argument("-c", "--config", choices=["debug", "release"], default="release")
    parser.add_argument("-i", "--input-file", type=Path)
    parser.add_argument("-o", "--output-dir", type=Path)
    parser.add_argument("--test", action="store_true", help="Test the staged schemas using Kit's USD and Python")

    def run(options, config_dict):
        root = Path(__file__).resolve().parents[2]
        if options.test:
            from omni.repo.man.configuration import resolve_tokens

            python, _, env = usd_environment(root, options.config)
            env["ANIMATION_SCHEMA_EXTS"] = str(
                root / "_build" / resolve_tokens("${platform}") / options.config / "exts"
            )
            subprocess.run([str(python), str(root / "tools/schema/test_schema.py")], env=env, check=True)
        else:
            if options.input_file is None or options.output_dir is None:
                parser.error("--input-file and --output-dir are required unless --test is specified")
            generate_schema(root, options.config, options.input_file.resolve(), options.output_dir.resolve())

    return run
