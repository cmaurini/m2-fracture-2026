"""Check the notebooks that CI has just executed.

Executing a notebook is not enough: `jupyter nbconvert --execute` also
succeeds on a notebook whose plots came out empty, so the checks below look
at what the run actually produced.

    python tools/check_notebooks.py executed/*.ipynb
"""

import json
import re
import sys
from pathlib import Path

# Per notebook: the minimum number of rendered images, and the printed
# quantities with the value expected on a correct run.
EXPECTED = {
    "00-Mesh.ipynb": {"images": 1, "values": {}},
    "01-LinearElasticity.ipynb": {
        "images": 2,
        "values": {
            r"The potential energy is\s+(-?[\d.eE+-]+)": -7.577e-01,
            r"The potential energy for Lcrack=[\d.eE+-]+ is\s+(-?[\d.eE+-]+)": -4.174e-01,
        },
    },
}

# The mesh depends on the gmsh version, so the energies move a little from one
# environment to the next. This band is wide enough for that and narrow enough
# to catch a solve that has stopped being the same problem.
RTOL = 0.15


def check(path):
    name = Path(path).name
    spec = EXPECTED.get(name)
    if spec is None:
        return [f"{name}: no expectation recorded for this notebook"]

    cells = json.loads(Path(path).read_text())["cells"]
    failures = []
    images = 0
    text = []

    for cell in cells:
        for out in cell.get("outputs", []):
            if out["output_type"] == "error":
                trace = "\n".join(out.get("traceback", []))
                failures.append(
                    f"{name}: {out['ename']}: {out['evalue']}\n{trace}"
                )
            if any(k.startswith("image/") for k in out.get("data", {})):
                images += 1
            if out["output_type"] == "stream":
                text.append("".join(out["text"]))
            text.append("".join(out.get("data", {}).get("text/plain", "")))

    if images < spec["images"]:
        failures.append(
            f"{name}: {images} rendered image(s), expected at least "
            f"{spec['images']} — pyvista did not draw"
        )

    joined = "\n".join(text)
    for pattern, expected in spec["values"].items():
        match = re.search(pattern, joined)
        if match is None:
            failures.append(f"{name}: nothing printed matching /{pattern}/")
            continue
        got = float(match.group(1))
        if abs(got - expected) > RTOL * abs(expected):
            failures.append(
                f"{name}: got {got:.4e}, expected {expected:.4e} "
                f"within {RTOL:.0%}"
            )

    if not failures:
        print(f"{name}: OK — {images} image(s), {len(spec['values'])} value(s) checked")
    return failures


def main(paths):
    if not paths:
        sys.exit("usage: check_notebooks.py <executed notebook> ...")
    failures = [f for p in paths for f in check(p)]
    for f in failures:
        print(f"FAIL {f}", file=sys.stderr)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
