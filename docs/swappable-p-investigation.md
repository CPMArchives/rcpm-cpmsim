# Swappable P: investigation

Historical investigation: the implementation and agreed marker-based NDSCAN
design are now described in [swappable volumes](swappable-volumes.md). That
design supersedes the options below for collection-specific names. The buffer-
flush precaution from PR #18 is retained. Published 1.0 assets are unchanged.

## Scope and established decisions

Add selectable historic archive images on P: while retaining existing J:
mounting. P: uses the same AUTH rules as J:: caller read access by default,
sysop-controlled drive/DU overrides, and private sysop access. Do not introduce
an unconditional read-only P: rule. Permission settings continue to belong to
drive/user slots rather than individual image names.

Flush pending CP/M buffers before a swap, then invalidate/relog the selected
drive after a successful replacement. AUTH's policy-change flush is handled in
PR #18. These are deterministic precautions, not assumptions of concurrent
applications or timed background writeback. Flush failure prevents the swap.

## What the current code establishes

- `patches/cpmsim-live-mount.patch` implements a guest I/O device on port 60.
  It validates an opened image using fstat, requiring a regular file of exactly
  4,177,920 bytes. It opens the replacement before closing the existing drivej
  handle. Names are restricted to 1-8 uppercase letters, digits or underscores.
- The production `build_modem_runtime.py` integration changes catalog opens to
  try read/write, with read-only fallback. BYE/AUTH enforce caller permissions.
  The original patch's read-only comment does not describe the complete runtime.
- The emulator disk table already represents J: and P: through separate file
  handles, with fixed geometries. The disk controller dereferences the current
  handle for each operation. P: therefore supports handle replacement without
  a new controller, BIOS disk definition or CP/M filesystem format.
- `guest/mount.asm` hard-codes J:, its 0200h drive-reset mask, listing header
  and result messages. It must select drive 15 and mask 8000h for P:, while
  preserving the user's currently selected drive after relogging.
- macOS and Windows builds both use prepare_service_source/integrate from
  `build_modem_runtime.py`. The core mount implementation can remain shared;
  both native builds still require compilation and runtime checks.

## Required geometry checks

| Slot | Format | Tracks | 128-byte sectors per track | Required image bytes |
| --- | --- | --- | --- | --- |
| J: | z80pack-hd | 255 | 128 | 4,177,920 |
| P: | z80pack-hdb | 256 | 16,384 | 536,870,912 |

Treat these as fixed formats for the first implementation. Select validation
from the requested drive, never from a filename suffix or an assumed catalog
folder. In particular:

- Reject a 4 MB image for P: and a 512 MiB image for J:.
- Reject truncated, oversized, non-regular and unopenable images.
- Check the opened descriptor with fstat before replacing the active handle.
- Return distinct wrong-size, unavailable and unsupported-drive results.
  MOUNT should name the requested drive and explain a geometry mismatch.
- List only compatible images for the selected drive, but repeat validation
  when mounting: listing is not authorization or proof that a file is unchanged.
- On validation/open/flush failure, retain the current handle and mounted name.
  The other drive must be unaffected in every case.

The raw images have no self-describing geometry header. Exact byte length
prevents the J:/P: size mix-up but cannot prove that a same-sized file has the
correct CP/M directory, allocation layout or contents. Use matching cpmtools
formats and offline filesystem/readback checks when preparing catalog images.
Padding an arbitrary disk image to the expected size does not convert it.

## Proposed user interface and catalog

Retain all existing commands unchanged:

    MOUNT /L                 list J: volumes
    MOUNT GAMES              select GAMES on J:

Add explicit drive selection:

    MOUNT J: /L
    MOUNT J: GAMES
    MOUNT P: /L
    MOUNT P: TORONTO
    MOUNT P: /DEFAULT        restore disks/drivep.dsk

Use `volumes/` for the existing J: catalog and `archives/` for P: images.
Names retain the existing 8-character limit. Separate folders make operating
both catalogs clear; geometry checks are mandatory even in the right folder.
A default-restore option avoids reserving an otherwise valid image name such
as DEFAULT. Keep the bundled SIG/M/CPMUG image as the startup default. Mounts
last for the running emulator, as with J: today; a process restart opens the
normal default. Automatic restoration at caller logoff would be a separate
behavior change and is not proposed here.

