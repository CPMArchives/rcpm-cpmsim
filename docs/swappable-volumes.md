# Swappable J: and P: volumes

Status: automatic-drive syntax is included in RCP/M 1.1.1. The original 1.1
packages provide explicit J:/P: swapping and standalone NDSCAN.

MOUNT handles media and CP/M disk relogging. After a successful replacement,
it uses CP/M 3 BDOS function 47 to chain to `A0:NDSCAN drive: /Q`. NDSCAN is a
separate, caller-accessible command; MOUNT does not duplicate its name logic.
Listing and failed mount requests never chain.

## Commands and image formats

| Command | Result |
| --- | --- |
| `MOUNT /L` | List J: and P: catalogs and their current images |
| `MOUNT J: /L` | List only J: |
| `MOUNT NAME` | Find NAME in both catalogs and select J: or P: by exact image size |
| `MOUNT J: GAMES` | Explicitly mount disks/library/GAMES.dsk on J: |
| `MOUNT P: /L` | List P: catalog and current image |
| `MOUNT TORONTO` or `MOUNT P: TORONTO` | Mount disks/library/archives/TORONTO.dsk on P: |
| `MOUNT J: /DEFAULT` | Restore disks/drivej.dsk |
| `MOUNT P: /DEFAULT` | Restore disks/drivep.dsk (normally SIG/M and CPMUG) |
| `NDSCAN P:` | Rebuild only P:'s names from the currently mounted image |

Successful mounts report `Volume NAME mounted on J:` or `Volume NAME mounted
on P:`. MOUNT uses NDSCAN /Q to suppress only its success message; scan errors
remain visible. Standalone NDSCAN retains its normal success message, with /Q
available explicitly.

If the same filename exists in both folders, an unqualified mount is refused
without replacing either drive. Use an explicit J: or P: command to choose.
`MOUNT /DEFAULT` continues to restore J:; qualify P: when restoring P:.

Names are 1-8 uppercase letters, digits or underscores. They are catalog IDs,
not host paths. Each drive keeps its own mounted-image identity. A process
restart restores both startup images; logging off does not change the mounts.

J: accepts only regular raw z80pack-hd images of **4,177,920 bytes**. P: accepts
only regular raw z80pack-hdb images of **536,870,912 bytes**. The emulator
validates the opened replacement descriptor before releasing the old one.
A wrong-size, missing, non-regular or unopenable image leaves both mounted
images unchanged. Each catalog lists only images matching its drive's size.
Exact size is a geometry safeguard, not proof of a valid CP/M filesystem;
create and verify images with the matching diskdefs entry. Padding a different
format does not convert it. No variable-size BIOS geometry is introduced.

MOUNT flushes pending CP/M buffers before replacing a handle, resets only the
selected drive's BDOS login state, logs it in, and restores the previous drive.
A flush failure prevents replacement. P: follows the same AUTH rules as J::
caller read access by default, with sysop-controlled drive/DU R/W overrides.
There is no new emulator-enforced permanent read-only policy.

## Directory markers and NDSCAN

Put an extensionless `-NAME` file in each user area that should have a name.
For example, `-SIGM` on P0: and `-CPMUG` on P1: restore the default archive
names. Marker contents are irrelevant. NAME consists of 1-7 uppercase letters,
digits or underscores; the leading hyphen leaves room in the 8-character
filename. Files with extensions, such as `-CATALOG.011`, are not markers.

NDSCAN scans all user areas 0-15 of the requested drive. It replaces that
drive's old names with the discovered names, clears names for user areas
without markers, and preserves all other drive entries, including their NDR
password fields. New marker-derived names have blank NDR password fields;
AUTH remains the authority for file access. NDSCAN never grants R/W access,
approves a COM file or writes a directory marker or any other disk file.

The replacement table is staged in the transient program's memory. Invalid
markers, multiple different markers in one user area, duplicate names (including
collisions with other drives), disk errors or insufficient table capacity abort
the update before resident names are changed. Repeated directory extents for
the same marker are not treated as different names. NDSCAN restores the entry
drive/user, DMA address and BDOS error mode, and returns program status 0000h
on success or FF01h on error.

The prepared Z3PLUS descriptor now reserves **42 names / 768 bytes**, instead
of 14 names / 256 bytes: an additional 512 resident bytes. That covers all 16
user areas on both J: and P: plus the existing system names. This is a Z3PLUS
configuration adjustment, not BetterCP/M's NDR.RSX. The utility also supports
other valid resident allocations up to 64 names and refuses unsupported tables.
Names are session state; standalone NDSCAN does not rewrite the startup library.

## Caller boundary and errors

NDSCAN is installed in protected A0: with F4 approval. BYE's normal caller load
rules still apply: effective R, no W, and the actual F4 directory attribute.

A new read-only BYE query, BDOS 201 with E=drive 0-15, returns HL=A118h/A=0 only
if the private sysop is in control or all 16 user areas have effective caller R
access. Otherwise it returns HL=FFFFh/A=FFh. It exposes neither the map nor a
resident pointer and does not mutate permissions. Existing private BDOS 200
AUTH operations stay private. This preflight prevents a denied directory search
from being interpreted as an absent marker and silently clearing private names.
A caller may scan another fully readable drive too; the utility is not tied to
P:. Sysops can scan private drives while the caller is blanked.

Media replacement and name scanning are separate operations because they are
separate chained programs. If NDSCAN fails, MOUNT has already reported a
successful media change; the new image stays mounted and the previous name
table remains intact. Correct the markers/access/capacity and rerun NDSCAN, or
restore /DEFAULT. Do not assume old aliases describe the newly mounted image
when an error was reported. Missing A0:NDSCAN.COM is detected before swapping.

The updated MOUNT needs the automatic-selection runtime and matching NDSCAN /Q;
older MOUNT programs keep their existing protocol and explicit-drive behavior.
New MOUNT requires the new mount protocol; an old emulator reports that it must
be updated and leaves media unchanged. Old J-only MOUNT programs remain
supported by the new emulator, but do not automatically scan names.

## Building and host maintenance

    python3 build_mount_tools.py --assembler /path/to/z80asm --output build/mount-tools

This produces MOUNT.COM, NDSCAN.COM and a SHA-256 build receipt. Fresh system
builders install both commands and mark them visible/approved through the
common caller policy. The updated emulator, BYE drivers and prepared Z3PLUS
library are required for full operation; copying NDSCAN alone into an old 1.0
installation does not provide the new BYE query or enlarge its resident table.

The native stopped-host approval tools accept `P/NAME` to address a named P:
image, e.g. `--caller-list P/TORONTO` or
`--caller-allow P/TORONTO:4:EXAMPLE.COM`. Plain P still means the default image;
plain GAMES means disks/library/GAMES.dsk. Normal live approval uses AUTH against the
currently mounted drive. Never edit images with host tools while RCP/M runs.

Copy disks/library/archives/ with the rest of an installation when backing up. Store private
media outside both public catalogs. A sysop who grants caller W access accepts
the possibility of changes to files and markers, just as on J: today.

## Validation record

[Recorded checks](performance/swappable-p-2026-11-22.json) cover actual CP/M
caller operation, live NDR contents, geometry rejection, default restoration,
permission grants/revocation, scan error preservation, buffer-flush failures and
the extracted native Mac package. The new Windows runtime and launcher compile
and pass their DLL audit, but this feature has not been runtime-qualified in
Windows. That is separate from the earlier 1.0 Windows qualification.
