#!/bin/sh
set -eu
cd -P "$(dirname "$0")"
if [ ! -f check_release.py ]; then
  qualification_checkout="$HOME/.codex/.chatgpt-projects/g-p-6a682f002be881918281554d644daf48/rcpm-cpmsim"
  if [ ! -f "$qualification_checkout/check_release.py" ]; then
    echo "Cannot find the RCP/M source checkout. Run this script from the rcpm-cpmsim checkout." >&2
    exit 1
  fi
  cd -P "$qualification_checkout"
fi
if [ ! -f build/release-runtime-separated/rcpm-macos-arm64-candidate.zip ]; then
  echo "The release candidate is missing from $PWD/build/release-runtime-separated." >&2
  exit 1
fi
mkdir -p build
qualification_output="$(mktemp -d "$PWD/build/release-1.0-live.XXXXXX")"
# check_release.py requires a new output path beneath the retained run folder.
set -- python3 check_release.py \
  build/release-runtime-separated/rcpm-macos-arm64-candidate.zip \
  --output "$qualification_output/results"
if [ -x /tmp/rcpm-tcpser-review/tcpser ]; then
  set -- "$@" --tcpser /tmp/rcpm-tcpser-review/tcpser
else
  echo "tcpser is unavailable; this run will qualify direct TCP only."
fi
"$@"
echo "Qualification report: $qualification_output/results/result.json"
