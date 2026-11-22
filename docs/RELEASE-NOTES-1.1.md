# RCP/M 1.1

RCP/M turns a modern computer into a classic remote CP/M system: browse historic
software libraries, read documentation, play compatible games and use the RBBS
bulletin board. It runs CP/M 3, Z3PLUS and BYE510 on z80pack, with one caller and
a local sysop console. Direct raw TCP defaults to 127.0.0.1:4000 at 4 MHz.

## New in 1.1

- P: now supports named, swappable 512 MiB archive images, independently of
  the 4 MB J: collections. Use MOUNT P: /L and MOUNT P: NAME.
- MOUNT validates exact image geometry before replacing either drive, flushes
  buffered writes, and can restore each drive's startup image with /DEFAULT.
- New caller-accessible NDSCAN.COM scans all 16 user areas of a selected drive
  and refreshes its named directories from extensionless -NAME marker files.
  MOUNT chains to NDSCAN after successful swaps. NDSCAN preserves AUTH policy
  and executable approvals; it does not write the disk image.
- J: and P: retain the same AUTH rules: callers are read-only by default, with
  deliberate sysop overrides supported.
- A cleaner installation layout groups images, documents, metadata and uploads.
  README.txt and private SYSOP.DOC remain at the top level.
- Optional collections remain independent downloads in the Software catalog,
  including BOSKUG, GAMES, GUIDES, INFOCOM, MODERNIF and SCOTT.

## Directory layout

| Location | Contents |
| --- | --- |
| disks/ | Active and startup disk images |
| disks/library/ | Optional J: collections |
| disks/library/archives/ | Optional P: collections |
| disks/library/offline/ | Development media, excluded from MOUNT catalogs |
| docs/ | Installation, sysop guide, disk reference and component notices |
| metadata/ | Package manifest, inventories, provenance and checksums |
| uploads/inbox/ | Completed uploads and saved caller messages |
| uploads/staging/ | Transfers in progress |
| runtime/ | Native executable tools |
| source/ | Source code and build instructions |
| state/ | Persistent local initialization state |

The Software collection ZIPs retain their existing internal volumes/ paths.
Copy the extracted .dsk files into disks/library/ on 1.1.

## Install or upgrade

Mac: extract the complete macOS ARM64 ZIP and launch Start-RCPM.command.
The tools are unsigned; read docs/INSTALLATION.DOC for macOS startup details.
Windows: extract the complete Windows x64 ZIP into a writable local NTFS folder
and launch Start-RCPM.cmd. See the validation limits below.
Neither platform needs Python or an installed compiler for ordinary operation.
The common ZIP is for builders and is not a standalone runnable host package.

For an existing installation, stop cleanly through SYSUTLS:BYEBYE and keep a
backup of the entire directory. Do not overwrite existing disks/, SYSOP.DOC,
RCPM.CONF or state/ with fresh-install files: they contain local data and
credentials. The source tree includes migrate_layout.py for reorganizing a
stopped Mac installation using a matching rebuilt layout-2 runtime. That script
changes host paths and runtimes; it does not install new guest programs. The
new P: MOUNT and NDSCAN features also require the matching 1.1 guest media.
Install 1.1 in a separate directory for a clean evaluation of all new features.

## Validation and limits

The reorganized Mac package passed startup, caller login, all nine HELP topics,
archive access, J: mounting, RBBS entry, private credentials, duplicate-instance
refusal and orderly shutdown. Separate live CP/M checks passed independent
J:/P: swaps, all 16 user areas, wrong-geometry rejection, NDSCAN name refresh,
denied-area handling and unchanged caller executable approvals. Unit checks and
fresh package construction also passed. Evidence is included under
source/rcpm/docs/performance/.

Windows x64 1.1 is cross-compiled and its PE imports are audited. Its changed
runtime and layout have NOT repeated Windows live qualification. The successful
Windows 11 ARM64/x64-emulation qualification belongs to 1.0 and is not claimed
for these rebuilt 1.1 binaries. The Windows 1.1 download is provided for testing.
Windows IP232, native x64 hardware, Linux and Intel Mac remain unqualified.
Mac IP232 passed on 1.0 but was not repeated for 1.1.

One caller is supported. The service speaks raw TCP, not Telnet. AUTH is a CP/M
command/file policy, not a sandbox for hostile native code. Archive availability
is not a promise that every program runs online. Browser-download/quarantine
startup and forced interruption during transfer/RBBS writes were not qualified.
Stop RCP/M before host disk maintenance or backup; abrupt termination can lose
writes. No crash-recovery guarantee is made.

## Notices and source

Component-specific terms continue to apply. Preserve docs/NOTICES/, source/
and notices within archive members. No uniform public-domain or open-source
license is asserted for the collection. Noncommercial/no-fee terms remain
applicable where specified.

The maintainer's accepted decisions for SIG/M, CPMUG, later Z3PLUS release
evidence, configured ZDE and modified BYE510 remain recorded in
source/rcpm/docs/distribution-review.md. Retaining modified BYE and configured
ZDE is not represented as a new permission grant from their original authors.
Microsoft M80/L80 and MicroPro WM development copies remain excluded; builders
supply the pinned external inputs when required. No blanket license has been
selected for original project code.
