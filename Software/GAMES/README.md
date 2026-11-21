# Expanded GAMES disk

An optional expanded edition of the v1.0 GAMES disk. It adds 11 tested CP/M
games and keeps only playable games, required data and playing instructions. Download it
separately; game binaries are not added to Git history or the base release.

[Download GAMES-expanded.zip](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-games-2026-11-22/GAMES-expanded.zip) ·
[Test report](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-games-2026-11-22/GAMES-REPORT.txt) ·
[Checksums](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-games-2026-11-22/SHA256SUMS.txt)

| Area | Games |
| --- | --- |
| J0: | All 14 launchers and the guide |
| J2: | Ladder, CatChum |
| J9: | Rogue, Wanderer, Star Trek, Sokoban, Hunt the Wumpus |
| J10: | Sargon, Othello, Backgammon, Battleships |

Adventure J1:, Maze Chase J3: and Animals J8: remain playable. Source-only
sets, unqualified programs and old catalogs have been removed. J4:–J7: and
J11:–J15: are empty. The image has **3,324 KiB free**, with 891 of its 1,024
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

All 11 additions received actual caller-session tests on RCP/M v1.0, CP/M 3,
Z3PLUS/BYE, ANSI terminal and the normal 4 MHz setting over direct TCP. Tests
covered meaningful moves or turns and exit. Rogue and Sargon also passed disk
save/reload checks. These are opening/session tests, not complete playthroughs.
The three existing games were played again after expansion. Caller recovery,
WORK cleanup, private-tool denial and unchanged GAMES bytes were checked.
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
