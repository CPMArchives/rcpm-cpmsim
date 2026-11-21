# Native Windows x64 host build

21 November 2026. Maintainer approved the native Windows host port. A complete
engineering candidate is cross-compiled; **manual Windows runtime checks have now passed on Windows 11 ARM64 running
the x64 application under emulation**. The required automated Windows suite has now passed on that VM.
This is not a cleared public release.

## Build and package

Use the existing Image Workbench LLVM-MinGW toolchain on macOS. No download or
Windows VM is required to compile. From this checkout:

```sh
python3 build_windows_release.py \
  --common build/release-runtime-separated/rcpm-common-candidate.zip \
  --toolchain ../cpmimage-feasibility/windows-runtime/llvm-mingw-20261104-ucrt-macos-universal \
  --output build/windows-x64-release
```

The output directory must be new. The builder verifies the common ZIP, builds
all Windows executables, audits PE architecture and imports, assembles a ZIP,
and writes SHA256SUMS. It rejects any changed common file. The exact isolated
native source/build logs remain in the output. Corresponding common source,
project patches, host adapters and build scripts are included in the package.

The ZIP has `Start-RCPM.cmd`, `runtime/rcpm.exe`, `runtime/cpmsim.exe`, the five
native cpmtools executables, the unchanged common payload, and a separate
`qualification/` directory. Running RCP/M requires no Python, WSL, Cygwin,
compiler or installed CP/M tools. Python is needed only for the optional
qualification script. Windows 10 1903 or newer is a provisional API baseline,
not an OS compatibility claim established by testing. Use a writable local
NTFS directory; private ACL support is mandatory.

## Implementation and preserved boundaries

The existing Z80/8080 implementation and shared RCP/M modem/transfer services
are built with Windows host adapters. CP/M media, AUTH, both BYE drivers, caller
HELP and guest service ports are unchanged. POSIX source paths are not modified.
The isolated Windows build disables legacy Unix pipes and optional z80pack TCP
serial boards; the common configuration already disables these boards. The
RCP/M direct/IP232 modem ports 70-74 remain enabled.

| Area | Windows implementation |
| --- | --- |
| Console | Win32 console events, key repeat and ANSI arrow keys; binary byte streams; restore console modes after normal child exit |
| Sockets | WinSock nonblocking sockets behind integer table indices; full SOCKET handles stay in the table; explicit errno translation |
| Endpoint ownership | Exclusive Windows listener bind; no Windows SO_REUSEADDR port stealing |
| Timing | QueryPerformanceCounter clock; native waitable timers for CPU pacing; service the existing 10 ms timer interrupt on the CPU thread at clock/I/O accounting boundaries |
| Single instance | Exclusive-sharing installation lock handle inherited by the emulator; parent waits and a kill-on-close job prevents orphan guests |
| Credentials | BCrypt randomness; protected current-account-only ACLs for new files, generated credentials, initialized I: and state/upload directories |
| Publication | Stage and flush driver/disk writes before same-volume replacement; native no-replace hard links for committed uploads |
| Paths | Wide Win32 process/path APIs, CRT-compatible argument quoting and embedded UTF-8 application manifests |
| Disk tools | Explicit raw driver, binary image opens and package-relative DISKDEFS lookup |

Only Windows system DLLs/CRT API sets are permitted by the import audit. The
package does not contain a POSIX compatibility runtime. Closing the console or
forcibly terminating its process is not orderly shutdown; use local
`SYSUTLS:BYEBYE`. Windows may delay rebinding an exclusive endpoint while an old
connection remains active; the native restart check must cover this.

Native probes are included for binary I/O, owner-only ACLs, non-overwriting
publication, monotonic time, timer delivery, sockets, exclusive binding, and
inheritance of the installation lease after its parent closes its own handle.
These probes are compiled but have not been executed on Windows.

## Qualification

`check_windows_release.py` validates/extracts the ZIP into a directory with
spaces and Unicode, then runs in a separate hidden Windows console and produces
`result.json`. Its console input is delivered through Win32 console events;
there is no manual keyboard capture or command-typing sequence. It exercises:

- Native host probes and disk-tool binary round trips.
- Relocation, manifests, no shipped credentials and retained development media.
- Native launcher configuration, default port where free, boot and caller login.
- Duplicate-instance refusal, all nine HELP topics, archives, public mounts and RBBS.
- Credential ACLs and equality with the guest password record.
- Orderly shutdown and restart preservation.

Run in an existing Windows test environment with Python:

```text
python check_windows_release.py rcpm-windows-x64-candidate.zip --output NEW_DIRECTORY
```

The report records actual Windows build and native/process machine types, so an
x64 process running under ARM64 emulation is distinguishable from native x64
Windows evidence. Optional real-tcpser/IP232 and final write-interruption
qualification remain separate. No runtime pass is inferred from compilation.

This session's unattended VM access remains blocked: UTM guest-agent commands
abort with exit 134; connecting to the existing Image Workbench Windows x64
QEMU monitor is denied with `Operation not permitted`. Even local host socket
binds are denied, preventing the existing modem socket regression suite. No VM
has been stopped, restarted or reconfigured for this port, and no Windows live
result has been fabricated. Other session permissions must be resolved before
executing and retrieving the qualification result.

## API references

- [Windows handle inheritance](https://learn.microsoft.com/en-us/windows/win32/sysinfo/handle-inheritance).
- [Windows file sharing modes](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilea).
- [WinSock exclusive endpoint ownership](https://learn.microsoft.com/en-us/windows/win32/winsock/using-so-reuseaddr-and-so-exclusiveaddruse).
- [Windows console input](https://learn.microsoft.com/en-us/windows/console/low-level-console-input-functions).

## Manual Windows runtime evidence — 21 November 2026

The maintainer ran the unchanged x64 candidate under Windows 11 ARM64, build
26300, in UTM. Screenshots and direct reports establish boot to modem-ready,
loopback caller login, system/public archive directory access, HELP index,
GAMES/GUIDES listing, GAMES mounting and Adventure-file listing, RBBS entry,
socket-disconnect recovery, reconnect, and normal BYE logoff returning ready.
The earlier runner passed native host probes, disk-tool round trips and all
21 retained development-file checks before timing out waiting for modem-ready.
Its screen logger replayed rows on cursor movement; manual startup subsequently
succeeded. A revised runner allows 180 seconds for boot, reports progress and
records changed console rows. That revised runner has not yet passed on Windows.

These are Windows ARM64 emulation results, not native x64 Windows-machine
evidence. No all-topics HELP, GUIDES read, process-restart credential persistence,
complete duplicate-instance, real IP232 or interrupted-write pass is claimed.
See [manual evidence](performance/windows-manual-2026-11-21.json).

## Required automated suite PASS — 21 November 2026

The maintainer ran RCPMManualTests-v4 against the unchanged candidate and
provided the complete PASS report (exit 0). Host probes, disk tools, retained
development files, duplicate refusal, direct boot/login, all nine HELP topics,
archives, both public mounts, RBBS, credential ACL/record consistency, orderly
shutdown, restart/login, preserved credentials and final shutdown passed.
This supersedes earlier pending/failed-run status above. The corrected runner
baselines the existing screen before each launch, excluding stale readiness
text; its runtime pass is now established.

Evidence is [the transcribed report](performance/windows-runtime-2026-11-21.json),
explicitly distinguished from a retrieved original guest file. The application
is x64 running under Windows 11 ARM64 emulation (build 26300). Optional Windows
IP232 and interrupted-write behavior remain outside this suite's result.
