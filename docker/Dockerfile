# The environment students get online, on Binder and in a Codespace.
#
# It is not defined here. It is created from the environment file of the
# installation instructions, https://github.com/cmaurini/fenicsx-install, so
# that the online environment and the one on a student's laptop are the same
# environment, and stay the same as it changes.
#
#   docker build -f docker/Dockerfile -t m2fr:env .
#
# Published by CI as ghcr.io/cmaurini/m2-fracture-2026:env-0.11, and only
# after the notebooks have run in it.

FROM condaforge/miniforge3:26.7.2-0

ARG FENICSX_INSTALL_REF=main
ARG CONDA_ENV=fenicsx-0.11

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    UCX_TLS=tcp,self,sm \
    UCX_NET_DEVICES=lo

# VTK renders with OpenGL and PyVista needs a display: the notebooks skip
# plotting when PYVISTA_OFF_SCREEN is set, so the container is given a real X
# server by Xvfb rather than being put in off-screen mode.
#
# UCX above: MPICH's UCX layer tries to open any RDMA device it sees and
# aborts MPI_Init when it cannot. Confine it to loopback, as CI does on the
# Azure runners.
# adduser: the Ubuntu base underneath no longer carries it, and
# .binder/Dockerfile creates the unprivileged user Binder runs as with it.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl adduser \
      libgl1 libglx-mesa0 libosmesa6 libxrender1 libxcursor1 xvfb \
 && rm -rf /var/lib/apt/lists/*

# The environment file is kept in the image: tools/check_environment.py reads
# it back to check that what it promises is actually importable here.
RUN curl -sSfL -o /opt/environment.yml \
      "https://raw.githubusercontent.com/cmaurini/fenicsx-install/${FENICSX_INSTALL_REF}/environment.yml" \
 && cat /opt/environment.yml \
 && conda config --set channel_priority strict \
 && mamba env create -f /opt/environment.yml \
 && mamba install -n "${CONDA_ENV}" -y jupyterhub notebook \
 && mamba clean -afy

# Make the course environment the default one, so that the Jupyter server
# itself runs inside it and finds the kernel installed just below.
ENV PATH=/opt/conda/envs/fenicsx-0.11/bin:${PATH}

# The notebooks pin kernelspec.name = fenicsx-0.11. Without this they open on
# a kernel that does not exist.
RUN python -m ipykernel install --sys-prefix \
      --name fenicsx-0.11 --display-name "FEniCSx 0.11"

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/bin/bash"]
