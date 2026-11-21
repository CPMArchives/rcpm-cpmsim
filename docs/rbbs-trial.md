# RBBS 3.7 evaluation

This separate, loopback-only trial evaluates the preserved compiled RBBS 3.7
under CP/M 3, Z3PLUS and BYE510. It does not replace the operator's current
installation. In the upper-area profile callers now enter with A0:RBBS;
the data and sysop tools remain private. This remains a loopback evaluation,
with public-service deployment and board policy configuration still pending.
Use invented credentials while the board configuration is being settled.

## Build

Build the shared runtime and BYE as described in `shared-services.md`, including
regenerating BYE sources with the current `prepare_bye5.py`. Then:

```sh
python3 prepare_rbbs_trial.py --source /absolute/path/to/z80pack \
  --romwbw /absolute/path/to/RomWBW --fetch --output ../rcpm-rbbs37-trial
```

Downloads are checked against `rbbs37-reference-sources.json`. No archived
accounts, messages or passwords are imported. Existing trial directories are
never replaced. This repository records source URLs/hashes and installation
steps rather than committing the third-party compiled programs or a populated
P: image.

## Start and try

1. Run the generated `Start-RCPM.command` in Terminal. It uses raw TCP
   `127.0.0.1:4002`, leaving the existing port-4001 trial available.
2. Connect SyncTERM to that address/port, connection type Raw. Press Return
   until the CP/M prompt appears.
3. In the upper-area profile, enter `RBBS` at the caller's CP/M prompt. Its
   fixed A0: launcher selects A0: first, then A15:, and starts the preserved
   RBBS37 program without wheel elevation. The retained legacy I2: evaluation
   still uses operator-started B:RBBS; public admission requires the new layout.
4. The caller can now sign on with an invented first/last name and
   password. For a new user, answer Y to registration and N to misspelling
   if the displayed name/city are correct.
5. `?` displays the menu. `E` enters a message, `R` reads it, `J` returns to
   CP/M, and `G` logs off. Answer the feedback question when leaving. Dates
   are entered in the period program's `MM/DD|HH:MM` format.

In the upper-area profile another visit needs only `RBBS`. The private B:RBBS or
SYSUTLS:RBBS entry remains available to a blanked local operator. The
BASIC interpreter/compiler and installation/maintenance programs are not caller
commands. Board-level SYSOP status does not grant BYE's wheel privileges.

## Disk layout

For the new I13:SYSUTLS/I14:HELP/I15:RBBS profile, see
[Z-System utilities and fresh-system build](zsystem-utilities.md). The layout
below describes the retained B:/I2: evaluation, not the upper-area profile.

| Area | Contents |
| --- | --- |
| A2: | Unmodified RBBS37.COM, BYE.COM, BOOTPWD and static display files |
| I2: (reserved BBS data) | Fresh USERS, CALLERS, LASTCALR, COUNTERS, SUMMARY, MESSAGES, COMMENTS and lower-case `pwds` |
| B0: | Private RBBS alias, RBBSINST.COM/HLP, RBBSUTIL.COM |
| I0:WORK | Existing disposable work area; BBS data does not go here |
| P: | Empty distributable archive, unchanged |

The BASIC source assigns DSK$=A:. BOOTPWD assigns DSK2$/DSK3$=I:. All data
uses user 2. The installer creates period-format random records (62-byte user,
60-byte caller, 65-byte message and 30-byte summary records) with empty counts
and terminal markers, rather than reusing historical users. `pwds` is genuinely
lower-case in the directory, as required by this release; lower-case naming
is not considered an access-control mechanism. Generated board passwords are
stored in the owner-readable `rbbs-trial-passwords.json` inside the trial.
RBBS stores period-format account data; use test passwords during evaluation.

The BBS name/directory permissions are not yet added to the public named-
directory table. Merely assigning I2: a name would not protect its contents.

### Planned upper user areas

The operator has selected I13:SYSUTLS, public read-only I14:HELP and private
I15:RBBS. The fresh-system builder implements those assignments, including
matching A15: board files, private file/execute checks and the sysop path.
The existing evaluation remains on I2: until a stopped-system migration
preserves its database. The boot-only updater does not relocate database
files. HELP topic content and selection of a public Z-System help reader
remain integration work.

## Compatibility work

Initial testing found a pre-existing relocation error in our BYE adapter.
RMAC's forward EQU aliases for MAXDRIV/MAXUSER/MSPEED assembled references to
the RSX base instead of the allocated adapter variables. A captured guest
showed CARCK storing both limits at C900h, while the BASIC runtime used nearby
memory for its stack. This caused remote output/input to fail with BASIC file
errors, hidden by RBBS's ON ERROR handler. Direct references to WXDRIVE/WXUSER/
WXSPD give LINK the correct relocation information. The fix is in the BYE
source preparer, not in BDOS, cpmsim, or RBBS.

