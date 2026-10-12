"""Plane elasticity on the quarter DCDC specimen, with DOLFINx.

The quarter built by `mesh_dcdc.py` is solved at E = 1, R = 1 and a
compressive end stress sigma = 1, so every output below is the dimensionless
quantity of Question 1.

    python utils/solve_dcdc.py --a 2.0 --W 2.0 --L 12.0

prints the potential energy and the energy release rate by the three methods
of Question 2, next to the handbook values.

The specimen stands upright: the compression is along y, the two cracks leave
the hole along y, and the ligament carries u_x = 0.

Four traps, all of them silent:

* the mesh carries a QUARTER of the specimen, and the specimen has TWO crack
  tips. The potential energy reported here is that of the whole specimen,
  4 x the quarter; the energy release rate of ONE tip is then
  -(1/2) dPi/da, since both cracks grow together;
* the G-theta domain integral is taken over the half-disc x > 0 that the
  quarter holds, so it gives G/2 and is doubled;
* the theta ramp must die before it reaches the hole behind the tip, the free
  face x = W beside it and the loaded face y = L ahead of it. Its radius is
  therefore measured on min(a, W, L - R - a), not on a alone;
* the specimen must be LONG. At L - R - a of the order of W the end face is
  felt and the answer is not the DCDC one: see `long_enough` below.
"""
import argparse

import numpy as np
import ufl
from mpi4py import MPI
from petsc4py.PETSc import ScalarType

import dolfinx.fem as fem
import dolfinx.fem.petsc  # noqa: F401
import dolfinx.geometry as dgeom
from dolfinx.io import gmsh as gmshio

import gmsh
import mesh_dcdc

CP = dict(c0=0.3156, c1=0.7350, c2=0.0346,      # Pallares et al. 2009, eq. (3)
          c3=-0.4093, c4=0.3794, c5=-0.0257)

LIGAMENT = 8.0          # ce que « assez long » veut dire : L = R + a + 8R


def long_enough(a, half_width=2.0):
    """The half-length beyond which the end face is no longer felt.

    Three half-widths of ligament ahead of the tip are enough; eight hole
    radii is what the correction uses, and it is comfortable for W <= 2.5R.
    """
    return 1.0 + a + max(LIGAMENT, 3.0 * half_width)


def elastic_moduli(nu, plane_strain=True, E=1.0):
    mu = E / (2 * (1 + nu))
    lmbda = E * nu / ((1 + nu) * (1 - 2 * nu))
    if not plane_strain:                                    # plane stress
        lmbda = 2 * mu * lmbda / (lmbda + 2 * mu)
    e_eff = E / (1 - nu**2) if plane_strain else E          # E' of Irwin
    return mu, lmbda, e_eff


def solve(a, half_width=2.0, half_length=None, nu=0.2, plane_strain=True,
          degree=2, lc_far=0.15, lc_tip=None, refine_radius=None,
          coarsen=4.0):
    """Solve the quarter at sigma = 1. Energies are for the WHOLE specimen.

    `lc_far` is the element size in the near field, `coarsen * lc_far` the one
    far from the hole and the tip. Grading is what makes a long specimen
    affordable: at a = 10R it divides the number of degrees of freedom by four
    and changes G in the fourth digit.
    """
    if half_length is None:
        half_length = long_enough(a, half_width)
    mesh_dcdc.build(a=a, half_width=half_width, half_length=half_length,
                    lc_far=lc_far, lc_tip=lc_tip, refine_radius=refine_radius,
                    coarsen=coarsen)
    data = gmshio.model_to_mesh(gmsh.model, MPI.COMM_SELF, 0, gdim=2)
    msh, facets = data.mesh, data.facet_tags
    gmsh.finalize()
    T = mesh_dcdc.TAGS

    V = fem.functionspace(msh, ("Lagrange", degree, (2,)))
    u, v = ufl.TrialFunction(V), ufl.TestFunction(V)
    mu, lmbda, e_eff = elastic_moduli(nu, plane_strain)

    def sigma(w):
        return 2 * mu * ufl.sym(ufl.grad(w)) + lmbda * ufl.div(w) * ufl.Identity(2)

    fdim = msh.topology.dim - 1
    dofs_x = fem.locate_dofs_topological(V.sub(0), fdim, facets.find(T["ligament"]))
    dofs_y = fem.locate_dofs_topological(V.sub(1), fdim, facets.find(T["sym"]))
    bcs = [fem.dirichletbc(ScalarType(0.0), dofs_x, V.sub(0)),
           fem.dirichletbc(ScalarType(0.0), dofs_y, V.sub(1))]

    traction = fem.Constant(msh, ScalarType((0.0, -1.0)))   # sigma = 1
    ds = ufl.Measure("ds", domain=msh, subdomain_data=facets)
    bil = ufl.inner(sigma(u), ufl.sym(ufl.grad(v))) * ufl.dx
    lin = ufl.inner(traction, v) * ds(T["end"])

    problem = fem.petsc.LinearProblem(
        bil, lin, bcs=bcs, petsc_options_prefix="hw2026_",
        petsc_options={"ksp_type": "preonly", "pc_type": "lu"})
    uh = problem.solve()

    work = fem.assemble_scalar(fem.form(ufl.inner(traction, uh) * ds(T["end"])))
    end_u = fem.assemble_scalar(fem.form(-uh[1] * ds(T["end"])))
    return {"mesh": msh, "facets": facets, "u": uh, "a": a, "nu": nu,
            "W": half_width, "L": half_length, "E_eff": e_eff, "sigma": sigma,
            "dofs": V.dofmap.index_map.size_global * 2,
            "energy": 4 * (-0.5 * work),          # whole specimen
            "shortening": 2 * end_u / half_width}  # mean, whole specimen


