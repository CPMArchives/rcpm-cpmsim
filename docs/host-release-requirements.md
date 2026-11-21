# Native host release requirements

Status on 21 November 2026. The package runs one foreground guest with a local
sysop console and a raw TCP listener. Python, tmux and an installed CP/M toolchain
are build-time conveniences, not package runtime requirements.

| Host | Existing implementation | Remaining qualification/build work |
| --- | --- | --- |
| macOS ARM64 | Native C launcher, cpmsim and raw cpmtools; deployment target 11.0; package built locally | Extracted candidate live checks, downloaded/quarantined archive startup, supported startup instructions |
| Linux x64 | Launcher has `/proc/self/exe` path discovery; host runtime and image tools use POSIX interfaces | Build all native files on Linux, add platform packaging, inspect dependencies and qualify on the declared minimum distribution |
| Windows x64 | No native release launcher/backend has been established | Resolve POSIX socket, terminal, process, file locking and randomness dependencies; select and document a native Windows runtime approach, then build/package/qualify it |
| macOS Intel | No qualified package | Inclusion in 1.0 remains a scope decision; build and test if included |

Do not rename the macOS package or merely substitute an emulator executable and
call that a Windows/Linux build. The bundled launcher and image tools are also
host executables. A Windows implementation must preserve disk ownership,
private first-start secrets, atomic driver selection and foreground console
behavior. Introducing WSL or an externally installed compatibility runtime would
change the download/unpack/run contract and requires a scope decision.

Every platform package must use the same common payload, including AUTH, both
BYE drivers, caller HELP, A:/I:/P: and GAMES/GUIDES. Record native dependencies,
minimum OS, binary hashes and exact common-payload identity separately.

Qualify a fresh extracted archive with a minimal environment: first-start
initialization, no shipped credentials, caller access, HELP, archive browsing,
mounts, RBBS, duplicate-process refusal, shutdown/restart and preservation of
credentials. Qualify optional IP232 using a real tcpser build on that host.
Existing macOS reports are not Windows/Linux evidence. Interruption during
transfer and RBBS writes remains part of the final frozen-release check.
