# Upper user areas and Z-System utilities

Fresh-system profile: A: remains IBM3740 boot/caller media, I: remains the
existing 4-MB geometry, and B: is no longer runtime media. Existing B:/I2:
trials are preserved. `prepare_system_trial.py` creates new media only; it is
not an in-place database migration. Never run host image tools on mounted media.

The A0: SYS attributes are explicit build policy (`system_attributes.py`),
rather than inherited from the source disk. All approved caller programs,
including BYE, CLS and TYPE, plus -SYSTEM and WELCOME.TXT are DIR/visible.
PATH and boot support (BYEDRIV, CPM3.SYS, PROFILE.SUB, STARTZ3P, SUBMIT,
VT100DYN, Z3PLUS.COM/LBR and !(C)1988) are SYS/hidden. Only the SYS bit is
changed; read-only and other attributes are retained. The builder verifies
the result. Caller-tool installation and boot-only updates of this profile
reapply the policy after replacing files, so they do not undo the layout.
The raw cpmtools builder now includes cpmchattr for these operations.

| DU | Name | Caller access |
| --- | --- | --- |
| I0: | WORK | Disposable working files; cleared at call boundaries |
| I13: | SYSUTLS | Denied, including explicit DU/FCB access and execution |
| I14: | HELP | Read-only; basic caller topics installed |
| I15: | RBBS | Denied except data operations by the trusted board |

The preserved RBBS executable/static files occupy A15:, and its database
occupies I15:. The private RBBS alias changes to A15: before loading RBBS37.
The BYE application exception records that user area, so it cannot open I13:.
Legacy A2:/I2: trials retain their existing exception and protections.
Names are limited to seven characters to leave room for `-NAME` marker files.
Fresh builds install authored HELPC plain-text topics from `guest/help/` via
`caller_help.py`, including the default HELP.HLP index. Topics cover commands,
mounting, libraries, transfers, RBBS, games, WORK and logoff.
The default Z3PLUS descriptor already reserves 14 names. The eight selected
names fit that allocation; the builder expands the library's NDR member to
two records and checks it against the configured memory capacity.

## Private tools

All former B: maintenance programs move to I13:, including stock DRI PIP.
The sysop editor is `SYSUTLS:ZDE` (ZDE 1.6), configured through its original
ZDENSTAL installer for ANSI standard / VT100-compatible terminals. It uses
WordStar-style keys: Ctrl-K X saves and exits; Ctrl-K Q abandons editing.
The supplied ANSI profile's extra Ctrl-K arrow assignment is disabled so it
does not swallow the WordStar prefix; cursor visibility uses VT100 CSI codes.
For example, blank the caller, then use `SYSUTLS:ZDE A0:WELCOME.TXT`.
ZDE is not an approved caller program. DRI ED remains available as well.
While a caller is blanked, BYE now passes local control keys through to the
application except Ctrl-B (the blank toggle). This includes ZDE's Ctrl-Q
prefix and Ctrl-G/N/O. In shared mode the historic BYE hotkeys remain active.
To use BYE's Ctrl-N disconnect hotkey, return to shared mode first.
Keep the caller blanked throughout private editing and saving; unblanking
revokes A: write access. After Ctrl-K S saves, Ctrl-K X can ask
`Unchanged; save? (Y/N)`; N exits without a redundant save.
On older running BYE builds, Ctrl-Q can enter the sysop-message loop;
Ctrl-X leaves it. If editing responds only with the caller unblanked, rescue
the text with Ctrl-K, plain N, `I0:RESCUE.TXT`, then Ctrl-K, plain X.
Blank again at CP/M and run `SYSUTLS:PIP A:WELCOME.TXT=I:RESCUE.TXT`
before ending the call (WORK is disposable). This rescue was verified on the
old build. Stop with SYSUTLS:BYEBYE, run Update-RCPM.command, and restart.
That boot-only fix preserves the customized welcome file and all data disks.
The complete original ZDE16.LBR and release notes accompany the editor in
SYSUTLS:, retaining the distribution and copyright notices. Its author prohibits
commercial distribution. Sources/hashes are in `zde-reference-sources.json`;
`build_sysop_editor.py` runs the original terminal installer without modifying
the archived originals. This editor is a 1990 revision.
CP/M 3 GET.COM also moves from A0: to I13:. A0:STARTZ3P.COM uses
`A0:PATH /C A0;I13:GET CONSOLE;A0:;A0:BYE`, explicitly restoring A0:
after input redirection is reset and before BYE starts. This relocation applies
to fresh upper-area builds; existing mounted installations are not modified.
STARTZ3P and Z3PLUS.LBR remain on A0:. Caller writes to A: are denied,
and neither startup alias nor Z3PLUS loader is a caller-approved executable.
SYS attributes affect display, not these access controls.
PPIP 1.8 is added under its own name, with original documentation. Its build
enables ZCPR3 and disables DateStamper/Z80DOS extensions, which are not the
CP/M 3 timestamp interface. The build uses preserved M80/L80 under CP/M.
Sources and upstream binaries are hash-pinned in `ppip18-reference-sources.json`.
PPIP is copyrighted freeware restricted against commercial use/monetary gain;
do not describe it as unrestricted public-domain or change its license.

