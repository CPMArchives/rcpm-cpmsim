# Scott Adams adventures for RCP/M

An optional dedicated SCOTT disk, using the original CP/M ADVENTUR.COM 8.4c
interpreter and unchanged story files from IF Archive. All files use user 0.

[Download SCOTT-collection.zip](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-scott-2026-11-22/SCOTT-collection.zip) ·
[Test report](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-scott-2026-11-22/SCOTT-REPORT.txt)

| Selection | Adventure |
| --- | --- |
| 1 | Adventureland |
| 2 | Pirate Adventure |
| 3 | Secret Mission |
| 4 | Voodoo Castle |
| 5 | The Count |
| 6 | Strange Odyssey |
| 7 | Mystery Fun House |
| 8 | Pyramid of Doom |
| 9 | Ghost Town |
| A | Savage Island I |
| B | Savage Island II |
| C | The Golden Voyage |
| 0 | Adventureland Sampler |

The sampler uses 0 despite the historical menu saying 1-Z. Adventures
10–12 use A, B and C. Secret Mission is Scott Adams' original Mission
Impossible; it is distinct from Richard Altman's MISSION on GAMES.

## Install and play

Stop RCP/M cleanly and copy volumes/SCOTT.dsk alongside the other optional
volumes. Restart, enter MOUNT SCOTT, then J0:SCOTT. The launcher prepares
only named story data in I0:WORK and runs approved J0 code. Initial
preparation can take a minute or more at 4 MHz; wait for Which Adventure.
J: stays read-only and WORK remains non-executable.

Choose a single character and enter a player name of 1–8 letters/digits,
with no drive or path. Answer N for a new game, Y to restore with that same
name and adventure. Press Return after the introduction. Use two-word
commands such as GO NORTH, GO TREE, GO STAIRS, GET RUM, SAVE GAME and QUIT;
INVENTORY and LOOK also work. QUIT then N returns to WORK.

Saves are NAME.S1 through NAME.SC, or NAME.S0 for the sampler. They stay in
WORK for the current call. Download before logging off, e.g.
YSEND I0:NAME.S1. WORK is cleared on disconnect. Cross-call saved-game
upload/download was not qualified. The original interpreter has no UNDO.

## Qualification and scope

Every included entry was exercised through startup, inventory/opening
commands, SAVE GAME, quit, relaunch and restore under RCP/M 1.0, CP/M 3,
Z3PLUS/BYE, 4 MHz, direct TCP. The Z80 refresh-register diagnostic returned
changing values, and gameplay continued beyond the historical RNG hang.
Savage Island II expects the continuation password before ordinary commands.
Some opening movement commands are blocked by puzzles or loop to the same
room; per-entry records distinguish successful room changes.

The finished image additionally restored Adventureland's changed location
and Pirate Adventure's changed inventory. Saves were verified in WORK;
carrier loss during play, fresh-caller recovery, WORK cleanup, private-tool
denial and unchanged SCOTT/GAMES hashes passed. These are opening/session
tests, not full solutions. Savage Island I-to-II completion handoff, all
timed/random events and later ScottFree-format titles remain unqualified.

## Sources, notices and reproduction

[IF Archive CP/M collection](https://www.ifarchive.org/indexes/if-archive/scott-adams/games/cpm/)
provides the original twelve adventures, sampler and 8.4c interpreter. The
[author's later downloads](https://www.msadams.com/downloads.htm) include a
notice describing copyrighted, voluntary-contribution shareware. The
games are not public domain and are not collectively relicensed as RCP/M.
Original copyright text, Russ Wetmore's CP/M conversion credit, the later
shareware notice and archive hashes accompany the ZIP.

The image contains games, the launcher and guides. The R-register test
utility is retained only in the host-side original archive. build_image.py
and the checked payload reproduce the disk byte-identically with RCP/M's
packaged cpmtools. No existing GAMES, INFOCOM, MODERNIF or v1.0 release
asset is replaced.