Extend port 60 rather than building another mounting subsystem. Preserve the
existing J: reset/list opcodes and make them explicitly select J:. Add distinct
P: reset/list commands and a capability query. A new MOUNT must reject a P:
request on an older runtime; it must never interpret a stale success status as
confirmation. Old J-only commands must still select J: after any P: command.
Default restoration also needs an explicit supported command. Exact opcode
assignments remain an implementation detail to review before coding.

The validated replacement handle is adopted only after the guest flush has
succeeded. The CP/M reset mask is chosen by drive. Flush/relog handling and
AUTH rules remain common to J: and P:.

## Named directories: remaining design choice

The resident Z3PLUS named-directory table is populated at startup. SIGM: and
CPMUG: point to P0: and P1:; swapping a host image does not update those names.
They would misleadingly label another collection. This is independent of the
emulator geometry and must not be silently treated as solved by swapping.

Two possible scopes need a decision before implementation:

1. Minimal mounting: retain the static table and explicitly document that the
   SIGM:/CPMUG: aliases describe the default image only. Other collections use
   P0:, P1:, etc. This works technically but leaves misleading labels/prompts.
2. Collection-aware names: associate P: images with named-directory metadata,
   replace only P: entries on successful swaps and restore the default entries
   on /DEFAULT. Validate name collisions, user numbers and available resident
   capacity before swapping. Leave all non-P: entries unchanged.

The second gives a better caller experience but adds guest-side metadata and
Z3PLUS environment handling. `prepare_z3plus.py` currently checks a configured
14-entry resident allocation; do not assume 16 new P: names will fit. Keep
permissions independent of names. No name-loading format or automatic table
rewrite has yet been approved or implemented.

## Other affected integration points

- Builders/package manifests: permit the optional archives/ catalog, include
  supplied images and metadata, and retain the default P: image. Do not change
  the fixed boot geometry or bundle an extra empty 512 MiB image unnecessarily.
- Host caller-approval tools: `packaging/launcher.c` currently maps P to the
  default disk and all named images to the 4 MB volumes/ catalog. Windows uses
  that launcher through its adapters. Extend target selection for named P:
  images if those tools are expected to administer them; never mistake the
  currently mounted P: image for disks/drivep.dsk in stopped-host tooling.
- Checksums, backup/restore and manual image maintenance: cover the new catalog
  and identify which images are defaults versus selectable collections. The
  packaged default need not be renamed or moved.
- Help and manuals: describe drive-qualified syntax, geometry rejection,
  persistent AUTH slot permissions, current collection and restoring default.
- Build integration: avoid modifying a patch hunk that later upload patches
  expect without updating their application contexts. Test preparation from
  pristine pinned source, not only an already-patched local tree.

## Proportionate acceptance checks

Use disposable media and assembled guest commands; no operator images:

1. Existing J: listing/mounting still works; P: commands leave J: unchanged.
2. Two valid P: images with different directory contents swap correctly,
   including repeated P: user-area access with no stale directory data.
3. Wrong-size images in both directions, missing files and failed flushes leave
   the previous image and mounted name unchanged. Catalog filtering is correct.
4. Restore the default P: and verify both preserved collections remain readable.
5. Default caller reads/writes and sysop AUTH overrides behave exactly as on J:.
6. Capability mismatch fails clearly on an old runtime; legacy J: opcodes still
   target J: after using P:. Process restart restores the normal defaults.
7. If collection-aware names are included, test default-name restoration,
   collisions/capacity rejection and preservation of all non-P: names.
8. Build native macOS and Windows runtimes from pinned source and run the mount
   checks on each. Rebuilding Windows alone is not runtime qualification.

## Conclusion

Swapping P: is a contained extension of the existing mount device and command.
The fixed 512 MiB geometry is already supported. Required work is drive-aware
mounting and validation, compatible protocol changes, guest relogging, catalog
and packaging support, and focused qualification. Collection-specific named
folders add a separate, visible scope choice. No arbitrary-size disk support,
new AUTH policy, new BIOS or concurrency mechanism is required.
