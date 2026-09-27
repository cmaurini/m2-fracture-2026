# mybinder.org.
#
# All the work is in the base image, built by CI from the environment file of
# the installation instructions (see docker/Dockerfile). A Binder launch is
# then a pull and the few lines below, not a conda solve.
#
# The base image also provides ENTRYPOINT, PATH and DISPLAY.

FROM ghcr.io/cmaurini/m2-fracture-2026:env-0.11

# Binder runs the notebooks as an unprivileged user with uid 1000, and the
# files must belong to that user for the student to be able to edit them.
ARG NB_USER=jovyan
ARG NB_UID=1000
ENV USER=${NB_USER} \
    NB_UID=${NB_UID} \
    HOME=/home/${NB_USER}

RUN adduser --disabled-password --gecos "Default user" --uid ${NB_UID} ${NB_USER}

# repo2docker builds from the repository root even though this file lives in
# .binder/, so this copies the whole repository.
COPY . ${HOME}
RUN chown -R ${NB_UID} ${HOME}

USER ${NB_USER}
WORKDIR ${HOME}
