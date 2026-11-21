#!/bin/zsh
# One persistent CP/M/BYE machine supplies both the listener and console.
set -eu
script_path=${0:A}
repository=${script_path:h}
export PATH="$repository/build/cpmtools/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
exec python3 "$repository/shared_launcher.py" "$@"
