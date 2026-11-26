# Linux x64 and ARM64 host packaging

Status: Linux ARM64 and x64 release packages are now built and qualified for
direct TCP. Both ran the extracted-package release checks in Debian 12 Docker
containers on an ARM64 host. x64 compilation and execution used CPU emulation;
native x64 hardware and optional IP232 were not tested. Reports and downloads
are attached to release v1.2.1. Docker startup and persistence instructions are
in [docker.md](docker.md).

The Linux builder consumes the unchanged, verified common ZIP from
`build/release-runtime-separated/rcpm-common-candidate.zip`. It builds only the
host launcher, emulator and raw image tools. It does not rebuild guest programs,
require Microsoft/MicroPro toolchain inputs, or alter A:/I:/P:, GAMES, GUIDES,
AUTH or either BYE driver. Every common file must retain its original hash.

## Build on Linux x64

The same commands apply on Linux ARM64; native architecture is detected and
checked against the ELF headers. The archive/root name becomes linux-arm64
instead of linux-x64. A binary with the wrong ELF machine is rejected.

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
Component-specific terms and prior release decisions remain applicable.

For ARM64, pass `--kit-architecture arm64` with `--prepare-kit`. The kit includes
Build-and-Check.sh: one native build and direct-TCP qualification pass, with
progress and logs under a fresh ~/rcpm-release-builds/run.* directory. Set
RCPM_TCPSER to an existing compatible executable to include optional IP232.

## Historical Debian guest handoff (superseded by Docker qualification)

`build/rcpm-linux-arm64-build.iso`, labeled RCPMBUILD, was attached to the
running Debian guest's previously empty CD/DVD drive. It contains the ARM64 kit
and Build-RCPM.sh, copied from packaging/Build-Linux-from-media.sh. The media
is read-only; build output goes into the guest user's home directory. Opening
the CD folder in a guest terminal and running `bash ./Build-RCPM.sh` starts the
complete build/check pass and prints the package and result.json paths.

Automated guest execution is blocked in this session: SSH returns Operation
not permitted, utmctl aborts, and the guest console is not reliably exposed by
the available UI interface. Attaching the ISO is verified; guest execution and
native build/check results remain pending. No VM restart, permission change or
security-setting change was made.

## Earlier packaging checks

Six focused checks cover common-file integrity, rejection of unrecorded files,
Linux tar launcher permissions/root discovery, and archive path rejection.
The added ARM64 cases cover architecture selection and rejection of x64 ELF
headers for an ARM64 package. These parser tests do not establish native builds.
The real common payload and the existing macOS package are also checked through
the new extraction/manifest paths. The builder refuses a native Linux build on
the Mac host before creating output. These are packaging checks, not a native
Linux compiler run or a caller session. The macOS runtime candidate is unchanged.
