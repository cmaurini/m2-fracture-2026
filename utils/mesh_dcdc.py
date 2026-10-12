"""Computational geometry of the DCDC specimen.

The specimen is a prism 2W x 2L with a hole of radius R drilled at its centre.
It stands upright and carries a uniform compression sigma on its two end
faces. Two mode I cracks of length a leave the hole along the axis of
compression. The two mid-planes are planes of symmetry, so one quarter is
meshed: y along the compression, x across, the hole centred at the origin.
Lengths are normalised by R, so R = 1.

    python utils/mesh_dcdc.py --a 2.0 --plot figures/domain.pdf

Physical groups

    domain     the quarter
    crack      x = 0, R < y < R + a      -- free
    ligament   x = 0, y > R + a          -- u_x = 0 (symmetry)
    sym        y = 0, x > R              -- u_y = 0 (symmetry)
    end        y = L                     -- carries the compression
    side       x = W                     -- free
    hole       the quarter circle        -- free

With `a = 0` the crack line is not built and the ligament covers the whole of
x = 0: that mesh gives the hoop stress at the mouth of the hole, which fixes
the short crack limit of the geometric function.
"""
import argparse
import pathlib

import gmsh
import numpy as np

TAGS = {"sym": 1, "side": 2, "end": 3, "ligament": 4, "crack": 5, "hole": 6,
        "domain": 20}


def build(a=2.0, half_width=2.0, half_length=12.0, lc_far=0.15, lc_tip=None,
          lc_hole=None, refine_radius=None, coarsen=4.0, verbose=False):
    """Mesh the quarter specimen. Returns the crack length a."""
    W, L = half_width, half_length
    if not 0.0 <= a < L - 1.0:
        raise ValueError("the crack tip must stay inside the specimen")
    if W <= 1.0:
        raise ValueError("the hole must fit in the width")
    lc_tip = lc_tip if lc_tip else max(a / 40.0, 2.0e-3)
    lc_hole = lc_hole if lc_hole else min(lc_far, 0.06)
    # La zone raffinee ne doit pas depasser le ligament ni la largeur : sinon
    # le maillage fin est jete loin du fond et la singularite est mal vue.
    refine_radius = refine_radius if refine_radius else min(1.0, W / 2.0)

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1 if verbose else 0)
    gmsh.model.add("dcdc-quarter")
    occ = gmsh.model.occ

    P = lambda x, y, lc=lc_far: occ.addPoint(x, y, 0.0, lc)
    centre = P(0.0, 0.0)
    mouth, equator = P(0.0, 1.0, lc_tip), P(1.0, 0.0, lc_hole)
    end_r, end_l, side_b = P(W, L), P(0.0, L), P(W, 0.0)

    # Le contour est parcouru dans le sens direct : le bas d'abord, puis la
    # face libre, la face chargee, l'axe de fissuration, l'arc pour fermer.
    lines = {"sym": occ.addLine(equator, side_b),
             "side": occ.addLine(side_b, end_r),
             "end": occ.addLine(end_r, end_l)}
    if a > 0.0:
        tip = P(0.0, 1.0 + a, lc_tip)
        lines["ligament"] = occ.addLine(end_l, tip)
        lines["crack"] = occ.addLine(tip, mouth)
    else:
        tip = mouth
        lines["ligament"] = occ.addLine(end_l, mouth)
    lines["hole"] = occ.addCircleArc(mouth, centre, equator)

    surf = occ.addPlaneSurface([occ.addCurveLoop(list(lines.values()))])
    occ.synchronize()
    occ.remove([(0, centre)])                     # le centre n'est pas du bord
    occ.synchronize()

    for name, tag in lines.items():
        gmsh.model.addPhysicalGroup(1, [tag], tag=TAGS[name], name=name)
    gmsh.model.addPhysicalGroup(2, [surf], tag=TAGS["domain"], name="domain")

    # ------------------------------------------------------------------
    # Le maillage est GRADUE. Trois tailles : lc_tip au fond de fissure,
    # lc_hole sur le bord du trou, lc_far dans le champ proche, puis
    # coarsen * lc_far au loin. Sans la derniere, une eprouvette longue paie
    # son remplissage en entier a lc_far, et c'est lui qui domine le nombre
    # de degres de liberte des que L depasse quelques rayons : a a = 10R le
    # champ lointain est dix fois la zone qui porte la physique.
    #
    # Un champ Threshold est lineaire en distance entre DistMin et DistMax.
    # Pour qu'il passe par lc_far a la distance voulue tout en continuant a
    # grossir jusqu'a lc_coarse, on etend DistMax dans le meme rapport.
    lc_coarse = coarsen * lc_far

    def graded(dist_field, size_min, dist_min, size_at, dist_at):
        """Threshold from size_min at dist_min, through size_at at dist_at,
        up to lc_coarse."""
        if size_at > size_min:
            span = (dist_at - dist_min) * (lc_coarse - size_min) / (size_at - size_min)
        else:
            span = dist_at - dist_min
        t = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(t, "InField", dist_field)
        gmsh.model.mesh.field.setNumber(t, "SizeMin", size_min)
        gmsh.model.mesh.field.setNumber(t, "SizeMax", lc_coarse)
        gmsh.model.mesh.field.setNumber(t, "DistMin", dist_min)
        gmsh.model.mesh.field.setNumber(t, "DistMax", dist_min + span)
        return t

    fields = []
    d = gmsh.model.mesh.field.add("Distance")
    gmsh.model.mesh.field.setNumbers(d, "PointsList", [tip])
    fields.append(graded(d, lc_tip, 2.0 * lc_tip, lc_far, refine_radius))

    # Le bord du trou porte la contrainte circonferentielle qui pilote tout :
    # il est raffine meme quand le fond de fissure est loin.
    dh = gmsh.model.mesh.field.add("Distance")
    gmsh.model.mesh.field.setNumbers(dh, "CurvesList", [lines["hole"]])
    gmsh.model.mesh.field.setNumber(dh, "Sampling", 120)
    fields.append(graded(dh, lc_hole, 0.0, lc_far, 1.0))

    m = gmsh.model.mesh.field.add("Min")
    gmsh.model.mesh.field.setNumbers(m, "FieldsList", fields)
    gmsh.model.mesh.field.setAsBackgroundMesh(m)
    for opt in ("MeshSizeExtendFromBoundary", "MeshSizeFromPoints",
                "MeshSizeFromCurvature"):
        gmsh.option.setNumber(f"Mesh.{opt}", 0)
    gmsh.model.mesh.generate(2)
    return a