Additional preserved utilities from the pinned RomWBW inventory are installed
privately: PWD, FF, ZSHOW, ZHELP, LBRHELP, LPUT, ZLT, LX, NAME, ARUNZ, IF and
VIEW. This is an operator toolbox, not public command approval. In particular,
LX can execute library members, LPUT modifies libraries, NAME edits directory
names, and ARUNZ/IF interpret command sequences. Inclusion does not establish
that every function of every utility has been qualified under CP/M 3.
Their source URLs and exact binary hashes are in `zsystem-tool-sources.json`.

Local private mode searches A0: then I13:; caller mode searches only A0:.
BYE updates the path through the validated Z3PLUS environment when it changes
the wheel state. The existing program/file guards remain the authority.
Use `SYSUTLS:PIP`, `SYSUTLS:PPIP`, `SYSUTLS:RBBS` and `SYSUTLS:BYEBYE`
explicitly when useful in private operator mode. Callers use `RBBS` on A0:;
this fixed launcher grants only the trusted board load and no wheel access.
Unblanking from a private DU recovers to A0:.

## Caller aliases and public utility review

Useful initial aliases are VOLUMES -> MOUNT /L, LOGOFF -> BYE, and TOPICS ->
the help-topic directory. They are proposals, not installed caller commands.
Compiled fixed aliases are preferable for the first two; they need no writable
alias database or public general-purpose command interpreter. Any installed
alias must be immutable and explicitly admitted by the caller loader; its
target must also pass normal authorization. Parameter expansion needs separate
qualification before offering DOWNLOAD or other argument-taking aliases.

Fresh builds now install these reviewed caller commands:

| Command | Preserved implementation | Examples |
| --- | --- | --- |
| DIR and SDZ | SD 1.37 configured for Z-System | `DIR HELP:`, `SDZ I14:`, `DIR P:` |
| HELP | HELPC 1.4 (RomWBW ZHELP binary) | `HELP`, `HELP topic`, `HELP //` |
| LDIR | LDIR-B 1.5 | `LDIR J:LIBRARY`, `LDIR VOLUME:LIBRARY` |
| LT | ZLT 1.5, installed under the shorter caller name | `LT J:README.TXT`, `LT J:LIBRARY README.TXT` |

HELP's configured alternate directory is HELP: (I14:); its default topic is
HELP.HLP. I14: remains unpopulated in the fresh profile. No help content is
implied by installing the viewer. Original CP/M DIR/HELP are retained privately
as I13:CPMDIR.COM and CPMHELP.COM. The original ZLT also remains private.

`build_caller_tools.py` builds SD from pinned SD137 source using native M80/L80.
The RCP/M configuration enables NDR, environment wheel/max drive/user and drive
vector support. Disk listing output, printer output, disk reset, SYS-only/all
SYS listings and attribute selection are wheel-dependent. BYE's DU/FCB guards
remain authoritative for private areas. Free-space and cumulative matched-size
values use 24-bit kilobytes instead of wrapping at 65536 KiB under CP/M 3.
Preserved source and upstream RCP/M notes are pinned in
`sd137-reference-sources.json`; LDIR source/docs in
`ldir-reference-sources.json`; installed binary hashes in
`caller-tool-binaries.json`. ZLT/HELPC copyrights permit non-profit use; retain
their notices. These revisions span later CP/M years, not exclusively 1983–86.
No library execution or extraction command is admitted by these additions.

The sign-on text is maintained in `guest/welcome.txt`, installed as
A0:WELCOME.TXT, and displayed through BYE510's original WELFILE feature.
The configured FCB names WELCOME.TXT exactly. Upstream's WELCOME.??? wildcard
can select ZDE's earlier WELCOME.BAK directory entry, displaying a stale banner.
Backups remain intact; they are not considered sign-on text. After deploying
the fixed BYE, saved changes to A0:WELCOME.TXT take effect on the next call
without another restart. The existing boot-only Update-RCPM.command installs
the fix without replacing either welcome file.
It names only installed caller commands and explains WORK cleanup. Return-key
connection instructions belong in setup notes because the banner is displayed
only after carrier/baud detection. `WELCOME.TXT` is caller-readable but A:
mutation restrictions prevent callers from changing it.

