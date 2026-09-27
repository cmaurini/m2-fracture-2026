"""Check that this environment carries what the installation file promises.

The notebooks run in three places — a student's conda environment, a
Codespace, and Binder — and all three are built from the same environment
file, https://github.com/cmaurini/fenicsx-install. This imports every
dependency that file lists, so that a package added there and missing here is
a failed build rather than a failed cell in the lecture hall.

    python tools/check_environment.py [environment.yml]

The default path is /opt/environment.yml, where the image keeps the file it
was built from.
"""

import importlib
import re
import sys
from pathlib import Path

import yaml

DEFAULT = "/opt/environment.yml"

# Conda names that are not the module name.
MODULE = {
    "fenics-dolfinx": "dolfinx",
    "python-gmsh": "gmsh",
    "pyyaml": "yaml",
    "matplotlib": "matplotlib.pyplot",
}

# Dependencies that are not importable Python: the interpreter itself, a
# library, a command-line tool, a JupyterLab extension.
NOT_A_MODULE = {"python", "mpich", "gmsh", "ruff", "jupyterlab-myst"}


def dependencies(path):
    """The conda package names listed in an environment file, unversioned."""
    spec = yaml.safe_load(Path(path).read_text())
    names = []
    for item in spec.get("dependencies", []):
        if isinstance(item, dict):  # a nested "pip:" list
            for sub in item.get("pip", []):
                names.append(sub)
        else:
            names.append(item)
    return [re.split(r"[=<>!\s]", name, maxsplit=1)[0] for name in names]


def check(path):
    missing = []
    checked = 0
    for name in dependencies(path):
        if name in NOT_A_MODULE:
            continue
        module = MODULE.get(name, name.replace("-", "_"))
        try:
            importlib.import_module(module)
        except Exception as exc:  # an import error, or a broken install
            missing.append(f"{name}: import {module} failed — {exc}")
        else:
            checked += 1
    print(f"{Path(path).name}: {checked} dependency import(s) OK")
    return missing


def main(argv):
    path = argv[0] if argv else DEFAULT
    if not Path(path).exists():
        sys.exit(f"no environment file at {path}")
    missing = check(path)
    for m in missing:
        print(f"FAIL {m}", file=sys.stderr)
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
