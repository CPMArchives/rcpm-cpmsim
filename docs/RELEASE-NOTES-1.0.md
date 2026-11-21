# RCP/M 1.0

A ready-to-run CP/M 3 remote system using Z3PLUS and BYE510, with one local
sysop console and one raw TCP caller. The default listener is 127.0.0.1:4000;
the emulated CPU runs at 4 MHz.

## Downloads and startup

- Apple Silicon Mac: extract the whole macOS ARM64 ZIP and start
  `Start-RCPM.command`. The tools are unsigned. See INSTALLATION.DOC for
  startup, networking and configuration; macOS 11 is the binary deployment
  target, not a claim that every macOS version was tested.
- Windows x64: extract the whole Windows ZIP into a writable local NTFS folder
  and start `Start-RCPM.cmd`. Qualified on Windows 11 ARM64 build 26300 through
  Windows x64 emulation; native x64 hardware was not separately tested.
- The common ZIP contains shared media and source for builders; it is not a
  standalone runnable host package. Linux and Intel Mac are not qualified 1.0
  downloads.

Runtime needs no Python, tmux, Homebrew, WSL, compiler or installed CP/M tools.
Python is used only by optional qualification scripts and source build tools.

## Included system

- AUTH drive/user-area permissions with live private sysop administration,
  persistent policy, and approved caller program loading.
- Nine caller HELP topics and detailed installation/sysop guides.
- 310 SIG/M and 93 CPMUG archive libraries, preserved with their notices.
- Mountable GAMES and documentation-only GUIDES volumes.
- Private RBBS storage and fresh board credentials generated on first start,
  preserved across process restarts. Generated SYSOP.DOC is private.
- ZDE configured for ANSI/VT100-compatible sysop use; complete original archive
  and notices retained.
- Separate direct-TCP and IP232 BYE drivers. Direct TCP is the default.

## Validation and limits

macOS direct TCP and real tcpser/IP232 qualification passed. The required
Windows suite passed host probes, binary disk-tool round trips, duplicate
refusal, caller login, all nine HELP topics, archives, both public volumes,
RBBS entry, private credentials, orderly shutdown and restart preservation.
Windows IP232 was not tested and is not a qualified Windows feature in 1.0.

One caller is supported. The service speaks raw TCP, not Telnet. AUTH is a
CP/M command/file policy, not a hostile-native-code sandbox. Games retain their
individual compatibility limits; archive presence does not promise online play.
Actual browser-download/quarantine startup and forced interruption during
transfer or RBBS writes were not qualified. Abrupt termination can lose writes;
this release makes no crash-recovery guarantee.
Stop the guest before backup or host image maintenance. Use the documented
local SYSUTLS:BYEBYE shutdown sequence rather than closing the terminal window.

## Notices and source

This is a collection of independently licensed components, not a uniformly
public-domain or open-source work. Preserve NOTICES/, source/ and archive member
notices. Component-specific noncommercial/no-fee restrictions remain applicable.
Microsoft M80/L80 and MicroPro WM development copies are excluded from the new
offline build disk; builders supply pinned external inputs when required.

The maintainer accepted proceeding with the modified BYE510 and configured ZDE
while preserving the original notices and the documented permission ambiguity.
That decision is not represented as a new grant from their original authors.
Z3PLUS's later free-release evidence and the accepted SIG/M/CPMUG collection
basis are recorded in source/rcpm/docs/distribution-review.md.

The original project contributions have no separately declared blanket license;
no license for them is inferred from third-party component licenses.
