# Windows host build review

21 November 2026. Windows x64 is the existing release target. This review does
not change CP/M media, service ports, AUTH, the BYE drivers or the CPU model.

## Completed build work

`build_windows_tools.py` uses the existing Image Workbench LLVM-MinGW toolchain
to cross-compile cpmtools 2.23. The five tools are `cpmcp.exe`, `cpmls.exe`,
`cpmrm.exe`, `cpmchattr.exe` and `mkfs.cpm.exe`. The isolated source copy accepts
the explicit raw driver, opens disk images in binary mode, and honors the
launcher's `DISKDEFS` environment for package relocation. Original input source
is not modified. The exact patched source is retained beside the build log.

All five PE headers identify AMD64. The dependency audit permits only Windows
system CRT API sets and KERNEL32/MSVCRT; no installed POSIX runtime is required
for these tools. Their hashes and import lists are in `BUILD.json`.

Current local output: `build/windows-tools-x64-relocatable/`. Compilation and
static inspection do not establish runtime correctness. No complete Windows
RCP/M package exists yet.

## Host architecture decision

The existing launcher uses POSIX processes, file locks, file permissions,
randomness and atomic rename. The emulator uses POSIX console setup, poll,
sockets, signals and timing. Upstream z80pack's Windows instructions use WSL;
that would change this project's download/unpack/run contract.

Recommended: implement a native Windows host layer with the existing CPU and
guest service implementations. Keep the POSIX path working and share protocol
and guest logic. This is more implementation work than bundling a POSIX runtime,
but keeps the existing package contract and avoids adding a compatibility
runtime to the release. Do not silently substitute a different emulator.

| Area | Required Windows behavior |
| --- | --- |
| Console | Foreground sysop terminal, byte-correct input/output, restore console state on exit |
| Modem/transfer | WinSock nonblocking I/O, preserve direct/IP232 and transfer protocol semantics; do not treat 64-bit SOCKET values as POSIX int file descriptors |
| Timing | Monotonic time for deadlines and idle timer; preserve guest-visible ports |
| Single instance | Installation-specific lock held for the entire emulator lifetime; Windows process creation must not drop ownership |
| Initialization | OS randomness and private credential/disk permissions using Windows ACLs; chmod is not an ACL substitute |
| Driver selection | Stage and flush disk writes before Windows atomic replacement; preserve installed disk on failure |
| Paths | Relocatable package and directory names with spaces; define Unicode/path handling consistently |
| Packaging | Unchanged verified common payload, native host manifest, matching host source and notices |

Consequential implementation of this host layer awaits maintainer approval of
the approach under the project's engineering-review instructions.

## Qualification access

The existing Image Workbench Windows x64 QEMU VM and its monitor socket were
located. A read-only monitor status query from this session was denied with
`Operation not permitted`. The existing UTM guest-agent route also aborts when
launched in this session. These are current execution-access blockers, not
evidence that the Windows guest or the prior workflow is broken. No VM was
stopped, restarted, reconfigured or booted for this review.

Before claiming a Windows release, obtain unattended guest execution and result
retrieval, run the disk-tool byte round trips and relocation checks, and qualify
the complete extracted package for boot, HELP, caller access, archives, mounts,
RBBS, private first-start credentials, duplicate refusal, orderly shutdown and
restart preservation. Existing macOS results cannot stand in for this evidence.
