# Standalone BASIC games

BASCOM's `/O` option and static runtime linking can turn many historical CP/M
BASIC games into standalone COM files. GAMES now includes a tested Hammurabi
build made this way. It does not contain MBASIC, BASCOM or BRUN.COM.

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

Three did not compile: AWARI has loop-structure incompatibilities; DIGITS
contains a duplicated THEN branch; HEXAPAWN has unsupported/invalid DEF FN
constructs. Exact errors are recorded in the build result. None of this batch
has been added to GAMES without gameplay qualification.
