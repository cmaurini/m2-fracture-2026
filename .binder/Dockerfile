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

# condaforge/miniforge3 is built on Ubuntu, and the Ubuntu base image already
# holds uid 1000, with a user named `ubuntu`: adduser stops there on
# "The UID 1000 is already in use." Hand that uid over to ${NB_USER}. Whoever
# holds it is looked up rather than assumed, because repo2docker run by hand
# builds with the uid of the person running it, which is usually free.
RUN existing=$(getent passwd ${NB_UID} | cut -d: -f1); \
    if [ -n "${existing}" ] && [ "${existing}" != root ]; then \
        userdel "${existing}" && rm -rf "/home/${existing}"; \
    fi \
 && adduser --disabled-password --gecos "Default user" --uid ${NB_UID} ${NB_USER}

# repo2docker builds from the repository root even though this file lives in
# .binder/, so this copies the whole repository.
COPY . ${HOME}
RUN chown -R ${NB_UID} ${HOME}

USER ${NB_USER}
WORKDIR ${HOME}
