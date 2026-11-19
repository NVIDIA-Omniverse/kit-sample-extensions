"""Keep staged extensions on the selected Kit's TBB runtime.

Run after repo_build stages vendor binaries and before native compilation. Only
runtime files directly in extension bin directories are removed; fetched vendor
packages, Kit, import libraries, and pip environments remain untouched.
"""
import argparse
from pathlib import Path
import re


LINUX_RUNTIME = re.compile(r"(libtbb(?:malloc(?:_proxy)?|bind(?:_\d+_\d+)?)?(?:_debug)?)\.so((?:\.\d+)*)$")
WINDOWS_RUNTIME = re.compile(r"tbb(?:12|malloc(?:_proxy)?|bind(?:_\d+_\d+)?)(?:_debug)?\.dll$", re.I)


def use_kit_tbb(build: Path, *, check: bool = False) -> list[Path]:
    extensions = build / "exts"
    # Precache resolves the selected provider here for kernel and SDK builds.
    provider = build / "extsbuild/omni.usd.libs/bin"
    if not provider.is_dir():
        provider = build / "kit/exts/omni.usd.libs/bin"
    replacements = []
    for binary_dir in sorted(extensions.glob("*/bin")):
        for binary in sorted(binary_dir.iterdir()):
            linux = LINUX_RUNTIME.fullmatch(binary.name)
            if not linux and not WINDOWS_RUNTIME.fullmatch(binary.name):
                continue
            # Unlink staged files, never a vendor cache reached through a directory link.
            if not binary_dir.resolve().is_relative_to(extensions.resolve()):
                raise RuntimeError(f"Extension bin directory links outside staged extensions: {binary_dir}")
            if not binary.is_file() and not binary.is_symlink():
                raise RuntimeError(f"Expected a TBB runtime file: {binary}")
            if linux:
                family, versions = linux.groups()
                major = versions.split(".")[1] if versions else None
                candidates = ([provider / f"{family}.so.{major}"] if major
                              else list(provider.glob(f"{family}.so*")))
            else:
                candidates = [provider / binary.name]
            if not any(path.is_file() for path in candidates):
                raise RuntimeError(f"Kit has no replacement for {binary.name} in {provider}")
            replacements.append(binary)

    # Validate the entire selection before changing the staging tree.
    if check and replacements:
        raise RuntimeError("Extension-local TBB runtimes remain: " + ", ".join(map(str, replacements)))
    for binary in replacements:
        binary.unlink()
        print(f"Using Kit TBB instead of {binary}")
    return replacements


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    use_kit_tbb(root / "_build" / args.platform / args.config, check=args.check)
