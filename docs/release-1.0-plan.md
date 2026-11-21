# RCP/M 1.0 release plan

Status: engineering candidate, not a cleared public release. Updated 21 November 2026.

## Release contract

Download, unpack, run one foreground CP/M session. Default raw TCP listener
127.0.0.1:4000, default CPU 4 MHz. No tmux or Python installation prerequisite.
The caller supplies the terminal client; virtual-modem mode is optional and has
its own compiled BYE driver. A:, I: and P: ship together, including the SIG/M
and CPMUG collections on P:. Common guest media and documentation are identical
across host packages; native launcher, emulator and image tools differ.

Retain the shared AUTH policy: drive defaults, DU overrides, private sysop
bypass, and caller execution requiring effective R, no W and actual file F4.
Do not redesign this policy during release stabilization.

## Work and acceptance gates

| Work | Evidence/status | Required before public 1.0 |
| --- | --- | --- |
| AUTH write-only lifecycle | Fixed; build/auth-writeonly-confirmed/result.json passes create/write/close, persisted contents, read-only close and NONE denial; rebuilt candidate driver hashes match | Extracted candidate live check passed; preserve exact driver identity |
| AUTH CLI and protection boundary | Direct/IP232, grants/revocation, inheritance, save/load, restart and RBBS tests recorded under docs/performance | Preserve results; repeat relevant checks after the close fix |
| Caller HELP | Nine I14 topics installed by fresh generation; build/caller-help-1.0-check/result.json passes every topic through HELPC as caller; rebuilt media readback passes | All nine shipped topics passed in the extracted candidate without reinstalling |
| Sysop guide | Detailed AUTH chapter already in SYSOP-GUIDE.DOC | Keep examples consistent with actual behavior and document limitations |
| Redistribution | [Component review](distribution-review.md) identifies the later CP/M grant and specific game terms; Microsoft/MicroPro build tools are separated from the new runtime package | Record later Z3PLUS release evidence; address the narrower new BYE core-derivative and preconfigured ZDE questions; retain utility and user-group collection notices |
| Native host packages | macOS ARM64 candidate rebuilt; [Windows x64 native candidate](windows-host-build.md) cross-compiled and statically audited; Linux x64 kit prepared with [pending native checks](linux-host-build.md) | Runtime-qualify Windows x64; build and qualify Linux x64; decide whether Intel Mac is included in 1.0 |
| Source consolidation | [Source baseline](source-baseline.md) pins 321 inputs; isolated rebuild reproduces nine guest outputs, all five media images and the emulator exactly | Preserve the baseline and qualified archive; changes to inputs or runtime behavior require affected checks |
| Frozen qualification | Boot, port conflict, RBBS, games, caller boundary and driver switching have prior reports | Qualify final extracted archives with minimal environment; target interruption during transfers and RBBS writes; verify recovery and no credential leakage |
| macOS distribution experience | Local unsigned candidate runs | Test actual downloaded archive/quarantine behavior and document supported startup steps |
| Release artifacts | Local candidate archives only | Versioned packages, checksums, notices, release notes, installation/sysop guides and explicit support matrix |

## Sequence

1. Fix the demonstrated AUTH close defect and add the missing caller HELP.
2. Review redistribution notices and native platform requirements while keeping
   the local engineering candidate usable. Do not publish around an unresolved
   distribution restriction. Contacting rights holders requires separate user
   authorization.
3. Consolidate source and build defaults into a reviewed baseline. Record which
   checks passed on which exact binaries; do not equate a local Mac run with
   Windows/Linux validation.
4. Build platform candidates from the same common payload, freeze them, and
   perform one proportionate final qualification pass. Retest only affected
   cases after any subsequent fix.
5. Publish 1.0 only after the release gates are satisfied and publication is
   authorized. Keep the local candidate label until then.

## Current candidate and qualification boundary

The current packaging profile is `build/release-runtime-separated/`. It
reconstructs offline/BUILD.dsk without M80, L80 and WM, and omits the original
stock cpm3-2.dsk from bundled sources. Builders still supply the pinned original
disk separately. DEVELOPMENT-MEDIA.json records the separation. The original
candidate below remains the exact historical live-qualification artifact.
The [separation checks](performance/development-separation-2026-11-21.json)
verify the four excluded files (including WM.HLP), all 21 retained development
files, absence of the unfiltered source disk, ZIP integrity and manifests.
All five runtime images, both drivers and all nine host files match the earlier
qualified candidate exactly; no repeated live run is required for this change.

`build/release-1.0-stabilization/rcpm-macos-arm64-candidate.zip` includes the
fixed `build/bye5-writeonly` drivers and all nine caller HELP topics. The common
archive and SHA256SUMS are beside it. `offline-qualification.json` records
verification of 467 common files and nine host files, exact driver hashes,
HELP readback, ZIP integrity and absence of installed credentials. Packaging
also verified every one of the 403 P: libraries against the preserved manifest.

The extracted-package live check passed in the operator's Terminal:
`build/release-1.0-live.9oZHiX/results/result.json`. It verifies direct TCP,
all nine shipped HELP topics without reinstalling, both public volumes, RBBS
entry, duplicate-process refusal, private credential records, real tcpser/IP232,
credential preservation and switching back to direct TCP. The earlier sandbox
socket refusal was an execution-environment limitation, not a package failure.
Further write-interruption and downloaded-quarantine qualification remain open.
The checker now prints stage and command progress during future runs.

## Deliberately outside 1.0

See [post-1.0 roadmap](roadmap.md): configurable CPU speed (default remains
4 MHz), additional curated CP/M-era BBS collections, and a reviewed caller
copy/temporary-upload service. Investigating remaining console overhead is
optional and does not justify increasing the default clock.

Games that require writes to the protected catalog are download/local-play
material. Universal game compatibility and persistent player storage are not
release requirements. Existing fixed launchers may prepare disposable WORK data.

## Evidence limits

A: RW preventing caller command loads is intentional, not a defect: writable
DUs cannot execute caller programs. SYS hides directory entries; it does not
provide access control. Native approved programs remain trusted code rather
than a hostile-code sandbox. Existing carrier-loss tests during Adventure input
do not establish crash safety at every RBBS or transfer write boundary.
