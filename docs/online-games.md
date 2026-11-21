# Online games and caller-program designation

Status: implemented per-file approval on protected public media. Gameplay and
connection-recovery results are recorded with the release checks.

Online games are an intended caller service. The existing machine uses trusted
program admission, not isolation of arbitrary Z80 code. A reviewed game can be
added to that model, but unpacking an archive alone does not qualify its code.

## Sysop designation

See [caller permissions](caller-execution.md) for the shared drive/DU policy.
In private sysop mode, use `SYSUTLS:AUTH J1:ADV.COM +X` to approve or `-X` to
revoke. This sets only F4. Caller execution additionally requires read access
and no write access to the executable's DU. No remount or restart is needed.
`AUTH /SAVE` persists DU permissions; F4 changes persist immediately as file
attributes. All A0 commands also use F4; there is no compiled filename exemption.

J: is writable for private sysop maintenance and read-only to callers by
default. The same BYE policy applies to every drive. Caller-writable WORK is
non-executable regardless of F4. Review native programs before approval;
interpreters, alternate loaders and shell escapes may execute additional code.

## Game launchers

After MOUNT GAMES, the J0: launchers ADVENT, ANIMALS and MCHASE prepare
per-call data in WORK and queue an exact J: executable. Only known seed filenames
are copied. Existing data is retained during the call; incomplete newly created
copies are deleted if preparation fails. WORK is selected explicitly before the
game loads. The launchers and game binaries remain on protected J: and have F4 approval.
Use `J0:ADVENT`, `J0:ANIMALS` or `J0:MCHASE` from the CP/M prompt.
No game-specific launcher is installed on A0:.

Saves and high scores in WORK disappear at logoff. Games that require writing
to J: are available for download and local play rather than online execution. Caller execution from other unapproved files and all
WORK programs remains denied. Game exits/disconnects must recover to CP/M/BYE
without granting wheel access. Programs that stop polling console/BDOS need
individual recovery assessment.

The normal CPU clock remains 4 MHz. Maze Chase is adapted through its documented
cursor hook to ANSI/VT100, with its 4 MHz timing value unchanged. The original
ADM-3A executable remains in the separate archive, not on GAMES. Its original
MCHASE.DOC and MCHASE.HLP are preserved unchanged. The terminal adaptation source
is guest/mchansi.asm; the manifest records original and installed hashes.

## User-area allocation

J0: is the launcher/index area. Group new games by category or shared runtime
when their filenames permit; do not allocate a user area automatically for
each game. Isolate conflicting data filenames only when needed. Qualified games retain their current locations. Source-only and unqualified
sets are excluded from GAMES.

## Current image

| User area | Contents | Preparation |
| --- | --- | --- |
| J0: | README, GAMES marker and ADVENT/ANIMALS/MCHASE launchers | Volume guide and WORK-data preparation |
| J1: | Expanded Adventure, SIG/M 11 | ADV.COM plus four runtime data files |
| J8: | Revised Animals, SIG/M 134 | ANIMALS.COM plus writable BEASTS data |
| J3: | Maze Chase, SIG/M 228 | MCHASE.COM adapted for ANSI/VT100; original in separate archive |

GAMES contains playable games, required runtime data and playing instructions.
The source-only sets formerly on J4-J7, source files, old catalogs and the
unapproved MCHORIG.COM have been removed. Original archives remain on P:.
SIGMV001 and the non-game SIGMV152 remain excluded.

## Optional expanded GAMES

The [Software/GAMES collection](../Software/GAMES/README.md) adds eighteen qualified
games in three shared areas, with every launcher on J0:. It is an optional
replacement image and is not a new base-system packaging input. The catalog
records tested editions, caller-session coverage and remaining limitations.
