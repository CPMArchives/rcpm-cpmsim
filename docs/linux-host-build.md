# Linux x64 host packaging

Status: packaging source and transferable build kit prepared. Native Linux x64
compilation and live qualification have not been performed. The available local
Debian ISO and prior VM evidence are ARM64; UTM's control command aborts in the
current execution environment. This is not Linux x64 release evidence.

The Linux builder consumes the unchanged, verified common ZIP from
`build/release-runtime-separated/rcpm-common-candidate.zip`. It builds only the
host launcher, emulator and raw image tools. It does not rebuild guest programs,
require Microsoft/MicroPro toolchain inputs, or alter A:/I:/P:, GAMES, GUIDES,
AUTH or either BYE driver. Every common file must retain its original hash.

## Build on Linux x64

Use Python 3.9 or later, a C compiler and headers, make, binutils/readelf, and
ldd. No downloads or privileged installation occurs during the build itself.
With this checkout and the common archive available on the Linux host:

```sh
python3 build_linux_release.py --common /path/to/rcpm-common-candidate.zip --output build/linux
python3 check_release.py build/linux/rcpm-linux-x64-candidate.tar.gz --output build/linux-check
```

Both output directories must be new. For optional real tcpser/IP232 checks,
append `--tcpser /path/to/tcpser` to the check command. Omitting that argument
does not establish IP232 qualification on Linux.

The package runs with `./Start-RCPM.sh` after unpacking. It requires no Python,
tmux, compiler, or installed CP/M tools at runtime. Its shared historical
installation notes are supplemented by LINUX-README.txt. The host build records
compiler identity, actual dependencies, ELF architecture and required GLIBC
symbol versions in BUILD-HOST.json. These are measured build requirements, not
a claim that every Linux distribution has been tested. Qualification runs from
an extracted directory with spaces and a minimal PATH.

## Transferable kit

Prepare the kit on the existing Mac host without invoking a Linux compiler:

```sh
python3 build_linux_release.py --prepare-kit \
  --common build/release-runtime-separated/rcpm-common-candidate.zip \
  --output build/linux-x64-build-kit
```

The resulting `rcpm-linux-x64-build-kit.tar.gz` includes that exact common ZIP,
native build sources/patches, the portable checker, instructions and a file-hash
manifest. Transfer it to Linux x64, unpack it, and follow its README. The kit
contains build inputs; the native runtime archive is created on the Linux host.
Public redistribution remains subject to the unresolved component review.

## Checks completed here

Four focused checks cover common-file integrity, rejection of unrecorded files,
Linux tar launcher permissions/root discovery, and archive path rejection.
The real common payload and the existing macOS package are also checked through
the new extraction/manifest paths. The builder refuses a native Linux build on
the Mac host before creating output. These are packaging checks, not a native
Linux compiler run or a caller session. The macOS runtime candidate is unchanged.
