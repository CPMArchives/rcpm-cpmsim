# Caller permissions and executable approval

BYE uses one resident policy for all 16 drives and all 16 user areas.
Caller access defaults to neither read nor write. Each drive has an R/W
setting; an explicit DU setting overrides it. Removing a DU override restores
inheritance from its drive. Private local sysop mode bypasses caller access
checks; genuine host read-only media remains read-only.

Default media grants A0: read, J:/P: read, I0: read/write, and I14: read.
Every other DU is private, including I13:SYSUTLS and I15:RBBS data.
Selecting a DU does not grant file access: Z3PLUS changes user before drive,
so intermediate selections are allowed and file operations enforce the policy.

Before replacing the live permission map, AUTH flushes pending CP/M disk
buffers while the previous policy remains active. This applies to direct
drive/DU edits and validated /LOAD operations, including changes to inherited
permissions. A flush error aborts the update and leaves the resident map
unchanged. This is a precaution; no background-write race is assumed.

## Executable approval

Caller BDOS 59 loads require effective R access, no effective W access, and
F4 in the actual directory entry of an exact COM file. All drives use the same
rule. The individual R/O file attribute is optional and retains its ordinary
CP/M meaning. No A0 filename has a compiled approval exemption: the standard
caller commands are seeded with F4 when building the image.

A writable DU never permits caller execution, even with F4 set. Making I0:
read-only allows its approved files to execute; making it writable blocks them
again. The WORK cleanup lifecycle still deletes I0: files at call boundaries.
Other user areas on I: have no hardcoded execution prohibition.

BYE masks supplied FCB attributes, rejects wildcard loads, reads F4 from the
real directory, and restores DMA afterward. File reads/downloads are governed
by R permission, independently of executable approval. This is trusted-program
admission, not CPU or memory isolation against hostile native code.

The existing A0:RBBS launcher remains a narrow exception: successful launcher
load permits one exact A15:RBBS37 load. Active RBBS gets access to its own I15:
private data and A15: support files. It gains no wheel privileges. Warm boot,
logoff or carrier loss clears that context. Public read/write settings for
those DUs remain denied.

## Live administration

Blank the caller locally with Ctrl-B, then use the private command path:

```text
SYSUTLS:AUTH /MAP
SYSUTLS:AUTH J: R
SYSUTLS:AUTH I0: RW
SYSUTLS:AUTH I14: R
SYSUTLS:AUTH I1: NONE
SYSUTLS:AUTH I1: INHERIT
SYSUTLS:AUTH J1:ADV.COM +X
SYSUTLS:AUTH J1:ADV.COM -X
SYSUTLS:AUTH /SAVE=I13:AUTH.DAT /Y
```

`AUTH` and `AUTH /MAP` show all drives. `AUTH J:` and `AUTH J3:` both
show only the complete J: row (users 0-15); queries never change permissions.
`AUTH J1:ADV.COM` reports effective caller executability, with a reason if
read access is absent, the DU is writable, or F4 is unset. Missing files are
reported separately.

Permission spellings replace the whole R/W setting:

| Slash form | Map form | Existing alias |
| --- | --- | --- |
| /RW | RW | RW |
| /R | R- | R |
| /W | -W | W |
| /NONE | -- | NONE |

A DU override survives later changes to its drive. `INHERIT` or `/INHERIT`
removes only that DU override. Setting a drive to NONE does not clear its DU
overrides. The map marks explicit overrides with a prefix asterisk (`*RW`).

+X/-X sets/clears only F4, preserving executable bytes and other attributes.
Exact DU and COM names are required. Existing SET can also manage F4 in private
mode. No remount or restart is needed. AUTH's resident API rejects caller-mode
requests even if AUTH.COM is copied to a public DU and approved.

Permission changes affect the resident map immediately. Bare `/SAVE` and `/LOAD`
prompt for a filename; Return selects `I13:AUTH.DAT`. A save to an existing file
asks for confirmation. For scripts, use explicit filenames:

```text
AUTH /SAVE=I13:PUBLIC.DAT
AUTH /SAVE=I13:PUBLIC.DAT /Y
AUTH /LOAD=I13:PUBLIC.DAT
```

