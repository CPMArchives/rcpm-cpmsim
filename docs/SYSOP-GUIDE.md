# HUMONGOUS RCP/M — Sysop's Guide

*For the released RCP/M 1.2.2 system • November 2026*

This is the maintained edition of the manual. It describes the released system, not features still under development. Check the [release notes](RELEASE-NOTES-1.2.2.md) if your installation differs.

## Contents

- [1. So you've decided to run an RCP/M](#1-so-youve-decided-to-run-an-rcpm)
- [2. Making the first call](#2-making-the-first-call)
- [3. Host configuration](#3-host-configuration)
- [4. At the sysop's console](#4-at-the-sysops-console)
- [5. A tour of the disks](#5-a-tour-of-the-disks)
- [6. Putting together a software collection](#6-putting-together-a-software-collection)
- [7. Giving directories names](#7-giving-directories-names)
- [8. Deciding what callers may do](#8-deciding-what-callers-may-do)
- [9. Approving programs for online use](#9-approving-programs-for-online-use)
- [10. Running RBBS](#10-running-rbbs)
- [11. Making the system your own](#11-making-the-system-your-own)
- [12. Transfers and incoming software](#12-transfers-and-incoming-software)
- [13. A word with the caller](#13-a-word-with-the-caller)
- [14. Backups, shutdown and recovery](#14-backups-shutdown-and-recovery)
- [15. When something goes wrong](#15-when-something-goes-wrong)
- [16. Inviting callers from elsewhere](#16-inviting-callers-from-elsewhere)
- [17. Keeping up with new releases](#17-keeping-up-with-new-releases)
- [Further reading](#further-reading)
- [Acknowledgements](#acknowledgements)
- [Appendix: AUTH command reference](#appendix-auth-command-reference)
  - [A.1 Starting AUTH safely](#a1-starting-auth-safely)
  - [A.2 The permission model and shipped defaults](#a2-the-permission-model-and-shipped-defaults)
  - [A.3 Reading the map and querying targets](#a3-reading-the-map-and-querying-targets)
  - [A.4 Setting drive and DU permissions](#a4-setting-drive-and-du-permissions)
  - [A.5 COM-file execution and F4](#a5-com-file-execution-and-f4)
  - [A.6 Live settings, saved files and startup](#a6-live-settings-saved-files-and-startup)
  - [A.7 Scripts, explicit filenames and overwrite authorization](#a7-scripts-explicit-filenames-and-overwrite-authorization)
  - [A.8 Worked policy workflows](#a8-worked-policy-workflows)
  - [A.9 Backups, failed saves and recovery](#a9-backups-failed-saves-and-recovery)
  - [A.10 Troubleshooting](#a10-troubleshooting)

## 1. So you've decided to run an RCP/M

Forty years ago, this would have meant setting aside a computer, buying a modem, arranging for a telephone line and spending a good many evenings persuading the various pieces of software to cooperate. Fortunately, most of that work has already been done for you.

HUMONGOUS RCP/M is a working CP/M computer, not simply a bulletin board with a CP/M theme. Callers can explore its disks, read documentation, exchange software, play approved games and visit the board. What sort of collection and community you build is up to you.

This guide assumes you know your way around CP/M and a host command line. If you would like a refresher on the caller's side of the system, see the companion [User's Guide](USER-GUIDE.md). It deals with the peculiarities of running this particular RCP/M. For exact disk geometry and host-side image tools, keep the [Disk Images reference](../packaging/DISK-IMAGES.DOC) handy. The [Installation notes](../packaging/INSTALLATION.DOC) cover platform-specific startup matters.

Under the bonnet is a customized version of Udo Munk's cpmsim, from the [z80pack project](https://github.com/udo-munk/z80pack), emulating a Z80 computer running banked [CP/M 3](https://www.cpm.z80.de/drilib.html). Our version adds facilities specifically for RCP/M, including the caller connection and shared sysop console, swappable library volumes, and the host-side services used to receive uploads and saved messages. These facilities work in conjunction with the adapted guest software. Use the cpmsim executable supplied with HUMONGOUS RCP/M rather than substituting a stock z80pack binary; the two are not interchangeable for this system. [Z3PLUS](https://manualzilla.com/doc/6919195/z3plus-user-s-manual) supplies the command environment and named directories. [BYE510](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/bye5/bye510/) handles remote operation, and [RBBS](#10-running-rbbs) provides forums and private mail.

We've also written several utilities specifically for HUMONGOUS RCP/M. [AUTH](#appendix-auth-command-reference) gives the sysop control over caller permissions and program approval. [MOUNT](#6-putting-together-a-software-collection) lets callers exchange software library volumes without restarting CP/M, and [NDSCAN](#7-giving-directories-names) updates the named directories to reflect the contents of a mounted disk. These three utilities are original contributions of this project, rather than adaptations of historical CP/M programs.

The normal emulated CPU speed is 4 MHz; changing it affects program timing, not just the apparent speed of the connection.

You and the caller share this one machine. There is one caller at a time, alongside your local console. Bear that in mind whenever you sit down to do some maintenance.

## 2. Making the first call

Obtain the complete package for your host from the [release page](https://github.com/CPMArchives/rcpm-cpmsim/releases/tag/v1.2.2). Unpack it into a writable directory. On macOS run `Start-RCPM.command`, on Linux `Start-RCPM.sh`, and on Windows `Start-RCPM.cmd`. There is no setup wizard and no initial configuration is required. Docker users should follow the [Docker instructions](docker.md); the CP/M side is the same.

The first startup generates the private file SYSOP.DOC in the installation directory. This contains your initial board credentials. It is **not** the Sysop's Guide and should never be made available to callers.

When the modem is ready, call your own system using a terminal such as [SyncTERM](https://syncterm.net/). Select raw TCP, address 127.0.0.1, port 4000. Press RETURN. Try:

    HELP
    DIR SIGM:
    DIR CPMUG:
    MOUNT /L
    RBBS

Register an ordinary account, enter a message, read it back and leave the board with C. At CP/M, type BYE. Call again. You have now seen the machine from the other end of the connection, which is a useful habit for a sysop to cultivate.

## 3. Host configuration

The external RCPM.CONF is deliberately small and commented. Stop the machine before editing it.

| Setting | Default | Purpose |
| --- | --- | --- |
| MODE | direct | Direct raw TCP; ip232 selects the bundled [tcpser](https://github.com/go4retro/tcpser) virtual modem |
| ADDRESS | 127.0.0.1 | Listener IPv4 address |
| PORT | 4000 | Caller port in either mode |

The launcher handles tcpser's internal endpoints automatically. Keep the distributed foreground terminal open while serving calls. If you use your own [tmux](https://github.com/tmux/tmux) wrapper, detaching is not shutting down. Docker uses its published port and persistent data volume; consult its guide before changing the container.

Running a second board is quite possible. Give it its own directory or Docker volume and a different caller port. Never share writable disk images between two running machines.

## 4. At the sysop's console

When a caller is online, your local keyboard and his remote keyboard ordinarily feed the same computer. Don't start a disk operation while someone is composing a message.

Use the following local BYE controls in shared mode:

| Key | Action |
| --- | --- |
| Ctrl-B | Blank the caller and enter private operation; again to unblank |
| Ctrl-G | Toggle the page bell and paging availability |
| Ctrl-Q | Enter sysop message mode |
| Ctrl-X | Leave message mode |
| Ctrl-N | Force caller hangup |

While blanked, most local control keys go to the application rather than BYE, except Ctrl-B. Finish private work, leave the application and return to A0: before unblanking. With a tmux wrapper, Ctrl-B Ctrl-B sends a literal Ctrl-B to the guest; the distributed launcher needs only one.

Between calls, local Ctrl-C opens BYE's menu. Select J to jump to CP/M with BYE attached if you intend to use AUTH. RETURN instead enters ordinary, unpatched CP/M; AUTH needs the resident interface, so don't confuse the two choices.

## 5. A tour of the disks

| Drive | Exact image bytes | Purpose |
| --- | ---: | --- |
| A: | 256256 | Boot and system disk |
| I: | 4177920 | Workspace, help, private utilities and board data |
| J: | 4177920 | Swappable software collections |
| P: | 536870912 | Large swappable archives |

The named directories are more useful than the bare drive letters:

| DU | Name | Contents |
| --- | --- | --- |
| A0: | SYSTEM | Public commands, boot files and WELCOME.TXT |
| A15: | — | Trusted board executable and static files |
| I0: | WORK | Temporary caller workspace |
| I13: | SYSUTLS | Private tools, including AUTH, PIP, PPIP, SET and ZDE |
| I14: | HELP | Caller-readable online documentation |
| I15: | RBBS | Private board records and message base |
| P0: | SIGM | SIG/M libraries on the default P: |
| P1: | CPMUG | CPMUG libraries on the default P: |
| J0: | VOLUME | Default J: volume directory |

WORK is cleared before answering, including startup and call recovery. Never leave your only copy of a rescued edit or a sysop document there. Uploads go to a separate host inbox, not a permanent CP/M UPLDS: directory.

## 6. Putting together a software collection

The default P: contains all 310 SIG/M and 93 CPMUG volumes. Browse a few of them before deciding what else your board ought to offer. You might specialize in a particular computer, programming language, or collection of games.

Put small raw z80pack-hd images in `disks/library/` and large raw z80pack-hdb images in `disks/library/archives/`. Catalog names are one to eight letters, digits or underscores, followed by .dsk. A filename extension is no guarantee of disk geometry. Prepare images with the matching format in the [Disk Images reference](../packaging/DISK-IMAGES.DOC); simply padding or renaming an unrelated image won't convert it.

    MOUNT /L
    MOUNT J: /L
    MOUNT P: /L
    MOUNT GAMES
    MOUNT P: /DEFAULT
    MOUNT J: /DEFAULT

MOUNT chooses J: or P: by exact image size. If a name occurs in both catalogs, qualify it with the drive. The old image remains mounted if selection or buffer flushing fails. A successful mount relogs the selected disk and refreshes its names. Default images return when the emulator restarts, not necessarily when a caller logs off.

Keep private media outside the public catalogs (the supplied offline directory is one such place). A private image mounted in a caller-readable DU is no longer private simply because of where it came from. AUTH permissions follow the drive/user slot, not the volume.

Never host-edit an image while cpmsim has it open. Stop the board, keep a backup, and use the supplied disk tools (based on [cpmtools](https://www.moria.de/~michael/cpmtools/)). Host file permissions and CP/M attributes are distinct from AUTH; an owner-writable image does not by itself grant callers write access.

The [GAMES collection](online-games.md) has preparation launchers in J0: for Adventure, Animals and Maze Chase. Try MOUNT GAMES followed by J0:ADVENT, J0:ANIMALS or J0:MCHASE. The launchers need readable/writable WORK for data; the approved game itself runs from a protected DU. Games that insist on writing to the library disk are better left for download and local play.

## 7. Giving directories names

A caller will remember INFOCOM: more readily than J3:. Create an extensionless marker file named -INFOCOM in the intended user area. Its contents don't matter. Use up to seven letters, digits or underscores after the hyphen.

    NDSCAN J:

NDSCAN rebuilds names for that drive alone, scanning users 0–15. MOUNT normally chains to NDSCAN after a swap. Areas without markers lose their old names. Duplicate names, multiple different markers in one user area, collisions with other drives or a full name table prevent the update. The supplied table holds 42 names. See [MOUNT and NDSCAN](swappable-volumes.md) for additional details.

If a mount succeeds but scanning fails, the new disk is mounted and the old names are still present. Use numeric DUs until you correct the markers and rerun NDSCAN, or restore the default volume. Callers need read access to every user area on a drive to scan it; private sysops can scan private drives.

Use PWD or ZSHOW for inspection. Don't use a bare NAME command to inspect a name: it can delete an entry. Names do not grant access.

## 8. Deciding what callers may do

An RCP/M gives strangers the use of a real computer. That's its attraction, and also the reason for taking permissions seriously.

AUTH lives in SYSUTLS:. With the caller blanked, or between calls with BYE attached, type AUTH /MAP. The map shows the effective read/write pair for each DU. An asterisk marks an explicit override; without it the DU follows the drive setting.

The shipped policy gives read access to A0:, I14:, J: and P:, read/write access to I0:, and denies other areas. In particular, I13: and I15: inherit I:'s denial. Don't casually grant access to all of I:; you would expose inherited private areas unless you explicitly protect them first.

Suppose you want to keep J3: out of sight:

    AUTH J: /R
    AUTH J3: /NONE

To remove that exception, use AUTH J3: /INHERIT. A drive change doesn't erase its DU overrides. Each permission argument replaces the entire pair: /W is write only, not an instruction to add write permission to read.

AUTH changes take effect immediately and survive calls. Save the map with AUTH /SAVE, accepting I13:AUTH.DAT, if you want it at the next startup. AUTH /LOAD restores a saved map. The [full reference in the appendix](#appendix-auth-command-reference) covers alternate policies, scripts and recovery.

## 9. Approving programs for online use

A disk full of useful CP/M programs is not necessarily a disk full of programs suitable for remote execution. Debuggers, memory editors and arbitrary loaders are obvious examples.

An ordinary caller COM load requires read access to its source DU, no caller write access to that DU, and F4 on the actual file. F4 is our approval convention, not a universal CP/M rule. For example, after reviewing Adventure on the mounted GAMES disk:

    AUTH J1:ADV.COM
    AUTH J1:ADV.COM +X
    AUTH J1:ADV.COM

Withdraw approval with AUTH J1:ADV.COM -X. These changes go straight to the disk directory; AUTH /SAVE and /LOAD affect permissions, not F4.

Clear inherited F4 flags when importing software. Review the actual binary and its options, including shell escapes and secondary loaders. BYE is not a sandbox for hostile Z80 code. See the [caller execution policy](caller-execution.md) and [security boundary](security-boundary.md) for details. Approving a program means trusting it. Individual file R/O and SYS attributes do not replace AUTH.

Don't give callers write access to A0: in an attempt to make a program work. That will prevent ordinary public COM loads. If it happens, restore AUTH A0: /R. A caller in writable WORK can still load approved commands from read-only A0:.

## 10. Running RBBS

The released 1.2.2 board uses RBBS 4.1 Edit 02. Our [RBBS integration notes](rbbs41-test.md) describe the adaptations to this version. Fresh boards contain PERSONAL, GENERAL, CPM and TEST areas, with one SYSOP seed account. New callers can register and post without prior validation.

### Getting in as sysop

Work at the private local console, not with the caller looking over your shoulder. Enter RBBS, give the name SYSOP and use the generated six-character password recorded in private SYSOP.DOC. Passwords are case-sensitive. The displayed 123456 is a character counter, not a password.

Normal menus accept a single key. Text, names and message numbers still require RETURN. Expert mode retains line commands and semicolon sequences such as R;1 and R;1+. End a message with a period on its own line, then S to save.

| Key | Main board function |
| --- | --- |
| F | Select forum |
| R | Read messages |
| S | Summarize |
| N | Read new messages |
| K | Delete an authorized message |
| C | Return to CP/M |
| G | Disconnect |

### Looking after the forums and accounts

From private CP/M run:

    SYSUTLS:RBUTIL41

The numbered maintenance menu offers 4 to select a forum, 5 to add a forum, 6 to manage users, and 9 to quit. **Option 3 resets the account database.** It is not an ordinary account-maintenance command. Back up before making significant changes.

Forum names have at most eight characters, and this released board supports eight areas total, including PERSONAL. Later RBBS revisions may differ; use their own documentation. A few active forums are much more inviting than a long list of empty ones. Choose subjects your callers are likely to care about, and put a welcoming message in each new forum.

Check new accounts and look in on the discussions. Answer questions when you can. Few things make a board seem more deserted than a question left unanswered for weeks.

The protected executable is A15:RBBS41.COM; accounts, callers, subjects, messages and associated data reside in I15:. The fixed public RBBS launcher grants only the access needed for the board. Do not make those areas public. Private mail is private from ordinary callers, not from the sysop or anyone with access to backups. Raw TCP is unencrypted.

Do not delete state/initialized to reset credentials. SYSOP.DOC records the original generated password. RBBS 3.7 and 4.1 data files differ; fresh release disks are not an in-place migration.

## 11. Making the system your own

The sign-on message should tell the caller where he's arrived and what he might find there. A few lines are often sufficient; regular callers needn't read several screens of announcements every time.

From private CP/M:

    SYSUTLS:ZDE A0:WELCOME.TXT

[ZDE](https://www.dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/zsystem/zde16/) uses WordStar keys: Ctrl-K S saves, Ctrl-K X saves and exits, Ctrl-K Q abandons changes. If an unchanged buffer prompts after a previous save, N exits without saving again. Keep the caller blanked throughout editing and saving. BYE displays WELCOME.TXT on the next call, not its .BAK file.

The HELP topics are in I14:HELP. DIR HELP: lists them; HELP GAMES opens a particular topic. The released 1.2.2 collection uses short ASCII topics beginning with a semicolon line, with CRLF and Ctrl-Z termination. The 1.2.3 source collection expands this to 120 linked and paginated help files, covering 63 installed command programs and 24 resident command entries. Its qualified links require the tested HELPC 1.5r viewer. `HELP COMMANDS` separates public and resident caller commands from `* SYSOP ONLY` utilities, resident commands and startup backends. `HELP GET` distinguishes the two private GET implementations; `HELP R` and `HELP RESET` distinguish disk reset from whole-machine reset. The labels document access; BYE policy and wheel restrictions enforce it. Maintain HELP privately, and put no passwords or installation-specific secrets in public topics.

## 12. Transfers and incoming software

Try at least one download and one upload yourself. There is no substitute for having seen the process from the caller's side when someone says his terminal has hung.

    YSEND A0:WELCOME.TXT
    UPLOAD EXAMPLE.LBR
    UPLOAD /Y

YSEND sends YMODEM; start the corresponding receive operation in your terminal. UPLOAD filename receives one file using XMODEM/CRC; UPLOAD /Y receives a YMODEM batch. Start the matching send operation at the terminal when prompted.

Completed submissions go to uploads/inbox/ on the host. In-progress files go to uploads/staging/. Keep both on the same filesystem: completion uses an atomic hard link. Duplicate names receive unique suffixes, rather than overwriting earlier submissions. Interrupted partial files are discarded; previously completed batch members remain. XMODEM retains record padding, while YMODEM retains the declared length.

MESSAGE notes saved by callers also arrive in the inbox. Unsaved drafts are discarded at call recovery. These files survive WORK cleanup and ordinary restarts.

Examine the actual contents of a submission, not just its filename. Check archive members, accompanying documentation and redistribution terms. Retain the original. Stop the board and back up the destination disk before importing reviewed files using the correct image format. Never place arbitrary uploaded files directly in the disk catalog, or automatically approve an uploaded COM file for caller execution.

## 13. A word with the caller

When paged by CHAT, answer with Escape on the local console. Both ends need an 80-column, 24-row ANSI/VT100 terminal for the split display. Your text appears above the caller's; the panes wrap and scroll separately. Backspace erases within the current line, Tab inserts spaces, and Ctrl-R redraws. Ctrl-C or Ctrl-X ends chat. CHAT /S provides the plain scrolling alternative.

A caller in RBBS must return to CP/M with C before invoking CHAT. Ctrl-G at the local console toggles paging availability. If you need to attend to private business, local Ctrl-B ends split chat and blanks the caller.

## 14. Backups, shutdown and recovery

BYE logs off a caller; it does not stop the machine. Between calls, use local Ctrl-C at BYE's waiting prompt, then RETURN for ordinary CP/M. From private local CP/M enter:

    SYSUTLS:BYEBYE

Wait until cpmsim has actually stopped. A blanked caller or an idle listener is not a stopped emulator.

Copy the whole installation to separate storage: disks/, the library catalog, uploads/inbox/, state/, RCPM.CONF and private SYSOP.DOC. In Docker, preserve the complete persistent volume while the board is stopped. A copy on the same disk is useful for recovery from mistakes, but not a substitute for a backup on separate storage.

Restore a complete snapshot into a new directory. Don't mix accounts and message files from unrelated dates. Stop the original before starting a restored copy on its port. Never bypass the installation lock or delete it to start a second guest on the same disks.

If WORK cleanup fails, the machine refuses to answer. Stop and repair the I: image or host write permissions before restarting.

## 15. When something goes wrong

| Symptom | First things to examine |
| --- | --- |
| Launcher won't start | Host permissions, occupied port, another running copy |
| Caller connects but sees nothing | Raw TCP rather than Telnet; press RETURN |
| DIR or LT works locally but not remotely | A0: caller read-only permission and F4 |
| Game won't prepare its files | MOUNT GAMES; I0: RW; approval of the actual game |
| Old names after MOUNT | NDSCAN errors, marker collisions |
| AUTH refuses to run | Private operation with BYE attached |
| AUTH settings vanish after restart | Saved I13:AUTH.DAT |
| HELP or board records missing | Correct I: image and DU permissions |
| Garbled CHAT | ANSI/VT100 setup, or CHAT /S |
| WORK files vanish | Expected at call boundaries |

Try to decide whether the trouble lies in the host, CP/M, BYE or a transient program. If a command works in private CP/M but not for a caller, look at permissions before rebuilding software. The [AUTH appendix](#appendix-auth-command-reference) goes into more detail about recovering a bad policy.

## 16. Inviting callers from elsewhere

Once you are happy with local calls, stop the system and change ADDRESS to the appropriate host IPv4 address, or 0.0.0.0 for all interfaces. Restart. The host firewall and router must permit the caller port. For Docker, arrange the host port publication instead; see the [Docker guide](docker.md).

Make a call from another computer before announcing the board. Raw TCP provides no encryption; advise callers not to reuse important passwords. Keep administrative tools and credentials private, approve only reviewed software, and retain a good stopped backup. Guest permission checks are not a substitute for securing the host itself.

Automatic startup, scheduled backups, monitoring and other unattended hosting arrangements are separate matters. Optional administration guides are available for [Linux](hosting-addon.md), [macOS](ADMINISTRATION-MACOS.md) and [Windows](ADMINISTRATION-WINDOWS.md). None is needed for ordinary foreground operation.

## 17. Keeping up with new releases

Don't unpack a new release over your board. Test it separately and follow its migration instructions. Preserve your accounts, messages, policy, credentials, uploads and custom software. Keep matching emulator and BYE driver versions together. Pulling a new Docker image doesn't automatically migrate an initialized volume.

CPMNet is not part of released 1.2.2; this guide describes local forums and mail only. Preserve the original component and archive notices when redistributing material. See the [distribution review](distribution-review.md).

## Further reading

For further historical reading, see the [RCP/M archive](https://www.dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/rcpm/), including Jon Schneider's 1985 RCP/M user's guide and period security notes. The [historical security review](historical-rcpm-security.md) explains how such material informs this distribution.

## Acknowledgements

HUMONGOUS RCP/M owes its existence to the work of a great many people, some of whom made their contributions more than forty years ago. Much of our work has been to bring their software together, adapt it to present-day computers and make it available to another generation of CP/M enthusiasts.

Our particular thanks go to Gary Kildall and the team at Digital Research for CP/M; Udo Munk for z80pack and cpmsim; Richard Conn for his pioneering work on ZCPR; and Jay Sage and Bridger Mitchell for Z3PLUS, with Joe Wright for his contributions to the Z-System.

We also owe a debt to Dave Jaffe, the original author of BYE, and to Wayne Masters, Irv Hoff, George Peace and the other contributors who carried its development forward; to the authors and maintainers of CP/M RBBS, whose work gives our callers a place to exchange messages; and to Jim Brain for tcpser, which allows us to recreate the modem connection without a telephone line.

Finally, our thanks to the many authors of CP/M utilities, the SIG/M and CPMUG librarians and contributors, and the archivists and volunteers who have kept this remarkable body of software and documentation accessible. Without their generosity and persistence, there would be very little for an RCP/M such as ours to offer.

The individual software distributions retain their original credits and notices.

## Appendix: AUTH command reference

This appendix gives the complete AUTH command reference for the released system, including policy recovery and scripting.

### A.1 Starting AUTH safely

With a caller connected, use local Ctrl-B to blank the caller and enter
private sysop mode. Then use SYSUTLS:AUTH, or simply AUTH if the private
command path is active. Keep the caller blanked throughout administration.
Return to A0:SYSTEM before pressing Ctrl-B again to restore caller operation.

If administering between calls, local Ctrl-C opens BYE's menu. Select J to
jump to CP/M with BYE attached. AUTH needs that resident BYE interface;
Return for normal unpatched CP/M removes it and is not the AUTH environment.

AUTH rejects administration outside private sysop mode, even if someone
copies AUTH.COM to a public DU and marks it executable. These permissions
control the caller, not the private operator. Private mode permits maintenance
on A:, I:, J: and P: through the same policy bypass. Genuine host read-only
media, ordinary CP/M file R/O attributes and other file errors still apply.

Display help with:

    SYSUTLS:AUTH //

Commands and filenames are case-insensitive. AUTH accepts one target per
invocation; use several commands in a SUBMIT file or alias for a sequence.

### A.2 The permission model and shipped defaults

D: means a drive, for example J:. DU: means a drive plus user area, for example
J3:. Each drive has a caller permission pair. Each DU either inherits that
pair or has an explicit replacement. The order is:

    explicit DU setting -> drive setting -> default NONE

An explicit DU setting always takes precedence, including an explicit NONE.
A drive change preserves existing DU overrides. There are no automatic private
exceptions for particular drive letters: SYSUTLS and RBBS data are private
because of the configured policy, with a separate controlled RBBS service grant.

The supplied startup policy grants:

    Scope                     Caller permission
    A0:SYSTEM                 R-  (public commands and banner)
    J: and P:                 R-  (public collections)
    I0:WORK                   RW  (temporary workspace)
    I14:HELP                  R-  (help topics)
    Other DUs                 --  (neither read nor write)

I13:SYSUTLS and I15:RBBS inherit I:'s NONE setting in that policy. If you grant
access to all of I:, those inherited DUs follow it too. To keep particular DUs
private under a broader drive grant, give them explicit NONE overrides first.
Keep the policy files and private board data protected against caller writes.

R permits file reading and directory browsing. W permits file mutations
through available programs. Write-only settings deny reading/listing; utilities
that require read access for file lookup may not work with a write-only DU.
RW is permission, not a supplied file-transfer or copy service: callers still
have no general copy command or direct upload into WORK in this package.
The game launchers seed WORK, and caller programs can create workspace data.
UPLOAD continues to use the private host inbox described in [Chapter 12](#12-transfers-and-incoming-software).

I0:WORK is cleared at startup and call recovery regardless of its AUTH setting.
Changing its permissions does not turn it into permanent storage.

### A.3 Reading the map and querying targets

    AUTH                      All drives, users 0-15
    AUTH /MAP                 Same complete map
    AUTH J:                   Only the J: row, users 0-15
    AUTH J3:                  Same complete J: row

These commands only display information. AUTH D: does NOT reset D: to NONE.
No permission change occurs without an explicit permission argument.

The map shows effective caller permissions for each DU. An asterisk before
the pair means that DU has an explicit override:

    *RW   Explicit read/write       *R-   Explicit read-only
    *-W   Explicit write-only       *--   Explicit denial
     R-   Read-only inherited from the drive (no asterisk)

A missing asterisk means inheritance, even when the inherited value is --.
The map does not show whether a disk is mounted or whether a particular file
exists. You can configure G3: even if no G: image is currently attached.

### A.4 Setting drive and DU permissions

Both slash syntax and map-style pairs are supported:

    Slash form       Map form       Also accepted       Result
    /RW              RW             RW                  Read and write
    /R               R-             R                   Read only
    /W               -W             W                   Write only
    /NONE            --             NONE                Neither

Every form REPLACES the complete pair. /W does not add W to an existing R;
it sets -W and removes read access. Likewise, /R removes write access.
Do not type the map's asterisk as part of a permission argument.

    AUTH J: /R                Set the drive's caller pair to R-
    AUTH J3: RW               Override J3: with read/write
    AUTH J3: /W               Replace that override with write-only
    AUTH J3: --               Explicitly deny both permissions on J3:
    AUTH J3: INHERIT           Remove its override; follow J: again

/INHERIT is equivalent to INHERIT and applies only to a DU. With J: set to R-,
J3: INHERIT becomes R- and loses its asterisk. Explicit J3: NONE remains denied
and keeps its asterisk even if the drive is readable. To deny a drive's base
permissions, use AUTH J: /NONE; that does not erase its explicit DU overrides.

Changes take effect in BYE's resident map immediately and survive caller
hangups. They remain unsaved until you use /SAVE. They are replaced by /LOAD
or by the next startup's saved map.

### A.5 COM-file execution and F4

Normal caller execution requires ALL of the following:

    - Read access to the executable's DU.
    - No caller write access to that DU.
    - F4 set on the actual COM file's directory entry.

The source DU matters, not the caller's current working directory. A caller
in writable I0: can run approved commands found on read-only A0:. The caller
cannot run a COM stored in writable I0:, even if it has F4 set. If you make
I0: caller-read-only, approved files there can run; they are still cleared
at call boundaries. Individual file R/O does not override the writable-DU ban.

All ordinary COM files use this rule, including public commands in A0:.
Setting A0: to RW therefore stops callers loading DIR, SDZ, LT and the other
COM commands there. Private sysop operation continues to work. To restore
normal caller commands, set AUTH A0: /R. See [A.10](#a10-troubleshooting).

Inspect, approve or revoke an existing exact filename:

    AUTH J1:ADV.COM            Report effective caller executable status
    AUTH J1:ADV.COM +X         Set F4; preserve other file attributes
    AUTH J1:ADV.COM -X         Clear F4; preserve other file attributes

The target comes first. AUTH +X J1:ADV.COM is not supported. These file commands
require a DU prefix, a COM extension and an exact name; wildcards are rejected.

Examples of status output:

    J1:ADV.COM is executable.
    J1:ADV.COM is not executable: F4 is not set.
    J1:ADV.COM is not executable: DU is caller-writable.
    J1:ADV.COM is not executable: no caller read access.
    J1:ADV.COM not found.

+X is approval, not a way to override DU permissions. F4 is our caller-approval
convention, not a universal meaning imposed by CP/M. Clear inherited F4 flags
when importing software, then approve reviewed programs deliberately. Individual
file R/O is optional for execution and retains its normal CP/M meaning. SET
can also manage F4 in private mode. SYS controls directory display, not
approval.

F4 changes are written directly to the file directory. They do NOT require
AUTH /SAVE. Conversely, AUTH /LOAD does not undo any F4 changes. If a copied
file retains F4, it still cannot execute while its DU is caller-writable.

Approval means trusting the program, including external loaders, interpreters,
shell escapes and direct memory/disk operations it may provide. BYE is not a
sandbox for hostile Z80 code. The reviewed RBBS entry has its own narrow grant
for the private board executable/data; do not make those DUs public to run it.

### A.6 Live settings, saved files and startup

BYE reads I13:AUTH.DAT into memory when its resident policy is initialized.
File checks use that memory table. AUTH's drive/DU commands update only that
table; they do not silently rewrite the startup file.

    /SAVE    Write the live drive/DU map to a chosen policy file.
    /LOAD    Validate a chosen policy file and replace the live map.

Saved files include drive settings and DU overrides. They do not contain
COM-file F4 approvals, accounts, passwords or disk images. Startup always uses
I13:AUTH.DAT; loading an alternate file does not change that startup filename.
Each interactive prompt still defaults to I13:AUTH.DAT, not the last-used file.
SAVE/LOAD always handle the entire map, not only the last drive you queried.
Policy files are binary; manage them with AUTH rather than a text editor.
Changing a saved file alone does not change the resident map until LOAD or
startup.

Bare forms prompt:

    AUTH /SAVE
    Save policy to [I13:AUTH.DAT]:

    AUTH /LOAD
    Load policy from [I13:AUTH.DAT]:

Press Return to select I13:AUTH.DAT, or enter an alternate filename. Saving
interactively asks before overwriting an existing file; answer Y to proceed
or N/Return to cancel. Cancelling leaves the destination unchanged.

Unqualified filenames use I13:, even if you started AUTH in another directory.
A drive-only prefix uses the current user area when AUTH starts; an explicit
DU selects that area. Scripts should use explicit DU filenames for clarity.
Names use exact CP/M 8.3 format and do not accept wildcards. These are CP/M
disk filenames, not host operating-system paths.

### A.7 Scripts, explicit filenames and overwrite authorization

    AUTH /SAVE=I13:PUBLIC.DAT
    AUTH /SAVE=I13:PUBLIC.DAT /Y
    AUTH /LOAD=I13:PUBLIC.DAT

With =filename these commands run without filename or overwrite prompts.
/SAVE=filename creates a new destination, but if it already exists the command
fails with "File exists; use /Y to overwrite." It does not wait for input.
Adding /Y authorizes overwrite and rotation of the prior same-basename backup.
/Y does not bypass private-mode checks, read-only media or file errors.
It is a SAVE option, not a LOAD option.

For normal startup-policy maintenance, a complete scripted save is:

    AUTH /SAVE=I13:AUTH.DAT /Y

AUTH reports success/failure and sets CP/M 3's program return code: 0000h on
success, FF01h on error or cancellation. How a batch file reacts depends on
its command processor/automation tools. A status query reporting that an
existing COM is not executable is a successful query; a missing file is an
error. Run scripts that administer policy only in private sysop mode.

AUTH flushes pending CP/M disk buffers before changing live DU permissions,
including /LOAD. If flushing fails, the live permissions remain unchanged.
There is no added delay or restriction on sysop permission choices.

### A.8 Worked policy workflows

Restore the normal public system directory and temporary workspace:

    AUTH A0: /R
    AUTH I0: RW
    AUTH /SAVE=I13:AUTH.DAT /Y

Try a temporary change without making it the startup policy:

    AUTH G3: RW
    AUTH G3:
    AUTH /LOAD=I13:AUTH.DAT

The load restores the saved map, discarding unsaved DU changes such as G3:.
It does not reset per-file F4 flags.

Keep an alternate policy and select it later:

    AUTH /SAVE=I13:PUBLIC.DAT
    AUTH J3: --
    AUTH /SAVE=I13:LIMITED.DAT
    AUTH /LOAD=I13:PUBLIC.DAT
    AUTH /LOAD=I13:LIMITED.DAT

The first two saves above assume unused filenames. Add /Y if deliberately
overwriting an existing version. Loading LIMITED.DAT changes the running map
only. To use that live map after restart as well:

    AUTH /SAVE=I13:AUTH.DAT /Y

Approve Adventure, with GAMES already selected on J:

    AUTH J1:ADV.COM
    AUTH J1:ADV.COM +X
    AUTH J1:ADV.COM

No remount or BYE rebuild is required. Restoring caller mode applies the normal
DU/F4 checks. A writable game-data workspace does not require making J: writable
to the caller. Games that insist on writes to J: remain download/local-play
software, not online games we must accommodate.

### A.9 Backups, failed saves and recovery

For a destination such as PUBLIC.DAT, SAVE first writes a complete PUBLIC.$$$
in the same DU. It closes and flushes that file, renames an existing destination
to PUBLIC.BAK (replacing the older backup), then installs the new PUBLIC.DAT.
The ordinary AUTH.DAT backup is AUTH.BAK. This backup is a policy-file backup,
not a backup of the board or its disk images.

.BAK and .$$$ are reserved SAVE extensions. LOAD can read such files if their
contents are a valid policy. An existing temporary file is not silently erased,
even with /Y. After an I/O error retain all temporary/backup files for
inspection.
If installing the new destination fails, AUTH attempts to rename the backup
back into place. Failure of that recovery or a power loss can still leave a
missing startup file; keep whole-installation backups as described in [Chapter 14](#14-backups-shutdown-and-recovery).

LOAD validates the signature, complete required records and every permission
byte before changing the resident table. An invalid, incomplete or missing file
leaves the current live map unchanged. If BYE cannot load a valid startup
policy, caller file access stays denied and a local diagnostic is displayed.
BYE does not automatically select AUTH.BAK or another alternate policy.

Recover a valid backup through private AUTH, without restarting:

    AUTH /LOAD=I13:AUTH.BAK
    AUTH /SAVE=I13:RESCUE.DAT
    AUTH /SAVE=I13:AUTH.DAT /Y

Use an unused name for RESCUE.DAT. Preserve that good copy before overwriting
AUTH.DAT: the final save rotates the old (possibly corrupt) AUTH.DAT into
AUTH.BAK, replacing the backup you just loaded. If a leftover AUTH.$$$ prevents
saving, first secure a valid policy under a different basename, then inspect
and clear only the stale staging file using private maintenance tools.

If no valid policy file remains, use private AUTH to rebuild the desired drive
and DU grants, inspect /MAP, then save them as I13:AUTH.DAT. The defaults table
in [A.2](#a2-the-permission-model-and-shipped-defaults) is a reference, not an automatic reset command.

### A.10 Troubleshooting

DIR?, SDZ? or LT? after making A0: RW:
    Caller-writable DUs cannot supply caller executables. Blank the caller and
    run AUTH A0: /R. Save the corrected map if the bad setting was saved.
    Query AUTH A0:DIR.COM if it still fails; also check that the file exists.

Game preparation failed:
    MOUNT GAMES first. I0: needs read/write access for the supplied launchers.
    Use AUTH I0: RW in private mode if necessary. The game executable's DU
    still needs caller read access, no write access and F4 approval.

I0: changed to -- after /INHERIT:
    It now follows I:'s NONE setting. Restore the explicit AUTH I0: RW override.

/LOAD did not undo an executable approval:
    Policy files hold DU permissions only. Use AUTH DU:FILE.COM -X to clear F4.

Changes disappeared after restart:
    Save to I13:AUTH.DAT, not just an alternate filename. Unsaved changes
    survive call boundaries but not a new BYE startup. Check that the save
    succeeded.

AUTH reports that private mode or an AUTH-enabled driver is required:
    Blank the caller locally. With no caller, use BYE's J menu choice to keep
    its resident interface attached. Do not use normal unpatched CP/M for AUTH.
    Check that the driver and utility came from a compatible package.

Explicit /SAVE says the file exists:
    Use /Y only if you intend to overwrite it, or choose a new filename.

Save reports a staging file already exists:
    Inspect the same-basename .$$$ before removing it. It may contain a complete
    recoverable map from a previous interrupted save; see [A.9](#a9-backups-failed-saves-and-recovery).

The optional host --caller-allow/deny/list helper is for stopped-image
maintenance. Normal live administration uses AUTH inside CP/M.
