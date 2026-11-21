# Standalone BASIC games

BASCOM's `/O` option and static runtime linking can turn many historical CP/M
BASIC games into standalone COM files. GAMES includes Hammurabi and 31 more tested
standalone BASIC titles made this way. It does not contain MBASIC, BASCOM or BRUN.COM.

The [runtime terms](MICROSOFT-RUNTIME-TERMS.txt) distinguish distribution of
compiled applications from distribution of the compiler or separate runtime
module. Required Microsoft notices are kept in each prepared application and
on the disk. Original game credits and permissions still apply.

## Build pipeline

Run `compile_basic.py` from this repository with your own development tools:

```text
python3 Software/GAMES/compile_basic.py \
  --archive /path/to/ccgames.zip \
  --compiler /path/to/private/bascom \
  --tools /path/to/rcpm/runtime \
  --cpmsim /path/to/build/cpmsim \
  --boot /path/to/cpm3-1.dsk \
  --output /path/to/new-build \
  --names ACEYDUCY,BAGELS,BOWLING,HILO
```

The compiler directory must contain BASCOM.COM, L80.COM and OBSLIB.REL. These
remain private inputs. `games/` contains only generated application COM files;
`prepared/` holds the adapted source; `build-results.json` records hashes and
compiler/linker results. The private `machine/` is not a distributable disk.

The adaptation preserves line numbers, joins historical wrapped source lines,
replaces standalone Ctrl-Z clears with ANSI output, changes RUN MENU to END,
and prepends the required notice to the first statement. Other source changes
require individual review. A successful build does not prove the game runs.

## First batch, 22 November 2026

27 built: ACEYDUCY, BAGELS, BATNUM, BATTLE, BLACKJCK, BOMBARD, BOMBSAWY,
BOWLING, BOXING, BULLSEYE, CHOMP, CIVILWAR, COMBAT, CRAPS, CUBE, DEPTHCHG,
DIAMOND, DICE, FURTRADR, GOMOKO, GUESS, GUNNER, HILO, HURKLE, MUGWUMP,
NIM and ROCKSP.

The first attempt rejected AWARI, DIGITS and HEXAPAWN. The reviewed repairs
below now compile and pass caller qualification; all 30 Creative Computing
candidates are included, plus the separately sourced MISSION.

## Runtime qualification

All 27 passed actual RCP/M v1.0 caller tests under CP/M 3, Z3PLUS/BYE,
4 MHz and direct TCP: meaningful gameplay input or activity output, exit to
I0:WORK, then an individual disconnect at an input prompt and fresh-caller
recovery. These are opening/session tests, not complete playthroughs.
The finished image also passed Hangman data preparation, BAGELS disconnect,
WORK cleanup, private-tool denial and unchanged master-image checks.

The 31 native COM files share J4:; every launcher is in J0:. Start with
`MOUNT GAMES`, then e.g. `J0:BAGELS`. `LT J0:BASIC.TXT` lists controls.
The collection includes per-game results and caller test events outside the
disk image. No compiler, interpreter, BRUN or raw runtime library is included.

BOMBARD's mandatory `LPRINT` output is redirected to the terminal. Reproduce
this edition with `--names BOMBARD --console-printer`; the option is opt-in
and should be reviewed per source. In BATTLE answer N to printer output.
Ctrl-C exits titles without a convenient quit command; a compiled BASIC
STOP message at an address can be a normal return to WORK. DIAMOND prints
patterns; DICE is a roll-frequency simulation.

## Reviewed repairs and MISSION ANSI edition

| Launcher | Repair/adaptation | Additional gameplay coverage |
| --- | --- | --- |
| `J0:AWARI` | Replace shared-NEXT pit scans with two structured loops | Two complete games, 26 legal human moves, extra turn, replay and normal exit |
| `J0:DIGITS` | Remove duplicate THEN; declare N(10) | Two 30-number rounds, scoring, replay and normal exit |
| `J0:HEXAPAWN` | Equivalent board-reflection formula; declare T(9); TAB once per row | Six rounds, 13 legal human moves, mirrored openings, 3×3 display, automatic restart and Ctrl-C exit |
| `J0:MISSION` | Kaypro controls to ANSI, simplified illustrations, ASCII markers, Q quit | Both instruction pages, name/skill 1, headquarters help/intelligence, report, map, discover, movement and quit |

All four also passed separate carrier-loss recovery at input and unchanged
master-image checks under RCP/M, CP/M 3, 4 MHz and direct TCP. MISSION was
not played to a complete win; all skills/random events were not tested.
Its original source and documentation permit free distribution and retain
the author's shareware registration notice.

[Source patches](patches/) operate on original numbered BASIC files after
removing Ctrl-Z padding and normalizing line endings to LF. Apply a patch
to a working copy; pass the resulting directory with
`--source-overrides /path/to/adapted`. The build record retains both original
archive-source and reviewed-source hashes. The compiled notice and general
terminal adaptations are added by the pipeline; do not apply them twice.

For the three repairs use the Creative Computing archive and
`--names AWARI,DIGITS,HEXAPAWN`. For MISSION, extract and uncrunch
`MISSION.BAS` from the CD-ROM's `LAMBDA/SOUNDPOT/F/MISSION.LBR`, verify the
crunch checksums, make a ZIP member `DISK1/MISSION.BAS`, and use
`--names MISSION`. The optional download includes original sources, adapted
sources, patches, source/archive hashes and test events.

MISSION controls are single keys: N/S/E/W move, R report, D scout, M map,
Q quit at Your orders. Use a titled name such as Mr. Smith; skill is 1–6.
At headquarters Y stays for another hour, A gets help, F gets intelligence.
`J4:MISSION.DOC` is the original author notice/documentation; its MBASIC
startup instructions describe the historical source edition.
