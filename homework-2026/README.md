# Homework 2026: the DCDC test

[`hw2026.pdf`](hw2026.pdf) is the subject.

[`hw2026.ipynb`](hw2026.ipynb) is the starting notebook of the homework. It
meshes one quarter of the DCDC specimen, solves the elastic problem, plots the
opening and the stress along the crack line, and computes $G$ by the G-theta
method. The blanks, marked `TO FILL IN`, are modelling decisions: a few
values, or the body of a function whose signature and docstring are given. The
DOLFINx code around them is written.

1. the two symmetry conditions: the component each blocks, and its value;
2. Hooke's law, `sigma(e)`, in plane strain;
3. the two components of the traction on the end face;
4. `potential_energy(uh)`: the form of the potential energy, and the energy of
   the whole specimen from that of the quarter;
5. `crack_opening(uh, points)`: the opening, from $u_x$ on the symmetry plane;
6. `g_theta(uh, r_in, r_out)`: the virtual advance, the Eshelby tensor, the
   G-theta form, and the $G$ of one tip.

Run it from this folder, like the other notebooks (see the
[main README](../README.md)), or
[on Binder](https://mybinder.org/v2/gh/cmaurini/m2-fracture-2026/HEAD?labpath=homework-2026%2Fhw2026.ipynb),
where nothing is saved.

Take $W=2R$ in Question 2, and the $W/R$ of your group, from the parameter
sheet, in Questions 3 and 4.

The notebook imports two modules from [`utils/`](../utils/):

| Module | Contents |
|---|---|
| [`mesh_dcdc.py`](../utils/mesh_dcdc.py) | `build`, the graded mesh of the quarter; `plot_tags`, its tagged elements. |
| [`solve_dcdc.py`](../utils/solve_dcdc.py) | `solve`, then `g_theta`, `k_from_cod` and `g_finite_difference`: the three methods of Question 2, and the curve $G(a)$ of Questions 3 and 4. The published fits `fett_2005`, `pallares_2009`, `he_1995`. `long_enough(a, W)`, the default length $L$. |

`solve_dcdc.py` has none of the blanks, so your `g_theta` and its must agree
to the digit the mesh allows. From this folder,

```bash
python ../utils/solve_dcdc.py --a 2.0 --W 2.0
```

prints $\hat g=GE/(\sigma^2R)$ at $a=2R$, $W=2R$ by the three methods, next to
the published fits.
