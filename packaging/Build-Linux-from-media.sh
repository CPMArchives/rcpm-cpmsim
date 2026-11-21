#!/bin/bash
set -euo pipefail
cd -P "$(dirname "$0")"
if [ "$(uname -s)" != Linux ]; then
  echo "Run this command inside the Debian Linux guest." >&2
  exit 1
fi
kit_archive=""
for candidate in rcpm-linux-arm64-build-kit.tar.gz rcpm-linux-arm64-build-kit.gz RCPM-LINUX-ARM64-BUILD-KIT.TAR.GZ RCPM-LINUX-ARM64-BUILD-KIT.GZ; do
  if [ -f "$candidate" ]; then
    kit_archive="$candidate"
    break
  fi
done
if [ -z "$kit_archive" ]; then
  echo "Cannot find the ARM64 build-kit archive beside this script." >&2
  exit 1
fi
build_root="${RCPM_BUILD_ROOT:-$HOME/rcpm-release-builds}"
mkdir -p "$build_root"
work="$(mktemp -d "$build_root/kit.XXXXXX")"
tar -xzf "$kit_archive" -C "$work"
exec bash "$work/RCPM-linux-arm64-build-kit/Build-and-Check.sh"