The first form creates a new file, but fails without prompting if it already
exists. `/Y` permits overwrite; it does not bypass file errors or private-mode
checks. Explicit `/LOAD=filename` also runs without prompts. Unqualified policy
filenames use I13:; a drive-only prefix uses the current user, and an explicit
DU selects that DU. File names are exact CP/M 8.3 names, without wildcards.

Saving stages three complete records in the destination DU using the same
basename with extension `.$$$`. It closes and flushes that file, then renames
the previous destination to the same basename `.BAK`, replacing its prior backup,
and installs the new file. `.BAK` and `.$$$` are reserved save extensions.
An existing staging file is never silently erased: inspect it before retrying.
On failed installation, AUTH attempts to restore the backup. Retain any staging
and backup files after an I/O error. AUTH reports errors and sets CP/M 3's
program return code (0000h success, FF01h failure/cancel).

Loading validates the signature and every permission byte before replacing the
resident table. Failed or invalid loads leave live permissions unchanged.
BYE always loads **I13:AUTH.DAT at startup**, regardless of the last alternate
file loaded. To make an alternate live map the startup policy, save it explicitly
to `I13:AUTH.DAT` with overwrite authorization. Live changes survive call
boundaries; saved changes survive restarts. F4 changes persist as file attributes
and do not require `/SAVE`.

A missing/invalid startup policy leaves caller access denied and reports locally;
the operator can repair it in private mode. Backups are never selected
automatically.

The policy format is three 128-byte records: `RCPMAU01`, 16 drive permission
bytes, 256 DU bytes in drive-major order, and reserved padding. R=1, W=2;
DU FF means inherit. The resident copy, not the disk file, serves file checks.
Only private sysop mode may read/change the resident API (BDOS 200).

## Import and trust

Clear inherited F4 flags before approving imported executables. Host imports
through cpmcp create fresh entries; the games builder marks only reviewed
programs. Approval includes trusting any code-loading/interpreter capabilities
of the program. It grants neither wheel nor private-directory access.
J:/P: images are writable by the host owner so the sysop can maintain them;
common BYE write guards protect caller-read-only DUs on A:, I:, J:, P: alike.
Programs requiring writes to a protected collection are download/local-play
candidates. Online game compatibility does not justify making J: caller-writable.

The optional host --caller-allow/deny/list helper remains an offline image
maintenance tool. It is not required for normal live AUTH administration.

## Resident commands and privilege transitions

Z3PLUS's resident GET, GO and JUMP bypass ordinary transient lookup, so their
native wheel protection is required. The supplied RCP also wheel-protects
memory inspection/modification, port I/O, register manipulation and ERA.
The builder verifies the exact DEFCP3 and DEFRCP module revisions before
using this behavior; an unrecognized revision fails the build.

The original DEFRCP's WHL command can grant wheel privileges using its default
password. The builder sets the command table's wheel-required bit for WHL,
using a validated entry in the pinned module, and updates the LBR CRCs.
Callers therefore cannot use the published password to elevate themselves.
BYE's local private-mode control owns normal operator elevation; restoring
caller mode clears the wheel again. All these rules apply to both keyboards
while the console is shared.

The native commands and default WHL behavior are described in the original
[Z3PLUS User's Manual](https://manualzilla.com/doc/6919195/z3plus-user-s-manual),
sections 3.2.1 and 3.2.3. BDOS function 59 is documented in Digital Research's
[CP/M 3 Programmer's Guide](https://www.mrynet.com/FTP/os/CPM/manuals/cpm3-pgr.pdf).
The tests verify the selected binaries rather than relying on the manuals alone.

## Caller-accessible name scanning

NDSCAN reads extensionless -NAME markers and updates only the selected drive's
resident named directories. It does not change this permission map or F4.
BYE's separate read-only BDOS 201 query checks that a caller can read all user
areas before scanning; the private AUTH API (BDOS 200) remains inaccessible.
Private sysops can scan any available drive. See [swappable volumes](swappable-volumes.md).
