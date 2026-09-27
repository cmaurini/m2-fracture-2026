#!/bin/bash
# Start the X server PyVista draws on, then run whatever the container was
# given. BinderHub replaces the command with jupyterhub-singleuser, so the
# command must be passed through rather than ignored.
set -e

Xvfb "${DISPLAY:-:99}" -screen 0 1920x1080x24 >/dev/null 2>&1 &

for _ in $(seq 1 50); do
    [ -e "/tmp/.X11-unix/X${DISPLAY#:}" ] && break
    sleep 0.1
done

exec "$@"
