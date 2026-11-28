# HUMONGOUS RCP/M — User's Guide

*For the released RCP/M 1.2.2 system • November 2026*

This is the maintained edition of the manual. It describes the released system, not facilities still under development. Individual sysops may provide different software collections, forums and access permissions. See the [release notes](RELEASE-NOTES-1.2.2.md) if your system differs.

## Contents

- [1. Welcome to RCP/M](#1-welcome-to-rcpm)
- [2. Calling the system](#2-calling-the-system)
- [3. Your first visit](#3-your-first-visit)
- [4. Finding your way around CP/M](#4-finding-your-way-around-cpm)
- [5. The drives and named directories](#5-the-drives-and-named-directories)
- [6. Getting help and reading files](#6-getting-help-and-reading-files)
- [7. Exploring the software collection](#7-exploring-the-software-collection)
- [8. Exchanging library disks](#8-exchanging-library-disks)
- [9. Taking software home](#9-taking-software-home)
- [10. Sending something to the sysop](#10-sending-something-to-the-sysop)
- [11. Visiting the bulletin board](#11-visiting-the-bulletin-board)
- [12. Reading and posting messages](#12-reading-and-posting-messages)
- [13. Private mail](#13-private-mail)
- [14. Playing games](#14-playing-games)
- [15. A word with the sysop](#15-a-word-with-the-sysop)
- [16. A few words about access and etiquette](#16-a-few-words-about-access-and-etiquette)
- [17. Finishing your call](#17-finishing-your-call)
- [18. Command reference](#18-command-reference)
- [19. When things don't work as expected](#19-when-things-dont-work-as-expected)
- [Further reading](#further-reading)
- [Acknowledgements](#acknowledgements)
- [Glossary](#glossary)

## 1. Welcome to RCP/M

If you've spent any time exploring old computers, you may have wondered what it was like to call one over the telephone. In the days before the World Wide Web, much of the business of exchanging computer software and talking to other enthusiasts was conducted on bulletin boards. An RCP/M was a particularly interesting kind of board, because the caller could use the computer itself.

RCP/M stands for Remote CP/M. On HUMONGOUS RCP/M you can browse disks, read documents, download programs, play games and exchange messages. The command prompt belongs to a real [CP/M 3](https://www.cpm.z80.de/drilib.html) operating system, running on a Z80 emulated by our customized version of cpmsim from Udo Munk's [z80pack project](https://github.com/udo-munk/z80pack). The enhanced command environment is [Z3PLUS](https://manualzilla.com/doc/6919195/z3plus-user-s-manual); remote operation is handled by an adapted version of [BYE510](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/bye5/bye510/).

We've also written a few things especially for this system. MOUNT exchanges library disks, NDSCAN refreshes their directory names and AUTH allows the sysop to decide which files and programs are available to callers. You needn't concern yourself with administering AUTH to use the system.

The major difference from calling an RCP/M forty years ago is that you don't need a modem or telephone line. Your terminal makes a network connection instead. Otherwise, much of the experience will be familiar to anyone who used such a system in the 1980s.

If you're looking for a particular piece of software, the library is a good place to start. If you've come for company, try the bulletin board. And if you simply want to spend an afternoon playing Adventure, you're welcome to do that too.

## 2. Calling the system

You'll need a terminal program capable of a raw TCP connection. [SyncTERM](https://syncterm.net/) is a good choice, especially if you intend to exchange files, since it handles the terminal display and traditional modem transfer protocols.

Ask the sysop for the address and port, or obtain them from the board's announcement. Choose **Raw TCP**, not Telnet or SSH. Use an 80-column, 24-row ANSI or VT100-compatible terminal if possible. This is particularly important for Maze Chase and the split-screen CHAT display.

If you're trying a copy of RCP/M on your own computer, the standard native installation listens on:

| Setting | Value |
| --- | --- |
| Connection | Raw TCP |
| Address | 127.0.0.1 |
| Port | 4000 |
| Terminal | ANSI/VT100, 80 x 24 |

Use the address and port advertised by the sysop for a remote system; the local address above won't reach a board elsewhere.

Connect and press RETURN. BYE should greet you with the board's welcome message and bring you to CP/M. There may be a short delay. If the board is already occupied, remember that this is a single-caller machine: try again later.

The connection is not encrypted. Use a password for the bulletin board that you do not use for anything important elsewhere.

## 3. Your first visit

You don't need a bulletin board account just to explore the CP/M facilities. The board has its own registration procedure when you enter RBBS.

Here are a few things worth trying on your first call:

    HELP
    DIR
    DIR SIGM:
    MOUNT /L
    RBBS

HELP lists the available topics; DIR shows files; the SIGM directory contains one of the large historical software collections; MOUNT /L lists the library disks that can be selected. RBBS takes you into the message board.

Once you're in RBBS, C returns you to CP/M. Type BYE when you're ready to finish your call. If all you've done is look around, there's nothing that needs saving.

The rest of this guide describes these facilities in more detail. You needn't read it from cover to cover before using the board.

## 4. Finding your way around CP/M

The CP/M prompt tells you where you are. On this system you may see a drive and user area, or a name associated with that location. For example, A0: and SYSTEM: refer to the same directory on a standard installation.

Unlike the directory tree of a modern computer, CP/M organizes files by drive and numbered user area. The combination of the two is often called a DU. J3: means drive J, user area 3. There are sixteen user areas per drive, numbered 0 through 15.

A command may refer to a file in another DU without moving you there. For example:

    DIR J1:
    LT A0:WELCOME.TXT

To make a directory current, enter its DU or name followed by a colon:

    SIGM:
    DIR
    A0:

You can use upper or lower case for ordinary command and file names. Passwords in RBBS are a separate matter and are case-sensitive.

CP/M filenames have up to eight characters, followed by an optional extension of up to three characters. You'll often see names such as README.TXT, PROGRAM.COM, GUIDE.DOC and SIGMV011.LBR.

Two useful filename wildcards are the question mark, which matches a character, and the asterisk, which matches the remainder of a filename or extension. Try:

    DIR P0:*.LBR
    DIR J1:*.DOC

Not every command accepts wildcards; use them where the command's instructions permit. If you have been away from CP/M for a while, HELP COMMANDS is a handy reminder.

## 5. The drives and named directories

A standard HUMONGOUS RCP/M has four drives. The sysop can customize their contents and the access you have to them.

| Drive or directory | What you'll find |
| --- | --- |
| A0: / SYSTEM: | Public commands and the welcome message |
| I0: / WORK: | Temporary workspace for programs |
| I14: / HELP: | Online HELP topics |
| J: | The selected smaller software collection |
| P: | The selected large software archive |
| P0: / SIGM: | SIG/M libraries on the default P: |
| P1: / CPMUG: | CPMUG libraries on the default P: |

There are also private system and bulletin board areas. You cannot ordinarily read or change their files. Selecting a DU or knowing its name does not confer permission to use it.

J: holds a nominal 4 MB collection; P: is a 512 MiB archive disk. Either can be exchanged using MOUNT. The SIGM and CPMUG names therefore describe the *default* P: disk, not every disk that can be mounted there.

Named directories save a good deal of typing and remembering. If a volume gives one of its user areas the name INFOCOM, for instance, you can enter that directory by typing INFOCOM: rather than having to remember which J: user area contains it.

The names are rebuilt automatically when you mount another volume. If a name isn't present, use the numeric DU or look at the volume's guide instead.

## 6. Getting help and reading files

The HELP command is worth remembering. A copy of the essential caller instructions is always available on the machine itself.

    HELP
    HELP MOUNT
    HELP TRANSFER
    HELP RBBS
    DIR HELP:

An unqualified HELP opens the main topic. In the released 1.2.2 system, topics are short text files. HELP followed by a topic name opens that topic directly. HELP // gives the preserved viewer's own usage information.

The expanded hierarchical online guides are planned for a subsequent release; don't be surprised if a stock 1.2.2 installation has simpler HELP screens.

To examine an ordinary text file, try LT:

    LT A0:WELCOME.TXT

LT is also useful for reading supported compressed text and text members inside libraries. TYPE is available for ordinary text files. CLS clears the terminal display. DIR and SDZ list directories; SDZ is the same supplied Super Directory utility as DIR.

Don't attempt to read a binary executable as text. Apart from being uninformative, the output can confuse your terminal.

## 7. Exploring the software collection

The standard P: disk contains the 310 SIG/M and 93 CPMUG volumes. These were assembled by the CP/M user groups and circulated amongst enthusiasts. They contain an extraordinary variety of material: programming tools, source code, games, technical notes, correspondence and programs written for particular makes of computer.

The individual volumes are supplied as LBR files. An LBR is a library containing a number of separate files. The individual members may themselves be compressed.

    DIR SIGM:
    DIR CPMUG:

A directory of numbered libraries doesn't tell you much about their contents. You can look inside one without downloading it:

    LDIR P0:SIGMV011

LDIR lists the members of the library. To read a text member, supply both the library name and the member name to LT:

    LT P0:SIGMV011 ABSTRACT.011

Use the actual name shown by LDIR. This is particularly useful when an archive contains an abstract or instructions, and you're trying to decide whether the volume is worth downloading.

If you mount a different P: archive, use the DU or named directory belonging to that disk instead. P0:SIGMV011 is an example for the default archive.

When you find something you want, download the library itself using YSEND and unpack it on your own machine. There is no general caller facility for extracting archive members onto the RCP/M disks.

Not everything in a historical archive will run on every CP/M machine. Some programs are written for a particular screen, disk controller, terminal or operating-system revision. Read the author's documentation before trying the program locally. Also bear in mind that the original author may have imposed conditions on copying or redistribution.

## 8. Exchanging library disks

You aren't restricted to the disks which were mounted when you called. The sysop may have made additional volumes available, ranging from small collections of games to much larger archives.

    MOUNT /L

This lists the J: and P: catalogs and identifies their current images. To select a volume, enter its catalog name:

    MOUNT GAMES

MOUNT chooses the appropriate drive for the image. The following forms are useful if you wish to look at just one catalog:

    MOUNT J: /L
    MOUNT P: /L

If both catalogs have a volume of the same name, specify the drive as well, for example MOUNT J: GAMES. The names in your board's catalog may be different from the examples in this manual.

After a successful mount the program reports which drive received the new volume. Try DIR J: for a J: disk and read its README.TXT if one is supplied.

To restore the original disks:

    MOUNT J: /DEFAULT
    MOUNT P: /DEFAULT

The second command restores the SIG/M and CPMUG archive on a standard installation. The two drives can be exchanged independently. Logging off does not necessarily restore them; a previous caller may have left a different volume mounted.

MOUNT automatically runs NDSCAN to rebuild the selected drive's names. If the scan reports an error after the mount has succeeded, don't assume that the old names refer to the new disk. Use explicit DUs until the names have been corrected or the default volume restored. You can run NDSCAN J: or NDSCAN P: yourself on a fully readable drive.

## 9. Taking software home

A file transfer involves two programs: one sending and one receiving. Entering the command at the RCP/M end is only half the job. Your terminal program must be ready to receive the file.

The supplied download command is YSEND, which uses YMODEM. A small text file makes a convenient first test:

    YSEND A0:WELCOME.TXT

When the RCP/M is ready to send, select YMODEM receive in your terminal, unless it has already started receiving automatically. Choose your local download directory according to the terminal's instructions. Wait for the transfer to complete and for the CP/M prompt to return.

To take a whole library home, for example:

    YSEND P0:SIGMV011.LBR

Make sure the file is on the currently mounted disk. A library is a binary file: do not run it through a terminal's text capture or character-set conversion.

If the RCP/M appears to be doing nothing after you start a transfer, it may simply be waiting for the receiving end. Check that you've selected the corresponding protocol and the right transfer direction. If a transfer fails, use the terminal's transfer-cancel facility and follow the remote program's prompts before trying again.

The YMODEM download service can send files from readable directories even when those files are not approved for execution on the board. The two permissions are quite different.

## 10. Sending something to the sysop

Perhaps you've found a CP/M program missing from the collection, or have written a utility of your own. The sysop will generally appreciate a useful contribution, particularly if it comes with instructions.

For a single file, the supplied upload command uses XMODEM with CRC:

    UPLOAD MYPROG.LBR

Supply the intended CP/M filename, then choose XMODEM/CRC send in the terminal and select your local file. For a batch, use:

    UPLOAD /Y

and choose YMODEM send at your end. Follow the prompts and wait for confirmation. XMODEM may leave record padding at the end of the received file; YMODEM carries its declared length.

Your submission goes into the sysop's private review inbox. It won't immediately appear in the public library or in WORK, and DIR cannot list that inbox. The sysop will examine it before deciding whether to add it to a collection.

It's helpful to accompany an upload with a note giving its filename, purpose, author, supported hardware and any distribution restrictions. Use MESSAGE or a suitable RBBS message to contact the sysop.

A completed file survives a disconnect. An unfinished partial upload is discarded; a completed member of a YMODEM batch is retained even if a later member fails.

The fact that a file was uploaded successfully is not a promise that it will be published or made executable on the board.

## 11. Visiting the bulletin board

At the CP/M prompt type:

    RBBS

The board is based on CP/M RBBS 4.1 Edit 02, adapted to our system. This is where you'll find the discussion forums and private mail.

Give your name at the sign-on prompt. If you've never visited the board, follow the registration prompts to establish an account. Choose a password you can remember, but don't reuse an important password from another service. Passwords are case-sensitive; the six-character password facility is a feature of this particular RBBS revision.

The normal menus respond to a single key. There is no need to press RETURN after choosing a command, a forum number or a Y/N answer. Names, message numbers and the text you enter still use RETURN. Expert mode is different: it accepts line commands and semicolon-separated arguments.

The current forum is identified at the top of the main menu. Here is a useful summary of its commands:

| Key | Function |
| --- | --- |
| E | Enter a message |
| R | Read messages |
| N | Read new messages |
| S | Summarize messages |
| K | Delete an authorized message |
| F | Select a forum |
| M | Forum status |
| B | Bulletins |
| U | Users |
| W | Welcome |
| P | Password |
| T | Bell |
| X | Expert mode |
| ? | Help |
| C | Return to CP/M |
| G | Disconnect |

The board's help and menus are the best authority for a particular sysop's installation. This guide describes the version in the standard release, rather than every variant of RBBS.

C takes you out of RBBS without ending your call; you may go back to exploring the library or playing a game. Reentering RBBS requires signing on to the board again. G ends the entire connection.

Your board account and saved messages are retained between calls. They are not stored in the temporary WORK directory.

## 12. Reading and posting messages

A bulletin board is most interesting when people actually use it. If you've a question about a piece of CP/M software or an interesting project to describe, don't feel that you must wait for somebody else to begin the discussion.

Use F to see the forums, then choose one of the displayed numbers. A fresh board has PERSONAL, GENERAL, CPM and TEST areas, but your sysop may have arranged matters differently. PERSONAL is for private mail; the other forums are public discussions.

S summarizes messages in the selected forum, R reads them, and N reads new messages. M shows the forum's status. Message numbers refer to the current forum.

To post, select E, supply the requested header information and enter your text. End the message by typing a period on a line by itself. This brings up the draft menu rather than immediately publishing your message.

| Draft key | Function |
| --- | --- |
| S | Save the message |
| L | Preview it |
| H | Edit the header |
| E | Edit the text |
| C | Continue entering text |
| A | Discard the draft |
| ? | Help |

Read the draft over before saving it. Blank lines are allowed; the special period line finishes text entry. During entry, a question mark on its own line opens the writing help. Ctrl-V shows the line-editing keys.

If you want to read a succession of messages without returning to the menu after each one, expert mode provides some useful shorthand:

| Expert command | Function |
| --- | --- |
| R;123 | Read message 123 |
| R;1+ | Read from message 1, pausing between messages |
| R;1* | Read from message 1 without pauses |
| N | Read new messages |
| R;#+ | Start at the next unread message |

The + and * suffixes also work with S and K. Take care with deletion commands. You may delete only messages which the board permits you to delete.

While the board is displaying messages, Ctrl-S pauses the output and any key resumes it; Ctrl-K stops the output. These controls are documented in RBBS's own help.

## 13. Private mail

If what you have to say is intended for one particular caller, use the PERSONAL forum rather than posting it in a public discussion.

Select PERSONAL with F, then enter a message with E and give the recipient when prompted. Use the recipient's registered board name. If you're uncertain of its spelling, the U command lists users.

Compose the message as usual, end the text with a period on a line of its own, and use S to save. In PERSONAL the draft menu also offers R to save another copy; H allows the recipient in the header to be changed. Follow the displayed prompts.

To read your mail, enter PERSONAL and use the ordinary reading commands. The board restricts private messages to the appropriate accounts.

Private mail belongs to this particular board. The released system does not yet exchange mail or forum messages with other RCP/Ms through CPMNet. Nor is private mail encrypted: the sysop has custody of the board and its backups, and your raw TCP connection is unencrypted. Don't use it for confidential information that you wouldn't wish to entrust to the system operator.

## 14. Playing games

One of the more pleasant ways of spending time on an RCP/M is to play the software instead of merely collecting it. The supplied GAMES volume contains three prepared launchers:

    MOUNT GAMES
    J0:ADVENT
    J0:ANIMALS
    J0:MCHASE

Each launcher is a separate alternative to enter at the CP/M prompt after mounting GAMES.

**Adventure** is the expanded version of the classic text adventure. Answer its instructions prompt and follow the game's own commands.

**Animals** is the guessing game which asks questions to identify the animal you're thinking of.

**Maze Chase** requires an ANSI/VT100-compatible display. If the screen is a mess of stray characters, check your terminal emulation.

The launchers prepare the files the games need in WORK before starting the actual game from the protected library disk. The supplied programs can therefore write temporary data without modifying the shared software collection.

Use a game's own exit command to return to CP/M. Temporary game data, including any saved games and high scores in WORK, disappears when you log off. You may be able to resume a game within the same call, but don't expect its data to be there next week.

Some sysops install the [optional software collections](../Software/README.md), including an expanded GAMES volume. Read their catalogs and instructions. Not all archived games are suitable for playing online; many are there for download and local use.

## 15. A word with the sysop

If the sysop is at the local console, you can have a live conversation. From the CP/M prompt enter:

    CHAT

Leave RBBS with C first if necessary. The program pages the sysop, who answers at the local console. An unanswered page returns you to CP/M; the sysop may simply be away from the keyboard.

In the normal display, the sysop types in the upper pane and you type in the lower one. Each wraps and scrolls independently, so you can type at the same time without the two conversations becoming intermingled.

Use an 80-column, 24-row ANSI/VT100 terminal. Backspace erases text on the current line, Tab inserts spaces, and Ctrl-R redraws the display. Ctrl-C or Ctrl-X ends the conversation.

For simpler terminals, use CHAT /S for the traditional scrolling display.

If nobody answers, don't spend the next ten minutes paging repeatedly. Leave a note instead:

    MESSAGE

Follow the prompts and save the message. This is a direct submission to the sysop's review inbox, independent of RBBS mail. An unsaved draft is lost at call recovery.

## 16. A few words about access and etiquette

An RCP/M is a shared computer, and the sysop has to strike a balance between providing useful facilities and keeping the machine available for the next caller.

Ordinarily you can read the public collections, download their files and execute approved programs. You cannot run every COM file you see in the directory. The sysop chooses which programs are suitable for online use; the supplied AUTH facility requires the executable's DU to be readable but not caller-writable and the file to have the appropriate approval attribute.

WORK is the exception to the normal read-only library arrangement. Programs use it for temporary data. It is not a personal disk or a place to keep software between calls. There is no general caller copy command or direct upload into WORK on the standard system.

If a program is unavailable for online execution, download it for your own machine rather than trying to circumvent the board's restrictions. Ask the sysop if you think it would make a useful addition to the online collection.

If you have the only caller connection, bear in mind that someone else may be waiting. Don't leave it occupied unnecessarily. Be considerate in the forums, keep private matters out of public messages, and give sufficient details when reporting a problem: the command you used, the volume mounted, the terminal type and what actually happened.

## 17. Finishing your call

Finish any file transfer or draft message and leave the program you're using in its normal fashion. From RBBS, C returns to CP/M; G logs off directly.

At the CP/M prompt enter:

    BYE

That ends your call and leaves the machine available for the next caller. You can also disconnect with your terminal, but the ordinary logoff command is preferable when circumstances permit.

WORK is cleared at call boundaries. Saved RBBS messages and your board account remain, as do completed uploads and saved MESSAGE notes. The mounted library volumes need not return to their defaults until the machine restarts or somebody selects another volume.

## 18. Command reference

For the expanded 1.2.3 online reference, enter `HELP COMMANDS`. Its menus separate public disk programs, resident caller commands and sysop tools. An asterisk (`*`) means **SYSOP ONLY**. Reading a sysop help page does not grant execution permission. Use `^` to return to the parent menu and `.` to return to the root of the current help session.

The following is the standard public transient command set. Sysops may add or restrict programs, and some commands have additional options documented in HELP or their original instructions.

| Command | Purpose | Example |
| --- | --- | --- |
| BYE | Log off | BYE |
| CHAT | Page the sysop | CHAT /S |
| CLS | Clear display | CLS |
| DIR / SDZ | List files | DIR SIGM: |
| HELP | Display online help | HELP TRANSFER |
| LDIR | List library members | LDIR P0:SIGMV011 |
| LT | Read text or a library member | LT P0:SIGMV011 ABSTRACT.011 |
| MESSAGE | Leave a note for the sysop | MESSAGE |
| MOUNT | List or exchange library volumes | MOUNT /L |
| NDSCAN | Refresh names on a selected drive | NDSCAN J: |
| RBBS | Enter the bulletin board | RBBS |
| TYPE | Display an ordinary text file | TYPE A0:WELCOME.TXT |
| UPLOAD | Send files to the sysop | UPLOAD /Y |
| YSEND | Download using YMODEM | YSEND A0:WELCOME.TXT |

Game launchers are on their respective volumes, not in the A0: command set. Mount the appropriate disk before using them.

## 19. When things don't work as expected

| Symptom | Things to try |
| --- | --- |
| No connection | Check the advertised address and port; the board may be occupied |
| Connected, but no welcome | Check Raw TCP and press RETURN |
| A directory name is missing | Check the mounted volume and use its numeric DU |
| A command is rejected | Check spelling, DU and caller execution approval |
| Download appears to stall | Start the matching YMODEM receive operation |
| Uploaded file isn't in DIR | Expected: the submission is in the private sysop inbox |
| RBBS ignores RETURN | Normal menus use single-key selection |
| CHAT or Maze Chase display is garbled | Check ANSI/VT100 and terminal dimensions; CHAT /S is an alternative for chat |
| Saved game is gone | WORK is temporary and cleared between calls |

If you can't resolve a difficulty, leave the sysop a note. Include the steps needed to reproduce it rather than merely saying that the program doesn't work.

## Further reading

If you decide you'd like to establish a board of your own, the companion [Sysop's Guide](SYSOP-GUIDE.md) describes the installation, configuration and maintenance of HUMONGOUS RCP/M.

For a glimpse of what calling an RCP/M was like in its heyday, see Jon Schneider's 1985 guide and other period material in the [historical RCP/M archive](https://www.dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/rcpm/). The command set and restrictions of those systems may differ from ours.

## Acknowledgements

HUMONGOUS RCP/M owes its existence to the work of a great many people, some of whom made their contributions more than forty years ago. Much of our work has been to bring their software together, adapt it to present-day computers and make it available to another generation of CP/M enthusiasts.

Our particular thanks go to Gary Kildall and the team at Digital Research for CP/M; Udo Munk for z80pack and cpmsim; Richard Conn for his pioneering work on ZCPR; and Jay Sage and Bridger Mitchell for Z3PLUS, with Joe Wright for his contributions to the Z-System.

We also owe a debt to Dave Jaffe, the original author of BYE, and to Wayne Masters, Irv Hoff, George Peace and the other contributors who carried its development forward; to the authors and maintainers of CP/M RBBS, whose work gives our callers a place to exchange messages; and to Jim Brain for tcpser, which allows us to recreate the modem connection without a telephone line.

Finally, our thanks to the many authors of CP/M utilities, the SIG/M and CPMUG librarians and contributors, and the archivists and volunteers who have kept this remarkable body of software and documentation accessible. Without their generosity and persistence, there would be very little for an RCP/M such as ours to offer.

The individual software distributions retain their original credits and notices.

## Glossary

| Term | Meaning |
| --- | --- |
| ANSI / VT100 | Terminal display conventions used by the supplied screen-oriented programs |
| Archive | A collection of preserved files or software volumes |
| Bulletin board / BBS | A system for exchanging messages, and often files, among callers |
| BYE | Resident remote-operation software; also the command to log off |
| Caller | Someone using a remote system |
| COM file | CP/M executable program, with a .COM extension |
| CP/M | Control Program for Microcomputers, the operating system used here |
| CPMUG | CP/M User Group; also the name of its software collection |
| DU | Drive/user combination, for example J3: |
| F4 | CP/M file attribute used by this distribution to mark caller-approved executables |
| Forum | A bulletin board message area devoted to a subject |
| LBR | CP/M library file containing other files |
| Library volume | A disk or disk image containing a software collection |
| Logoff | Ending a call |
| Message base | The collection of stored bulletin board messages |
| Named directory | A Z-System name associated with a particular DU |
| Private mail | Messages addressed to a particular registered board user |
| Raw TCP | Network connection carrying terminal data without Telnet negotiation |
| RBBS | The bulletin board software supplied with the system |
| RCP/M | Remote CP/M |
| Resident program | Software which remains in memory while other programs operate |
| SIG/M | A CP/M software-sharing user-group collection |
| Sysop | System operator |
| Terminal | The program or device used to communicate with the remote computer |
| Transient program | A program loaded to perform a task and then return control to the command environment |
| User area | One of CP/M's numbered file areas on a disk |
| Warm boot | Return to the CP/M command environment without a full machine restart |
| WORK | Temporary caller workspace in I0: |
| XMODEM / YMODEM | File transfer protocols supported by the supplied upload/download services |
| Z-System | The enhanced CP/M command environment from which Z3PLUS developed |
