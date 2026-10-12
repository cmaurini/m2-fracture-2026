"""Check the homework modules, which the starter notebook cannot check.

The starter `homework-2026/hw2026.ipynb` has blank cells and does not run to
the end, so CI does not execute it. It checks instead the two modules the
notebook imports: `utils/solve_dcdc.py` at the reference point a = 2R, W = 2R,
nu = 0.2, plane strain, where G-theta and the finite difference of the
potential energy agree on g = G E / (sigma^2 R) = 0.5376.

    python tools/check_homework.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "utils"))

import solve_dcdc as sd  # noqa: E402

EXPECTED = 0.5376
RTOL = 0.01

out = sd.solve(2.0, half_width=2.0, nu=0.2)
values = {"G-theta": sd.g_theta(out),
          "finite difference": sd.g_finite_difference(2.0, half_width=2.0, nu=0.2)}

failures = []
for name, got in values.items():
    ok = abs(got - EXPECTED) <= RTOL * EXPECTED
    print(f"{'OK  ' if ok else 'FAIL'} g, {name:<18s} = {got:.4f}, expected {EXPECTED}")
    failures += [] if ok else [name]
sys.exit(1 if failures else 0)
