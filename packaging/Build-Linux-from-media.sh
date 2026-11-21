#!/bin/bash
set -euo pipefail
cd -P "$(dirname "$0")"
if [ "$(uname -s)" != Linux ]; then
  echo "Run this command inside the Debian Linux guest." >&2
  exit 1
fi
mkdir -p "$HOME/rcpm-release-builds"
work="$(mktemp -d "$HOME/rcpm-release-builds/kit.XXXXXX")"
tar -xzf rcpm-linux-arm64-build-kit.tar.gz -C "$work"
exec bash "$work/RCPM-linux-arm64-build-kit/Build-and-Check.sh"