## Reproduce a fresh build

First build the normal runtime/cpmtools and regenerate BYE with this revision:

```sh
python3 prepare_bye5.py --reference /path/to/pristine/bye510
python3 build_bye5.py --source /path/to/z80pack
python3 build_ppip.py --source /path/to/z80pack --fetch
python3 build_caller_tools.py --source /path/to/z80pack --fetch
python3 build_sysop_editor.py --source /path/to/z80pack
python3 prepare_system_trial.py --source /path/to/z80pack \
  --romwbw /path/to/RomWBW --fetch --output /path/to/new-system
```

The output must not already exist. It uses loopback raw TCP port 4002.
Run its Start-RCPM.command; attach SyncTERM, press Return until the prompt,
then enter RBBS at the caller's CP/M prompt. For private SYSOP login, blank
locally before starting the board and keep the caller blanked during that login.
Leave RBBS with J before local maintenance. Use SYSUTLS:BYEBYE to stop.
The launcher selects 4 MHz, matching BYE's MHZ equate. An unlimited-speed
qualification run disconnected during initial baud detection; it is not a
supported substitute for this launch setting. Utility copying itself was
qualified at 4 MHz. Default-unlimited bare cpmsim startup needs separate work.
Existing trial users/messages are not imported by this fresh-build command.
P: is empty; the offline BUILD image remains outside the public mount collection.

To update an existing **stopped** upper-area direct-TCP installation without
replacing its BBS database, first prepare an unbooted release using
`--output build/caller-tools-final`, then run:

```sh
python3 upgrade_caller_tools.py --instance /path/to/existing-trial
```

Leave RBBS with J, blank locally, and run SYSUTLS:BYEBYE before updating.
The updater refuses a held console lock, verifies the board and release, backs
up A:/I:/manifest, preserves I15: entries and allocated data, adds the private
GET dependency first, then installs the boot disk with matching BYE policy,
caller programs and banner. Account/password host files and J:/P: are untouched.
Custom STARTZ3P aliases require a manual merge; an existing customized ZDE is
also preserved by refusing to replace it. Restart the existing launcher.

`check_caller_tools.py --instance /path/to/disposable-trial` adds test-only HELP,
library and large P: fixtures. It tests named/numeric directory syntax, HELP
fallback, library listing/text/decompression, private-area denial, wheel-gated
listing output, banner display and unchanged A:/J:/P: during caller use.
Never run this fixture builder against a real installation.
`check_sysop_editor.py --output /path/to/new-test` uses copied A:/I: disks to
test private ANSI editing, saving, and caller denial.
The expanded private-console regression also saves A0:WELCOME.TXT with the
caller continuously blanked, exercises quick/format/edit control keys, checks
that no private text reaches the caller, and verifies unblanking and shared
Ctrl-Q message entry still work. Results: `build/private-console-keys-verified`.
The equivalent tcpser/IP232 regression passed in
`build/private-console-keys-ip232-final`.

Validation for this integration: `build/caller-tools-check3/caller-tools-result.json`
records caller viewer tests, including a real 68-MiB set of matched files on
P: (69632K matched, 454400K free). SD's build reproduced byte-identically.
Both transports passed the full RBBS registration/post/read/reconnect checks
in `build/caller-tools-rbbs-checks`. `build/sysop-editor-final-check/result.json`
records ANSI editing/saving and caller denial. The stopped updater also passed
against that populated RBBS fixture with byte-identical I15: directory entries
and allocated file contents, plus an unchanged host credential file.

Qualification, on disposable images, uses:

```sh
python3 check_rbbs.py --source /path/to/z80pack --romwbw /path/to/RomWBW \
  --tcpser /path/to/tcpser --upper-areas --tools --output build/upper-checks
```

This checks both transports, a test-only BDOS probe for private user areas and
HELP read-only access (including all-user directory searches), named/numeric
PPIP copying with CRC, exact extracted binary contents, stock PIP copying,
extended NDR lookup, the sysop path, unblank recovery from I13:/I15:, and
RBBS registration, post/read persistence, J/G and carrier-loss recovery.
The test's CLS replacement and HELP topic do not go into the fresh profile.
