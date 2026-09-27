"""Evaluation of a finite element function at arbitrary points.

`evaluate_function` below is a copy of `scifem.evaluate_function`, kept here so
that the notebooks do not depend on scifem being installed. It works in serial
and in parallel: each process evaluates the points that fall in the cells it
owns, and the values are then gathered on every process.

Adapted from https://github.com/scientificcomputing/scifem (MIT).
"""

import numpy as np
from mpi4py import MPI

import dolfinx.geometry


def evaluate_function(u, points, broadcast=True):
    """Evaluate the function `u` at `points`.

    Args:
        u: the `dolfinx.fem.Function` to evaluate.
        points: array of shape `(num_points, dim)`, with `dim` at most 3.
            Missing columns are taken to be zero, so for a 2-D mesh the points
            can be given either as `(num_points, 2)` or as `(num_points, 3)`.
        broadcast: if True, every process gets the values at every point. This
            is a collective call, so all processes must reach it. If False,
            each process gets only the values of the points it owns.

    Returns:
        Array of shape `(num_points, value_size)` if `broadcast` is True, the
        rows being in the order of `points`. A discontinuous function evaluated
        on a facet shared by two cells may be given either value.
    """
    mesh = u.function_space.mesh
    u.x.scatter_forward()
    comm = mesh.comm

    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2:
        raise ValueError(
            f"expected points of shape (num_points, dim), got {points.shape}"
        )
    num_points = points.shape[0]

    # dolfinx works with three coordinates per point; pad with zeros
    missing = 3 - points.shape[1]
    if missing < 0:
        raise ValueError(f"points have {points.shape[1]} columns, at most 3 expected")
    if missing > 0:
        points = np.hstack((points, np.zeros((num_points, missing))))

    # the cells whose bounding box contains each point, then those that
    # really do contain it
    tree = dolfinx.geometry.bb_tree(mesh, mesh.topology.dim)
    candidates = dolfinx.geometry.compute_collisions_points(tree, points)
    colliding = dolfinx.geometry.compute_colliding_cells(mesh, candidates, points)

    # keep the points for which this process found a cell, one cell each
    found = np.flatnonzero(colliding.offsets[1:] - colliding.offsets[:-1])
    cells = colliding.array[colliding.offsets[found]]
    values = u.eval(points[found], cells)

    if not broadcast:
        return values

    # -inf on the points this process does not own, so that the maximum over
    # the processes is the value found by whoever owns the point
    value_size = u.function_space.value_size
    gathered = np.full((num_points, value_size), -np.inf, dtype=np.float64)
    gathered[found, :] = values
    comm.Allreduce(MPI.IN_PLACE, gathered, op=MPI.MAX)

    missed = np.flatnonzero(np.isinf(gathered[:, 0]))
    if missed.size > 0:
        raise ValueError(
            f"{missed.size} point(s) lie outside the mesh, the first being "
            f"{points[missed[0], : mesh.geometry.dim]}"
        )
    return gathered
