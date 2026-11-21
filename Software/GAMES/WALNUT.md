# Walnut Creek CD-ROM games

The optional GAMES download adds 24 tested titles from
LAMBDA/SOUNDPOT/F/MBGAMES1.LBR through MBGAMES6.LBR on the
[November 1994 Walnut Creek CP/M CD-ROM](https://archive.org/details/cdrom-1994-11-walnutcreek-cpm).
These six libraries contain 156 BASIC program members; this is a selected
batch, not an exhaustive CD-ROM qualification. Existing games are preserved.

All additions share J4:. After MOUNT GAMES, use their J0: launchers.
If a game asks for a random-number seed, any integer works; tests used 7.

| Game | Launcher | Controls |
| --- | --- | --- |
| 23 Matches | `J0:MATCH23` | Take 1-3 matches; avoid the last match. Y replays; N exits. |
| Baccarat | `J0:BACCARAT` | N skips rules; Y starts; enter a wager, Y/N for another card, N ends at replay. |
| Bug | `J0:BUG` | N skips instructions; Y/N chooses bug pictures between dice turns. Ctrl-C exits at a question. |
| Chemist | `J0:CHEMIST` | Dilute each acid quantity with 7/3 as much water. A wrong answer loses a life; Ctrl-C exits. |
| Crazy Eights | `J0:CRAZY8` | Y means you know the rules. Y plays a card; N draws. Enter rank,suit when playing; Ctrl-C exits. |
| Flip Flop | `J0:FLIPFLOP` | Enter positions 1-10 to change X/O. 0 resets the line; 11 starts over; Ctrl-C exits. |
| Golf | `J0:GOLF` | Enter handicap 0-30 and your weakness, then club (and swing percentage when requested). Ctrl-C exits. |
| Hi-Q peg solitaire | `J0:HIQ` | Return displays the numbered board. Enter peg number and destination, e.g. 23 to 41. Ctrl-C exits. |
| Hockey | `J0:HOCKEY` | N skips rules; enter teams, minutes, six names per team, referee, then pass/shot/area numbers. Ctrl-C exits. |
| Horse Race | `J0:HORSES` | Enter random seed, horse 1-7, wager, then a number other than 1 to confirm. Ctrl-C exits. |
| King | `J0:KING` | N skips rules. Decide land sales, food distribution, planting and pollution spending. Ctrl-C exits. |
| Lunar Lander | `J0:LUNAR` | Enter burn rate 0-200 for each ten-second interval. Y/N replays; Ctrl-C exits. |
| Nicoma | `J0:NICOMA` | Think of a number 1-100; supply its remainders modulo 3, 5 and 7. N ends at replay. |
| One Check | `J0:ONECHECK` | Return starts. Enter from/to squares for a diagonal checker jump; 0 at Jump from ends; N exits. |
| Orbit | `J0:ORBIT` | Return advances instructions. Enter bomb angle 0-360 and distance in hundreds of miles. Ctrl-C exits. |
| Queen | `J0:QUEEN` | N skips rules. Enter a starting square (41 works), then queen moves. 0 forfeits; N exits. |
| Reverse | `J0:REVERSE` | N skips rules. Enter how many initial numbers to reverse. 0 quits the round; N exits. |
| Roulette | `J0:ROULETTE` | Enter date as month/day,year; N skips rules. Enter bet count then bet-code,amount. N ends; enter payee. |
| Slalom | `J0:SLALOM` | Enter gates 1-25, RUN, skill 1-3, then speed options 0-8. Ctrl-C exits. |
| Stock Market | `J0:STOCK` | N skips rules. Enter signed share transactions for five stocks. N ends after a trading day. |
| Trap | `J0:TRAP` | N skips rules. Give low,high bounds to trap a number 1-100; six guesses; N ends at replay. |
| War | `J0:WAR` | N skips directions. Y continues dealing; N exits. |
| Word | `J0:WORD` | Guess five-letter uppercase words; QUIT exits. Y/N at replay. |
| Yahtzee | `J0:YAHTZEE` | N skips comments; enter players and names; N skips optional scorecard. Choose dice to change and scoring row. Ctrl-C exits. |

## Qualification

Every addition accepted meaningful gameplay input, exited to I0:WORK and
recovered from a separate caller disconnect at an input prompt under RCP/M
v1.0, CP/M 3, Z3PLUS/BYE, 4 MHz, direct TCP. These are opening/turn/session
tests, not full playthroughs or coverage of all random branches and printer
choices. Ctrl-C is the tested exit where a convenient quit was unavailable.
A runtime STOP at an address can be a normal return to WORK. Wait for an
input prompt before sending exit keys.

Hockey additionally completed a one-minute match, showed final statistics,
and exited normally. Hi-Q accepted the 23-to-41 peg jump. Baccarat played
and settled a winning hand. Crazy Eights drew a card; its additional play
check is recorded separately when available. Yahtzee rolled and scored a
Chance category, then advanced to the next turn. Test events and per-title
results accompany the ZIP; only protected programs/guides are on the image.

Hi-Q, Roulette and Yahtzee redirect LPRINT to the terminal. Hi-Q's opening
text is adjusted accordingly. Hockey's line 630 assist lookup used an
uninitialized J array; it now reads H(J-1), matching its other pass-history
lookups. All changes and source/build hashes are retained.

## Source recovery and reproduction

The CD-ROM was read by ISO-sector ranges. LBR members were extracted and
CrLZH checksums verified; the separately inspected ARC candidates passed CRC
checks. Selected MBASIC programs were loaded using a private MBASIC.COM and
saved with SAVE "NAME.ASC",A. The original members and resulting ASCII
listings are in the host ZIP's walnut-source directory, with archive/member
hashes and the 156-member inventory. Private interpreter/compiler disks are
not distributed.

The existing compile_basic.py pipeline builds standalone BASCOM /O programs
linked with OBSLIB.REL. Hi-Q, Roulette and Yahtzee use --console-printer;
Hi-Q and Hockey use reviewed --source-overrides files. The required
Microsoft notice and original author/editor credits are retained.
The checked payload and build_image.py reproduce the optional disk
byte-identically from the released base; no source compiler is needed for
image reproduction.

CRAM36 relies on Bondwell memory-mapped graphics. POKIE4 and the separate
Beehive YAHTZE edition use Microbee graphics. They were inspected and not
ported or admitted. The native FOOTBALL archive was retrieved but has not
been runtime-qualified in this batch. None of these exclusions is counted
as an added game.