Speculative register-preservation and serial-status changes did not resolve
the failure and are not incorporated. The preserved RBBS program is unmodified
in the trial. Diagnostic builds/replaced programs were confined to throwaway
qualification images.

Verification passed on both direct TCP and real tcpser/IP232: fresh account
registration, posting, retrieval after leaving/re-entering RBBS, persistent
I2: storage after logoff, J to CP/M, G invoking BYE and disconnecting the
caller, and modem rearming. B:PIP and A2:RBBS37 remained denied at the caller
prompt after the board returned. The existing full caller-execution/private-B
checks also passed on both backends with the corrected BYE builds.

Reproduce the application checks on fresh diagnostic images:

```sh
python3 check_rbbs.py --source /absolute/path/to/z80pack \
  --romwbw /absolute/path/to/RomWBW --tcpser /absolute/path/to/tcpser \
  --output build/rbbs37/qualification
```

Omit `--tcpser` to check direct TCP only. The check refuses to overwrite a
previous results directory. Its accounts/passwords are synthetic. No test
program replaces an approved public command in these final checks.

Still required for production: review of RBBS's internal program chaining and exits, carrier-loss
recovery during database updates, and configuration of board policies.

## Private I2: and corrected directory prompts

The BYE BDOS interceptor denies ordinary caller file access to I2:, including
explicit I: requests from another drive's user 2 and whole-directory searches
that could enumerate other I: user areas. A local private sysop retains access.
The application exception is narrow: after a successful, locally authorized
BDOS 59 load of A2:RBBS37.COM, that trusted program may access I2:. No wheel
privilege or B: access is granted by this exception. Its installed executable
and static files remain on caller-write-protected A:.

BYE clears the application context on warm boot, call recovery and subsequent
program loads. J therefore returns to the normal caller boundary. G and carrier
loss prepare a new call without retaining BBS data access. The checks exercise
all three paths, including a dropped connection while RBBS is active.

The CCP previously displayed B0: after BDOS rejected B: selection, even though
the actual selected drive remained A:. A forbidden drive/user selection now
prints `Directory access denied.`, selects A0: through native BDOS, resets the
login byte, clears pending commands and aborts to the normal warm boot. The
previous directory is not a safe fallback: when the sysop releases private
mode while in I2: or B0:, it becomes forbidden and would cause an endless
warm-boot/denial loop on both shared consoles. The recovery now settles at
A0:SYSTEM>. Tests reproduce the old loop and exercise unblanking from both
private directories with both transports. FCB-level denials still return
file-operation errors, so explicit `B:PIP` remains rejected normally.

This remains guest policy for approved code, not isolation against arbitrary
machine code, direct BIOS access or modifications made by the owner.

## Update an existing evaluation without losing its database

To add caller entry to an older operator-only upper-area evaluation, stop CP/M
first: leave RBBS with J, blank locally, then run SYSUTLS:BYEBYE. Run the
instance's `Enable-RBBS.command`, then `Start-RCPM.command`. This is a boot-disk
update, not a fresh installation: it retains accounts, messages and passwords.
The updater admits only the reviewed policy transition that adds RBBS to the
previous command list, checks the installed board and alias template hashes,
saves a rollback copy of A:, and refuses the active console lock. I:/J:/P:
are not opened for writing. Ordinary later boot updates use Update-RCPM.command.

Alternatively, from this repository after stopping the upper-area system:

```sh
python3 upgrade_bye5_trial.py --instance /absolute/path/to/upper-area-system --enable-rbbs
```

The updater requires a stopped, direct-TCP trial with the matching approved
caller policy. It acquires the same exclusive console lock as the launcher,
verifies the corrected build hashes and installed COMs, and saves a rollback
copy of A: under `backups/` before replacing the boot disk. It does not write
B:, I:, J: or P:. Existing users, messages and board passwords are retained.
Tests verify refusal while the console lock is held and unchanged data disks.
Legacy B:/I2: installations require their separate layout migration first;
Enable-RBBS refuses them instead of exposing an additional board source.

To roll back, stop the guest and restore the recorded backup to
`disks/drivea.dsk`. Neither update nor rollback should edit a mounted image.

### Public launcher permission

Loading the immutable A0:RBBS.COM launcher successfully arms permission for
the next program-load attempt to load only A15:RBBS37.COM. Legacy A2: is not
admitted by this permission.
The pending permission survives the fixed alias's CCP warm boots; any next
load attempt consumes it, including a failed or different executable request.
Call reset/carrier recovery clears it. Only a successful trusted board load
activates private data access; loading the launcher alone grants no data,
SYSUTLS or wheel access. J, G and carrier loss clear active board access.
The preserved RBBS executable is unchanged. The launcher accepts no executable
name or command template from the caller.