def triangles():
    tags, coord, _ = gmsh.model.mesh.getNodes()
    xy = coord.reshape(-1, 3)[:, :2]
    index = {int(t): i for i, t in enumerate(tags)}
    tri = []
    for etype, _, nodes in zip(*gmsh.model.mesh.getElements(2)):
        if etype == 2:
            tri = np.array([index[int(n)] for n in nodes]).reshape(-1, 3)
    return xy, tri


def plot(a, W, L, out):
    """Draw the quarter, its mesh and the boundary conditions."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xy, tri = triangles()
    h = 5.0
    fig, ax = plt.subplots(figsize=(max(1.7, h * (W + 1.2) / (L + 1.4)), h))
    ax.triplot(xy[:, 0], xy[:, 1], tri, lw=0.22, color="#4a6fa5", alpha=0.85)
    ax.plot([0, 0], [1.0, 1.0 + a], lw=2.6, color="#b03030")
    ax.plot([0, 0], [1.0 + a, L], lw=1.6, color="#1f4e79")
    ax.plot([1.0, W], [0, 0], lw=1.6, color="#1f4e79")
    for x in np.linspace(0.06 * W, 0.94 * W, 5):
        ax.annotate("", xy=(x, L - 0.42), xytext=(x, L + 0.30),
                    arrowprops=dict(arrowstyle="->", color="#1a7a3a", lw=1.2))
    ax.text(W / 2, L + 0.36, r"$\sigma$", color="#1a7a3a", fontsize=12,
            ha="center", va="bottom")
    ax.text(-0.10, 1.0 + a / 2, "crack, free", color="#b03030", fontsize=8,
            rotation=90, ha="right", va="center")
    ax.text(-0.10, (1.0 + a + L) / 2, r"ligament, $u_x=0$", color="#1f4e79",
            fontsize=8, rotation=90, ha="right", va="center")
    ax.text((1.0 + W) / 2, -0.10, r"$u_y=0$", color="#1f4e79", fontsize=8,
            ha="center", va="top")
    ax.set_ylim(-0.55, L + 0.75)
    ax.set_xlim(-0.30 * W, W + 0.12)
    ax.set_aspect("equal")
    ax.set_xlabel(r"$x/R$", fontsize=8)
    ax.set_ylabel(r"$y/R$", fontsize=8)
    ax.tick_params(labelsize=7)
    fig.tight_layout()
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    print(f"wrote {out}")


# ---------------------------------------------------------------- the tags

# Une couleur et une condition aux limites par groupe physique. C'est la seule
# table a lire pour savoir ce que le maillage porte : le notebook la trace.
# `domain` est le groupe de DIMENSION 2, celui des triangles : sans lui gmsh
# n'exporte aucun element de surface et le maillage arrive vide.
GROUPS = {
    "domain":   ("#4a6fa5", r"the quarter, $\mathrm{d}x$"),
    "crack":    ("#b03030", "free"),
    "ligament": ("#1f4e79", r"$u_x=0$"),
    "sym":      ("#3a8fb7", r"$u_y=0$"),
    "end":      ("#1a7a3a", r"$T=-\sigma\,e_y$"),
    "side":     ("#888888", "free"),
    "hole":     ("#c08a30", "free"),
}


def plot_tags(msh, facet_tags=None, cell_tags=None, ax=None, show_mesh=True,
              lw=2.8, zoom=None, legend=True, title=None, counts=True,
              legend_below=False):
    """Draw the mesh and colour every tagged element, of both dimensions.

    `msh`, `facet_tags` and `cell_tags` are what `gmshio.model_to_mesh`
    returns. The triangles of each cell group are filled, the segments of each
    facet group are drawn over them, and the legend carries the condition each
    group holds and how many elements it has. `zoom` is an (x0, x1, y0, y1)
    box.

    Both dimensions matter. The facet groups carry the boundary conditions;
    the cell group is what `dx` integrates over, and a mesh built without it
    reaches DOLFINx with no cell at all.
    """
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection, PolyCollection
    from dolfinx.mesh import entities_to_geometry

    if ax is None:
        _, ax = plt.subplots(figsize=(4.2, 7.0))

    x = msh.geometry.x[:, :2]
    tri = msh.geometry.dofmap.reshape(-1, 3)
    named = {v: k for k, v in TAGS.items()}

    # les triangles, groupe par groupe
    if cell_tags is not None:
        for tag in np.unique(cell_tags.values):
            name = named.get(int(tag), f"cells {int(tag)}")
            colour, label = GROUPS.get(name, ("#4a6fa5", ""))
            cells = cell_tags.indices[cell_tags.values == tag]
            ax.add_collection(PolyCollection(
                x[tri[cells]], facecolors=colour, edgecolors="none",
                alpha=0.30, zorder=0,
                label=_label(name, label, len(cells), "cells", counts)))

    if show_mesh:
        ax.triplot(x[:, 0], x[:, 1], tri, lw=0.32, color="#54749c",
                   alpha=0.95, zorder=1)

    # les segments de bord, groupe par groupe
    fdim = msh.topology.dim - 1
    if facet_tags is not None:
        for name, (colour, label) in GROUPS.items():
            if name == "domain":
                continue
            facets = facet_tags.find(TAGS[name])
            if len(facets) == 0:
                continue
            nodes = entities_to_geometry(msh, fdim, facets)
            ax.add_collection(LineCollection(
                x[nodes], colors=colour, linewidths=lw, zorder=3,
                capstyle="round",
                label=_label(name, label, len(facets), "facets", counts)))

    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_xlabel(r"$x/R$")
    ax.set_ylabel(r"$y/R$")
    if zoom is not None:
        ax.set_xlim(zoom[0], zoom[1])
        ax.set_ylim(zoom[2], zoom[3])
    if legend:
        if legend_below:
            ax.legend(fontsize=7.5, loc="upper center", ncol=2,
                      bbox_to_anchor=(0.5, -0.10), frameon=False)
        else:
            ax.legend(fontsize=7, loc="center right", frameon=True,
                      framealpha=0.94, edgecolor="none")
    if title:
        ax.set_title(title, fontsize=9)
    return ax


def _label(name, condition, n, kind, counts):
    """`crack - free, 24 facets`, the way the legend spells a group."""
    head = f"{name} — {condition}" if condition else name
    return f"{head}   [{n} {kind}]" if counts else head


# Ancien nom, garde parce que le notebook de 2026 s'en sert.
plot_facet_tags = plot_tags


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--a", type=float, default=2.0)
    p.add_argument("--W", type=float, default=2.0)
    p.add_argument("--L", type=float, default=12.0)
    p.add_argument("--lc", type=float, default=0.15)
    p.add_argument("--coarsen", type=float, default=4.0)
    p.add_argument("--plot", type=str, default=None)
    c = p.parse_args()
    build(a=c.a, half_width=c.W, half_length=c.L, lc_far=c.lc,
          coarsen=c.coarsen)
    n = len(gmsh.model.mesh.getNodes()[0])
    print(f"a/R = {c.a}, W/R = {c.W}, L/R = {c.L}: {n} nodes")
    if c.plot:
        plot(c.a, c.W, c.L, c.plot)
    gmsh.finalize()