# ---------------------------------------------------------------- the three methods

def potential_energy(a, **kw):
    return solve(a, **kw)["energy"]


def g_finite_difference(a, da=None, **kw):
    """G of ONE tip from a centred difference of the potential energy.

    Both cracks grow together, so dPi/da counts the two tips and G is half of
    the slope. The two solutions share one length L: the default L grows with
    a, and its change would enter the difference through the energy of the
    uniform compression, at about four times G.
    """
    da = da if da else max(0.005, 0.01 * a)
    kw.setdefault("half_length", long_enough(a + da, kw.get("half_width", 2.0)))
    pm = potential_energy(a - da, **kw)
    pp = potential_energy(a + da, **kw)
    return -0.5 * (pp - pm) / (2.0 * da)


def crack_opening(out, r_min=0.05, r_max=0.30, n=60):
    """The crack opening behind the tip, and the K_I it implies point by point.

    The opening of the crack is twice u_x on the symmetry plane x = 0, and the
    mode I asymptotics give  delta(r) = (8 K_I / E') sqrt(r / 2 pi), so

        K_app(r) = E' delta(r) / [ 8 sqrt(r / 2 pi) ]

    tends to K_I as r goes to zero. `r_min` and `r_max` are fractions of the
    crack length. Returns (r, delta, K_app).
    """
    a, msh, uh = out["a"], out["mesh"], out["u"]
    r = np.linspace(r_min * a, r_max * a, n)
    pts = np.zeros((n, 3)); pts[:, 1] = 1.0 + a - r
    tree = dgeom.bb_tree(msh, msh.topology.dim)
    cand = dgeom.compute_collisions_points(tree, pts)
    coll = dgeom.compute_colliding_cells(msh, cand, pts)
    keep = [i for i in range(n) if len(coll.links(i))]
    cells = [coll.links(i)[0] for i in keep]
    delta = 2.0 * np.abs(uh.eval(pts[keep], cells)[:, 0])
    r = r[keep]
    return r, delta, out["E_eff"] * delta / (8 * np.sqrt(r / (2 * np.pi)))


def k_from_cod(out, r_min=0.05, r_max=0.30):
    """K_I as the r -> 0 intercept of a straight line through K_app(r)."""
    r, _, kapp = crack_opening(out, r_min=r_min, r_max=r_max)
    return np.polyfit(r, kapp, 1)[1]


def g_theta(out, r_in=None, r_out=None):
    """G of one tip by the G-theta method, the virtual advance being along +y."""
    a, msh, uh, sigma = out["a"], out["mesh"], out["u"], out["sigma"]
    # ⚠ Le rayon se mesure sur la PLUS COURTE des trois distances du fond au
    #   bord : le trou derriere lui (a), la face libre x = W a cote, la face
    #   chargee y = L devant. Une rampe qui deborde l'une d'elles laisse theta
    #   non nul sur un bord ou il doit s'annuler : l'integrale de domaine perd
    #   son independance de chemin et rend un nombre faux sans rien signaler.
    span = min(a, out["W"], out["L"] - 1.0 - a)
    r_in = r_in if r_in else 0.25 * span
    r_out = r_out if r_out else 0.75 * span

    Vs = fem.functionspace(msh, ("Lagrange", 1))
    th = fem.Function(Vs)
    th.interpolate(lambda x: np.clip(
        (r_out - np.sqrt(x[0] ** 2 + (x[1] - 1.0 - a) ** 2)) / (r_out - r_in),
        0.0, 1.0))
    theta = ufl.as_vector((0.0, th))                 # along the crack path

    s = sigma(uh)
    W = 0.5 * ufl.inner(s, ufl.sym(ufl.grad(uh)))
    eshelby = W * ufl.Identity(2) - ufl.dot(ufl.grad(uh).T, s)
    form = -ufl.inner(eshelby, ufl.grad(theta)) * ufl.dx
    return 2.0 * fem.assemble_scalar(fem.form(form))  # the half-disc x > 0