The security checks use separate test-only launcher/board stand-ins to verify
that an unrelated load cannot use the permission, a different attempt consumes
it, returning from the board clears access, and carrier loss revokes an unused
permission. Real-board checks use the pinned alias and unmodified RBBS for
caller entry from WORK:, registration, posting, retrieval, J/G and reconnects
with both transports. Use --operator-entry for the original private-entry check.

## Validate a new member

RBBS membership is independent of BYE's wheel. The original RBBS 3.7 manual
describes validation under the sysop's expanded P command; the preserved
source implements it at lines 6640–6700 and 7550–7660. RBBSUTIL maintains
messages and does not provide the user-validation procedure.

1. Keep the remote console blanked during account administration: the period
   program displays the selected account's password.
2. Start RBBS privately (`B:RBBS` in the old evaluation or `SYSUTLS:RBBS` in
   the new profile). At FIRST Name enter SYSOP; at LAST Name enter the
   `rbbs_sysop` value in the instance's `rbbs-trial-passwords.json`.
3. Enter P at the board's command prompt. Supply the member's first/last
   names. Choose V at `Change <P>assword or <V>alidate this user ->`.
4. At the authorization prompt use the JSON file's `validation` value.
   Choose V for normal validated membership, S for board-level super-user
   status, or T to mark the account as a twit. V is the ordinary admission.
5. Press Return at the next user's first-name prompt to return to the menu.
6. Leave the RBBS sysop login with J before unblanking. BYE's wheel change
   does not sign the board's SYSOP account out. If resuming the caller's
   board session, restart RBBS privately and unblank at FIRST Name instead.

Credentials are generated per installation; the archived source's default
passwords are not the installation's passwords. Do not enter the sysop's own
surname at LAST Name: that prompt is the sysop password entry. Board
super-user status does not enable BYE's wheel.

### Pasting passwords at the local console

A disposable local-login check reproduces a 24-character burst being consumed
as 12 mask characters. Pacing the same credential succeeds. This is an input
delivery issue, not evidence that RBBS limits passwords to 12 characters.
Use `Login-SYSOP.command` from a second macOS Terminal while the console is
blanked and RBBS is at an empty FIRST Name prompt. The helper matches the
trial's current cpmsim tmux pane by working directory, checks the latest
remote-off state and current prompt, then types SYSOP and the saved credential
at a controlled pace. It never prints the credential or edits mounted media.
It also accepts an empty LAST Name prompt after SYSOP was entered manually.
It refuses ambiguous panes or other prompts without sending keys.

The helper uses the password file belonging to that particular trial. Fresh
trials generate different passwords; do not reuse another trial's JSON file.
New generated sysop passwords begin with a letter because this RBBS rejects
LAST Name values lexically below A before testing sysop authentication.

Reproduce the local burst/paced test on disposable media:

```sh
python3 check_rbbs_login.py --source /path/to/z80pack \
  --romwbw /path/to/RomWBW --output build/rbbs-login-check
```

The guest receives the helper's actual paced keystrokes. A substituted tmux
transport bridges to that test PTY because workspace policy blocks host tmux
sockets; the host pane-discovery integration still needs the operator's check.

### Pause and live sysop messages

CP/M's Ctrl-S output pause resumes with Ctrl-Q sent from the caller terminal
(SyncTERM). RBBS's displayed S/K pause/abort instructions describe its own
application handling; they do not release a CP/M output stop.

On the local console, BYE assigns Ctrl-Q to its separate live `Message from
Sysop` mode. Exit that mode with local Ctrl-X. If the interrupted output is
still stopped, send Ctrl-Q from SyncTERM; local Ctrl-Q can enter the live
message mode again. The `check_rbbs_login.py --chat` check verifies local
Ctrl-Q entry, text echo and Ctrl-X return to the interrupted RBBS prompt on
disposable media. It does not diagnose every possible nested pause state in
an existing session.

`check_console_flow.py` separately reproduces caller Ctrl-S during CP/M text
output, ordinary local keys beeping while stopped, local Ctrl-Q entering the
live message mode, and Ctrl-X leaving it with the original pause intact.
Caller Ctrl-Q resumes the original output. Local Ctrl-N is BYE's forced
hang-up key: it disconnects and rearms answering rather than just ending chat.
Neither behavior requires restarting the emulator.

```sh
python3 check_console_flow.py --source /path/to/z80pack \
  --romwbw /path/to/RomWBW --output build/console-flow-check
```

The fixture uses TYPE's `[NO PAGE]` option so its separate page-at-a-time
Return prompt cannot be mistaken for XOFF. No live system is changed.
