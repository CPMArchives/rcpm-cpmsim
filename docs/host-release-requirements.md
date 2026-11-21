# Native host release requirements

Status on 21 November 2026. The package runs one foreground guest with a local
sysop console and a raw TCP listener. Python, tmux and an installed CP/M toolchain
are build-time conveniences, not package runtime requirements.

| Host | Existing implementation | Remaining qualification/build work |
| --- | --- | --- |
| macOS ARM64 | Native candidate passes extracted-package checks; runtime identity preserved through development-tool separation; deployment target 11.0 | Downloaded/quarantined archive startup and final write-interruption qualification |
| Linux x64 | [Native packager and transferable build kit](linux-host-build.md) prepared; common-payload integrity and portable extraction checks pass | Run native compilation, ELF/dependency audit and extracted-package live checks on a Linux x64 host; establish the supported distribution baseline |
| Linux ARM64 | Maintainer approved the existing Debian 13 KDE ARM64 guest; architecture support and read-only build media prepared/attached | Run the guest build/check runner; collect native ELF/dependency and direct/IP232 qualification evidence |
| Windows x64 | [Native host port](windows-host-build.md) approved and implemented; complete candidate cross-compiled, all PE/import audits and common/host archive hashes pass | Required suite PASS on Windows 11 ARM64 through x64 emulation, including restart and credentials; optional Windows IP232 and interrupted writes not tested |
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