def hoop_at_mouth(out):
    """sigma_xx at the mouth of the hole, (0, R), in units of the applied sigma.

    Read on the uncracked quarter, where nothing is singular. It is the hoop
    stress at the point of the hole that lies on the axis of compression: the
    stress concentration k_t that drives the initiation, and with it the short
    crack limit of the geometric function. The stress of a P2 displacement is
    discontinuous, so it is projected on the continuous P1 space before being
    read at the node: a value taken from one adjacent element alone moves by a
    few percent with the mesh.
    """
    msh, uh, sigma = out["mesh"], out["u"], out["sigma"]
    Vs = fem.functionspace(msh, ("Lagrange", 1))
    p, q = ufl.TrialFunction(Vs), ufl.TestFunction(Vs)
    problem = fem.petsc.LinearProblem(
        p * q * ufl.dx, sigma(uh)[0, 0] * q * ufl.dx, bcs=[],
        petsc_options_prefix="hw2026_proj_",
        petsc_options={"ksp_type": "preonly", "pc_type": "lu"})
    sxx = problem.solve()
    pts = np.zeros((1, 3)); pts[0, 1] = 1.0
    tree = dgeom.bb_tree(msh, msh.topology.dim)
    cand = dgeom.compute_collisions_points(tree, pts)
    coll = dgeom.compute_colliding_cells(msh, cand, pts)
    return float(sxx.eval(pts, [coll.links(0)[0]])[0])


# ---------------------------------------------------------------- handbook fits
# All three are written as  K_I = sigma sqrt(pi R) F(alpha, chi),  with
# alpha = a/R the crack length counted from the edge of the hole and
# chi = W/R the half-width. They differ only by the coefficients of 1/F,
# which is affine in alpha in every one of them.

def he_1995(alpha, chi):
    """He, Turner & Evans, Acta Metall. 43 (1995). Fitted for 2 < chi < 4."""
    return 1.0 / (chi + (0.235 * chi - 0.259) * np.asarray(alpha, dtype=float))


def fett_2005(alpha, chi):
    """Fett & Rizzi, FZKA 7094 (2005), eq. (2.3). Same range, better fit."""
    return 1.0 / (-0.37 + 1.116 * chi
                  + (0.216 * chi - 0.1575) * np.asarray(alpha, dtype=float))


def pallares_2009(alpha, chi):
    """Pallares et al., Int. J. Fract. 156 (2009), eq. (3).

    Quadratic in chi, fitted on 2.5 < chi < 5 and valid for chi < alpha, i.e.
    for cracks longer than the half-width. ⚠ The slope multiplies a/R, NOT
    a/W: written with a/W the long crack branch comes out a factor chi too
    flat.
    """
    x, al = float(chi), np.asarray(alpha, dtype=float)
    return 1.0 / ((CP["c0"] + CP["c1"] * x + CP["c2"] * x**2)
                  + (CP["c3"] + CP["c4"] * x + CP["c5"] * x**2) * al)


def g_handbook(alpha, chi, nu=0.2, plane_strain=True, fit=fett_2005):
    """g_hat = G E / (sigma^2 R) from one of the fits above."""
    f = 1 - nu**2 if plane_strain else 1.0
    return f * np.pi * fit(alpha, chi) ** 2


def g_short(alpha, kt=1.0, nu=0.2, plane_strain=True):
    """The short crack limit: an edge crack of depth a in the hoop stress kt.

    K_I -> 1.1215 kt sigma sqrt(pi a), so g_hat -> pi (1-nu^2) 1.1215^2 kt^2
    alpha, a straight line through the origin.
    """
    f = 1 - nu**2 if plane_strain else 1.0
    return f * np.pi * (1.1215 * kt) ** 2 * np.asarray(alpha, dtype=float)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--a", type=float, default=2.0)
    p.add_argument("--W", type=float, default=2.0)
    p.add_argument("--L", type=float, default=None)
    p.add_argument("--nu", type=float, default=0.2)
    p.add_argument("--lc", type=float, default=0.15)
    p.add_argument("--ratio", type=float, default=40.0)
    p.add_argument("--coarsen", type=float, default=4.0)
    p.add_argument("--plane-stress", action="store_true")
    c = p.parse_args()
    L = c.L if c.L else long_enough(c.a, c.W)
    kw = dict(half_width=c.W, half_length=L, nu=c.nu, lc_far=c.lc,
              lc_tip=c.a / c.ratio, plane_strain=not c.plane_stress,
              coarsen=c.coarsen)

    out = solve(c.a, **kw)
    kI = k_from_cod(out)
    gt = g_theta(out)
    gfd = g_finite_difference(c.a, **kw)
    ps = not c.plane_stress
    print(f"a/R = {c.a}, W/R = {c.W}, L/R = {L}, nu = {c.nu}, "
          f"{out['dofs']} dofs")
    print(f"  potential energy   Pi = {out['energy']: .6e}")
    print(f"  end shortening        = {out['shortening']: .6e}")
    print(f"  g, crack opening      = {kI**2 / out['E_eff']: .6f}"
          f"   (K_I/(sigma sqrt(pi R)) = {kI / np.sqrt(np.pi): .5f})")
    print(f"  g, finite difference  = {gfd: .6f}")
    print(f"  g, G-theta            = {gt: .6f}")
    for name, fit in (("He 1995", he_1995), ("Fett 2005", fett_2005),
                      ("Pallares 2009", pallares_2009)):
        g = g_handbook(c.a, c.W, nu=c.nu, plane_strain=ps, fit=fit)
        print(f"  g, {name:<14s}   = {g: .6f}   (F = {fit(c.a, c.W): .5f})")
