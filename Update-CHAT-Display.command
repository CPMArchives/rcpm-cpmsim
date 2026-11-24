#!/bin/zsh
set -eu
task_root=${0:A:h}
task_instance=${1:-$HOME/CPM/RCPM}
export PYTHONPYCACHEPREFIX="$task_root/build/pycache"
print "Updating CHAT display in: $task_instance"
exec python3 "$task_root/install_chat46.py" --instance "$task_instance" --build "$task_root/guest/chat46" --tools "$task_instance/runtime"
