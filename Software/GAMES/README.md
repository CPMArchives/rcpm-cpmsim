# Expanded GAMES disk

An optional expanded edition of the v1.0 GAMES disk. It adds 49 tested CP/M
titles, including 31 standalone BASIC additions, and keeps ready-to-run
software, required data, playing instructions and notices. Download it
separately; game binaries are not added to Git history or the base release.

[Download GAMES-expanded.zip](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-games-2026-11-22/GAMES-expanded.zip) ·
[Test report](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-games-2026-11-22/GAMES-REPORT.txt) ·
[Checksums](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-games-2026-11-22/SHA256SUMS.txt)

| Area | Games |
| --- | --- |
| J0: | All 52 launchers and the guide |
| J2: | Ladder, CatChum, CPMtris, Robots, Snake |
| J4: | 31 standalone BASIC titles; see [BASIC collection](BASIC.md) |
| J9: | Rogue, Wanderer, Star Trek, Sokoban, Hunt the Wumpus, Hangman, Minesweeper |
| J10: | Sargon, Othello, Backgammon, Battleships, Mastermind, Hammurabi |

Adventure J1:, Maze Chase J3: and Animals J8: remain playable. Source-only
sets, unqualified programs and old catalogs have been removed. J5:–J7: and
J11:–J15: are empty. The image has **2,638 KiB free**, with 800 of its 1,024
directory slots free.

## Install and play

Stop RCP/M cleanly and back up your existing `volumes/GAMES.dsk` before replacing
it with the supplied image. This edition intentionally removes 46 archive/source/unqualified files;
all retained game binaries and required data are unchanged. If your installed disk contains further local
additions, apply the recorded removals and supplied `payload/` to a stopped copy of that disk instead
of overwriting those additions. The supplied reproduction script deliberately
accepts only the recorded released base image.

Start RCP/M, enter `MOUNT GAMES`, and use a launcher such as `J0:LADDER`.
All game-specific launchers stay on J0:. They select I0:WORK and copy only named
seed data; native game code stays on protected J:. Scores and saves last for
this call, so download anything you want to keep before logging off. Let screens
finish drawing before sending keys; pasted key sequences can be lost.

The ZIP changes only GAMES. It does not replace A:, I:, P:, permissions, or the
v1.0 download. Existing A0: game wrappers in an older installation can be removed
by the sysop after confirming the corresponding J0: launcher works. New system
builds place those launchers on GAMES.

## Qualification and limits

All 49 additions received actual caller-session tests on RCP/M v1.0, CP/M 3,
Z3PLUS/BYE, ANSI terminal and the normal 4 MHz setting over direct TCP. Tests
covered meaningful moves or turns and exit. Rogue and Sargon also passed disk
save/reload checks. These are opening/session tests, not complete playthroughs.
The three base games were regression-tested in the earlier expansion; their
files are unchanged here. Caller recovery, WORK cleanup, private-tool denial
and unchanged GAMES bytes were checked on the finished image.
IP232 was not rerun for this expansion.

Aliens was tested but excluded: its original Kaypro edition uses ADM-3A screen
codes. Wumpus qualifies in its documented scrolling text mode: answer **N** to
built-in instructions and read `LT J9:WUMPUS.DOC` instead. Cave 3 is absent
upstream; use 0, 1, 2, 4 or 5. Only cave 0 received gameplay testing. Sokoban's
movement and undo pass; no persistent save support is claimed. Higher Sargon
levels and later Wanderer levels were not individually tested.

Ladder's Escape key pauses; Ctrl-C returns to its menu and E exits. Do not use
the Ladder/CatChum configuration options on the protected master. Detailed
controls and other edition-specific limits are in the image's `README.TXT` and
the downloadable report.

## Sources and reproduction

The ZIP includes the per-file manifest, checked payload, generated launcher
assembly, available game sources, notices, test records and `build_image.py`.
The script applies the recorded removals and payload, clears free blocks and
rebuilds a byte-identical image from the released base using RCP/M's
packaged cpmtools. Individual games retain their original rights and notices.

ANSI editions come from [acn's VT100 CP/M collection](https://git.imzadi.de/acn/vt100-games).
Sargon and Star Trek come from the [Retroarchive games mirror](https://www.mrynet.com/FTP/os/CPM/retroarchive-CPM/games/).
Othello and Wumpus use the project's preserved CPMUG048 and CPMUG073 members.

## Latest additions and BASIC compilation

The seven additions are CPMtris (`J0:CPMTRIS`), Hammurabi (`J0:HAMURABI`),
Hangman (`J0:HANGMAN`), Mastermind (`J0:MASTERM`), Minesweeper (`J0:MINES`),
Robots (`J0:ROBOTS`) and Snake (`J0:SNAKE`). Ladder was already present.

CPMtris uses its VT100/4 MHz arguments automatically. Hangman uses a supplied
154-word English list. Minesweeper is rebuilt with ASCII borders. Snake is
rebuilt for 24 rows and a lower memory ceiling to fit the resident system.
All seven passed actual gameplay input and exit checks. Disconnect recovery
during Snake and temporary Hangman word-list cleanup were verified.

Hammurabi is a standalone BASCOM `/O` build with statically linked runtime
routines. It requires neither an interpreter nor `BRUN.COM`. The original
Microsoft manual permits distributing linked applications royalty-free with
the prescribed notice; the compiler and separate runtime module have different
terms. [Distribution terms](MICROSOFT-RUNTIME-TERMS.txt) and the image's
`COPYING.TXT` retain the distinction and required notice.

A [reusable private build pipeline](compile_basic.py) initially compiled 27 of
30 more BASIC programs. Those 27 passed meaningful input, exit to WORK and individual
carrier-loss recovery tests and are now on J4:, with launchers on J0:. BOMBARD
uses terminal output in place of its mandatory printer output. DIAMOND is a
pattern activity and DICE is a roll-frequency simulation. AWARI, DIGITS and
HEXAPAWN have now been repaired, tested and added alongside Richard S.
Altman's Mission: Impossible from the Walnut Creek CD-ROM. All four share
J4: and use J0: launchers. See [BASIC qualification and controls](BASIC.md).

## Repaired games and Mission: Impossible

Start `J0:AWARI`, `J0:DIGITS`, `J0:HEXAPAWN` or `J0:MISSION`. AWARI
passed two complete rounds and replay; DIGITS passed two 30-number rounds
and replay; HEXAPAWN passed six rounds with a corrected 3×3 display and
mirrored openings. Each passed exit and separate carrier recovery.

MISSION is Richard S. Altman's 1989 user-supported espionage game from
`LAMBDA/SOUNDPOT/F/MISSION.LBR` on the November 1994 Walnut Creek CD-ROM.
The ANSI/standalone edition replaces Kaypro cursor/attribute codes, simplifies
decorative line graphics, uses ASCII map symbols, and adds Q to quit at
“Your orders”. Both instruction pages, headquarters assistance/intelligence,
status, map, scouting, movement, quit and disconnect recovery passed. A
complete mission win, all random encounters and higher skill levels were
not tested. Original author credits and free-distribution/shareware terms
are retained in `J4:MISSION.DOC` and in the host ZIP. No MBASIC is needed.
