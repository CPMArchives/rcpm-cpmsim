# RCP/M 1.0 — macOS ARM64 and Windows x64 release preparation

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

Qualified Mac host: Apple Silicon macOS. Its earlier extracted-package
live pass covers direct/IP232 operation, caller login, all HELP topics, archive
browsing, public mounts, RBBS, duplicate refusal and credential preservation.
A new extracted-archive direct-TCP check also passed on 21 November 2026,
including minimal PATH, relocation, all HELP topics, both public mounts, RBBS,
private credentials, duplicate refusal and orderly shutdown. See
`docs/performance/final-macos-runtime-2026-11-21.json`.
The current archive excludes external Microsoft/MicroPro development binaries;
all five runtime disk images, both BYE drivers and native host binaries retain
the earlier qualified identity.

Windows x64 has a complete native cross-built candidate and automated test
runner. The required automated suite now passes on Windows 11 ARM64 through x64
emulation, including restart and credential preservation. Windows can be
included in the release scope on that documented evidence; native x64 Windows
hardware and optional Windows IP232 were not tested. Linux remains unqualified.

Known boundaries: one caller; raw TCP rather than Telnet; unsigned Mac tools;
no promise that every archived game runs remotely; no hostile-code sandbox for
approved native CP/M programs. Keep SYSOP.DOC private and back up the whole
installation while stopped. Do not advertise the aggregate as unrestricted
public-domain software.

Z3PLUS and configured ZDE are retained; the maintainer accepts proceeding with
the modified BYE510 while preserving its notices and the documented uncertainty.
These three items no longer require replacement or a wrapper rewrite.

Before publication: finish remaining specific utility notice decisions,
finish the narrow Mac download-startup/write-interruption gates or explicitly
revise their acceptance criteria, and review the prepared macOS/Windows publication set.
The full distribution review is docs/distribution-review.md. Original notices
and corresponding source remain in each candidate. No rights-holder contact,
public tag, release or upload has been made by this staging step.

## Staged artifacts

`build/release-1.0-final/` contains versioned macOS ARM64, Windows x64 and
common ZIPs, SHA256SUMS, release notes and ASSEMBLY-RECEIPT.json. The assembler
verifies both original candidate manifests, identical shared media, and unchanged
runtime binaries, launchers and guest images before creating new manifests.
Documentation, source snapshots, the Windows qualification runner and status
metadata are refreshed. The Windows evidence is explicitly transcribed from
the operator's passing v4 screenshot; it is not the original guest JSON.
