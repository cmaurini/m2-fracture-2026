import numpy as np
import dolfinx.plot as plot
import pyvista


def warp_plot_2d(
    u, cell_field=None, field_name="Field", factor=1.0, backend="none", **kwargs
):
    # "ipyvtklink", "panel", "ipygany", "static", "pythreejs", "none"
    msh = u.function_space.mesh

    # Create plotter and pyvista grid
    plotter = pyvista.Plotter()

    topology, cell_types, geometry = plot.vtk_mesh(msh)
    grid = pyvista.UnstructuredGrid(topology, cell_types, geometry)

    # Attach vector values to grid and warp grid by vector
    values = np.zeros((geometry.shape[0], 3), dtype=np.float64)
    values[:, : len(u)] = u.x.array.real.reshape((geometry.shape[0], len(u)))
    grid["u"] = values
    warped_grid = grid.warp_by_vector("u", factor=factor)
    if cell_field is not None:
        warped_grid.cell_data[field_name] = cell_field.x.array
        warped_grid.set_active_scalars(field_name)
    plotter.add_mesh(warped_grid, **kwargs)
    # plotter.show_axes()
    plotter.camera_position = "xy"

    return plotter
