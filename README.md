# Computational notebooks — Fracture Mechanics 2026

[![Run the notebooks](https://github.com/cmaurini/m2-fracture-2026/actions/workflows/test-notebooks.yml/badge.svg)](https://github.com/cmaurini/m2-fracture-2026/actions/workflows/test-notebooks.yml)

Finite element notebooks for the joint Master course in fracture mechanics of
École Nationale des Ponts et Chaussées, Institut Polytechnique de Paris and
Sorbonne Université (MU5MES02 / MEC_53642_EP). They run on
[DOLFINx](https://github.com/FEniCS/dolfinx) **0.11.0**.

## Install

The notebooks need DOLFINx 0.11, gmsh, PyVista, scifem and JupyterLab. Follow
the instructions and run the self-test at

**https://github.com/cmaurini/fenicsx-install**

— conda on Linux and macOS, WSL2 + conda on Windows. They produce a conda
environment named `fenicsx-0.11`, which is the one used here.

## Run

Register the environment once as a Jupyter kernel:

```bash
conda activate fenicsx-0.11
python -m ipykernel install --user --name fenicsx-0.11 --display-name "FEniCSx 0.11"
```

`make kernel` does the same. The notebooks ask for that kernel by name, so from
then on they open on the right environment by themselves, whichever environment
JupyterLab was started from.

```bash
git clone https://github.com/cmaurini/m2-fracture-2026.git
cd m2-fracture-2026
jupyter lab
```

Open `linear-elasticity/00-Mesh.ipynb` and run the cells. The kernel shown in
the top right corner should read *FEniCSx 0.11*. The notebooks import their
helper modules from `utils/` through a relative path, so run them from their
own directory — opening them in JupyterLab does this for you.

## Contents

| Notebook | What it does |
|---|---|
| [`linear-elasticity/00-Mesh.ipynb`](linear-elasticity/00-Mesh.ipynb) | Builds the mesh of a cracked slab with gmsh, refines it at the crack tip, imports it into DOLFINx, plots it with PyVista and saves it to XDMF. |
| [`linear-elasticity/01-LinearElasticity.ipynb`](linear-elasticity/01-LinearElasticity.ipynb) | Solves plane-stress linear elasticity on that mesh, computes the potential energy and the von Mises stress, plots the deformed configuration, and plots the crack opening and $\sigma_{yy}$ along the line $y=0$. |

The geometry is half of an elastic slab with a straight crack, the half being
taken by symmetry:

![the domain](linear-elasticity/domain.png)

Helper modules, imported by the notebooks:

| Module | Contents |
|---|---|
| [`utils/meshes.py`](utils/meshes.py) | `generate_mesh_with_crack`, the mesh of `00-Mesh` as a function. |
| [`utils/plots.py`](utils/plots.py) | `warp_plot_2d`, a PyVista plot of a field on the deformed mesh. |
| [`utils/elastic_solver.py`](utils/elastic_solver.py) | `solve_elasticity`, the whole of `01-LinearElasticity` as a function, returning the displacement, the potential energy and the stress. |

Evaluating a field at a set of points — a plot along a line, a value at the
crack tip — is done with
[`scifem.evaluate_function`](https://scientificcomputing.github.io/scifem/),
which is part of the installed environment. It works in serial and in parallel,
and replaces the hand-written point-evaluation helpers of earlier versions of
these notebooks.

Results are written to `linear-elasticity/output/`, in a form
[ParaView](https://www.paraview.org/) reads.

## Check that it works

```bash
conda activate fenicsx-0.11
make test
```

This executes both notebooks and checks the run: no cell raised, PyVista drew
its figures, and the computed potential energies are the expected ones. The
same two steps run in CI on Linux and macOS, in the conda environment of the
installation instructions and in the `ghcr.io/fenics/dolfinx/lab:v0.11.0`
image, every Monday morning and on every push.

## Further material

- The full notebook collection of the [NEWFRAC](https://www.newfrac.eu) network,
  covering LEFM, plasticity, phase-field and dynamics:
  https://github.com/newfrac/fenicsx-fracture
- The DOLFINx tutorial by Jørgen S. Dokken: https://jsdokken.com/dolfinx-tutorial/
- FEniCS documentation: https://docs.fenicsproject.org/

## Provenance and license

Derived from [newfrac/fenicsx-fracture](https://github.com/newfrac/fenicsx-fracture),
notebooks `notebooks/linear-elasticity/00-Mesh.ipynb` and
`01-LinearElasticity.ipynb` with their helper modules, verified against
DOLFINx 0.11.0.

Authors: Corrado Maurini (Sorbonne Université) and Laura De Lorenzis (ETH Zürich).

MIT, see [LICENSE](LICENSE).
