# RCP/M 1.0 — proposed macOS-first release

Publication draft; not a public release or a redistribution clearance.

RCP/M provides one foreground CP/M 3 session with a local sysop console and
one raw TCP caller. The default endpoint is 127.0.0.1:4000 at 4 MHz. The package
requires no Python, tmux, Homebrew, compiler or installed CP/M tools.

The common media includes A:, private I: system/board/work areas, the 310 SIG/M
and 93 CPMUG libraries on P:, and mountable GAMES/GUIDES volumes. AUTH provides
one default-deny caller permission policy and live sysop administration. Caller
execution requires read access, no write access, and file F4 approval. Nine
caller HELP topics and detailed installation/sysop documentation are supplied.
Fresh private board credentials are generated on first start and preserved on
restart. Optional IP232 uses a separate compiled BYE driver.

Proposed first stable host: Apple Silicon macOS. Its earlier extracted-package
live pass covers direct/IP232 operation, caller login, all HELP topics, archive
browsing, public mounts, RBBS, duplicate refusal and credential preservation.
The current archive excludes external Microsoft/MicroPro development binaries;
all five runtime disk images, both BYE drivers and native host binaries retain
the earlier qualified identity.

Windows x64 has a complete native cross-built candidate and automated test
runner, but no Windows runtime pass. Linux candidates remain unqualified.
Neither belongs in a stable supported-platform claim yet.

Known boundaries: one caller; raw TCP rather than Telnet; unsigned Mac tools;
no promise that every archived game runs remotely; no hostile-code sandbox for
approved native CP/M programs. Keep SYSOP.DOC private and back up the whole
installation while stopped. Do not advertise the aggregate as unrestricted
public-domain software.

Before publication: resolve the existing third-party distribution decision,
finish the narrow Mac download-startup/write-interruption gates or explicitly
revise their acceptance criteria, and approve the Mac-first platform scope.
The full distribution review is docs/distribution-review.md. Original notices
and corresponding source remain in each candidate. No rights-holder contact,
public tag, release or upload has been made by this staging step.

## Staged artifacts

`build/public-release-review/` contains exact copies of the existing Mac and
common ZIPs, SHA256SUMS, these draft notes and RELEASE-GATES.json. No runtime
bytes were rebuilt or changed. Windows is deliberately excluded from this
proposed stable asset set until its native runtime qualification passes.
