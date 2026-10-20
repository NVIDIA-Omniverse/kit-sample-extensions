import argparse
import glob
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# See [repo_build.post_build] in repo.toml for why this exists


def main(arguments: argparse.Namespace):
    config = arguments.build_config
    platform = arguments.build_platform

    search_path = str(Path(REPO_ROOT, f"_build/{platform}/{config}/ext*/*/pip_*/bin/*.exe"))
    print("globbing for pip exes:", search_path)
    # Multiple extensions can link the same pip bundle. Remove each payload once.
    exes = sorted({Path(exe).resolve() for exe in glob.glob(search_path)})
    print("found pip exes:", exes)

    for exe in exes:
        print("erasing:", exe)
        os.remove(exe)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove pip-generated executable shims from extension bundles.")
    parser.add_argument("--config", dest="build_config", required=True)
    parser.add_argument("--platform", dest="build_platform", required=True)
    main(parser.parse_args())
