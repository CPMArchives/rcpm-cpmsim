#!/bin/zsh
set -eu
task_root=${0:A:h}
export PYTHONPYCACHEPREFIX="$task_root/build/pycache"
exec python3 "$task_root/qualify_install_chat46.py" "$@"
