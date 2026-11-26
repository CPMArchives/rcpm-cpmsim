#!/bin/sh
set -eu
if [ ! -e /data/.rcpm-installed ]; then
    if [ -n "$(ls -A /data)" ]; then
        echo 'Refusing to initialize nonempty /data without .rcpm-installed' >&2
        exit 1
    fi
    cp -a /opt/rcpm-seed/. /data/
    touch /data/.rcpm-installed
fi
exec /data/runtime/rcpm --address 0.0.0.0 "$@"
