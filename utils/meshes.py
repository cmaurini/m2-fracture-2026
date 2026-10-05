"""Meshes of a slab with a straight crack, built with gmsh.

Only the upper half of the slab is meshed: the crack lies on the symmetry
line `y = 0`, from `x = 0` to `x = Lcrack`, and the crack tip is the point
`(Lcrack, 0)`.

The mesh is refined around the tip, with one of two size fields:

`graded=True` (the default)
    `h(r) = min(lc, max(h_min, r / grade))`, `r` being the distance to the
    tip.  Away from the floor `h_min` the mesh is self-similar, `h / r`
    constant, which is the structure the `r**(1/2)` displacement field asks
    for.  `dist_min` and `dist_max` are then unused.

`graded=False`
    The `Threshold` field of the gmsh tutorials: a uniform disc of size
    `h_min` for `r < dist_min`, then a linear ramp up to `lc` reached at
    `r = dist_max`.

In both cases `h_min = lc / refinement_ratio`.  On the energy of the mode-I
problem of `01-LinearElasticity`, the graded field with quadratic elements
reaches a given accuracy with about twenty times fewer degrees of freedom
than the threshold field with linear elements, and converges twice as fast
in the number of degrees of freedom.  For a convergence study, let
`refinement_ratio` grow like `1 / lc`: keeping it fixed leaves the error
dominated by the elements touching the tip.

The names of the physical groups are `FACET_TAGS`, `CELL_TAGS` and
`POINT_TAGS` below; the meshtags returned carry those integer values.
"""

import gmsh
from mpi4py import MPI
from dolfinx.io import gmsh as gmshio


FACET_TAGS = {"left": 1, "right": 2, "top": 3, "crack": 4, "bottom_no_crack": 5}
CELL_TAGS = {"all": 20}
POINT_TAGS = {"crack_tip": 10}


def generate_mesh_with_crack(
    Lx=1.0,
    Ly=0.5,
    Lcrack=0.3,
    lc=0.1,
    dist_min=0.1,
    dist_max=0.3,
    refinement_ratio=10,
    graded=True,
    grade=5.0,
    gdim=2,
    verbosity=4,
):
    """Mesh the half-slab `(0, Lx) x (0, Ly)` cracked over `(0, Lcrack)`.

    Args:
        Lx, Ly: the sides of the half-slab.
        Lcrack: the crack length, `0 < Lcrack < Lx`.
        lc: the element size away from the tip.
        dist_min, dist_max: radii of the uniform disc and of the transition
            zone of the threshold field; used only if `graded` is False.
        refinement_ratio: the element size at the tip is `lc` divided by it.
        graded: use the graded size field rather than the threshold one.
        grade: the slope `r / h` of the graded field; larger is finer.
        gdim: the geometric dimension the mesh is imported with.
        verbosity: the gmsh verbosity, from 0 (silent) to 99.

    Returns:
        `(mesh, cell_tags, facet_tags)`, the tags being `dolfinx` meshtags.
    """
    if not 0.0 < Lcrack < Lx:
        raise ValueError(f"expected 0 < Lcrack < Lx, got Lcrack={Lcrack}, Lx={Lx}")
    if refinement_ratio < 1.0:
        raise ValueError(f"expected refinement_ratio >= 1, got {refinement_ratio}")
    if graded:
        if grade <= 0.0:
            raise ValueError(f"expected grade > 0, got {grade}")
    elif not 0.0 <= dist_min < dist_max:
        raise ValueError(
            f"expected 0 <= dist_min < dist_max, got {dist_min} and {dist_max}"
        )

    mesh_comm = MPI.COMM_WORLD
    model_rank = 0
    h_min = lc / refinement_ratio

    # leave the session as we found it: the caller may own it
    owns_gmsh = not gmsh.isInitialized()
    if owns_gmsh:
        gmsh.initialize()

    try:
        # every process needs a model to hand to `model_to_mesh`, but only
        # `model_rank` builds the geometry and meshes it
        model = gmsh.model()
        if mesh_comm.rank == model_rank:
            model.add("Rectangle")
            model.setCurrent("Rectangle")
            # Create the points
            p1 = model.geo.addPoint(0.0, 0.0, 0, lc)
            p2 = model.geo.addPoint(Lcrack, 0.0, 0, lc)
            p3 = model.geo.addPoint(Lx, 0, 0, lc)
            p4 = model.geo.addPoint(Lx, Ly, 0, lc)
            p5 = model.geo.addPoint(0, Ly, 0, lc)
            # Create the lines
            l1 = model.geo.addLine(p1, p2, tag=FACET_TAGS["crack"])
            l2 = model.geo.addLine(p2, p3, tag=FACET_TAGS["bottom_no_crack"])
            l3 = model.geo.addLine(p3, p4, tag=FACET_TAGS["right"])
            l4 = model.geo.addLine(p4, p5, tag=FACET_TAGS["top"])
            l5 = model.geo.addLine(p5, p1, tag=FACET_TAGS["left"])
            # Create the surface
            cloop1 = model.geo.addCurveLoop([l1, l2, l3, l4, l5])
            surface = model.geo.addPlaneSurface([cloop1])

            # Define the mesh size and fields for the mesh refinement
            model.mesh.field.add("Distance", 1)
            model.mesh.field.setNumbers(1, "PointsList", [p2])
            if graded:
                #  Size
                #   lc -                        /---------------
                #                              /
                # SizeMin -o------------------/
                #          |                  |
                #          0        grade * SizeMin        Distance
                model.mesh.field.add("MathEval", 2)
                model.mesh.field.setString(
                    2, "F", f"Min({lc}, Max({h_min}, F1 / {grade}))"
                )
            else:
                # SizeMax -                   / ------------------
                #                            /
                # SizeMin -o----------------/
                #          |                |  |
                #        Point        DistMin   DistMax
                model.mesh.field.add("Threshold", 2)
                model.mesh.field.setNumber(2, "InField", 1)
                model.mesh.field.setNumber(2, "SizeMin", h_min)
                model.mesh.field.setNumber(2, "SizeMax", lc)
                model.mesh.field.setNumber(2, "DistMin", dist_min)
                model.mesh.field.setNumber(2, "DistMax", dist_max)
            model.mesh.field.setAsBackgroundMesh(2)
            # the field alone sets the size: the sizes carried by the points
            # of the geometry would otherwise compete with it
            gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
            gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
            gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
            model.geo.synchronize()

            # Assign the physical groups, before meshing
            model.addPhysicalGroup(2, [surface], tag=CELL_TAGS["all"])
            model.setPhysicalName(2, CELL_TAGS["all"], "Rectangle surface")
            for name, tag in FACET_TAGS.items():
                model.addPhysicalGroup(1, [tag], tag=tag)
                model.setPhysicalName(1, tag, name)
            # the tip as a group of its own, to locate it without a
            # geometrical search
            model.addPhysicalGroup(0, [p2], tag=POINT_TAGS["crack_tip"])
            model.setPhysicalName(0, POINT_TAGS["crack_tip"], "crack_tip")

            gmsh.option.setNumber("General.Verbosity", verbosity)
            model.mesh.generate(gdim)

        # collective: the mesh is built on `model_rank` and distributed to all
        msh, cell_tags, facet_tags, *_ = gmshio.model_to_mesh(
            model, mesh_comm, model_rank, gdim=gdim
        )
    finally:
        if owns_gmsh:
            gmsh.finalize()

    msh.name = "rectangle"
    cell_tags.name = f"{msh.name}_cells"
    facet_tags.name = f"{msh.name}_facets"
    return msh, cell_tags, facet_tags
