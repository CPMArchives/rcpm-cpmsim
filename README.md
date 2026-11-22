# RCP/M

**Run your own corner of the dial-up computing era—on a modern computer.**

RCP/M brings a classic remote CP/M system back to life. Start it on your Mac
or Windows PC, connect from a terminal, and step into a working 8-bit world:
a command prompt, hundreds of software collections, online games and a
bulletin board. You can explore it yourself or become the sysop of your own
remote system and welcome a caller.

No vintage hardware, modem or telephone line required.

## What is an RCP/M?

CP/M was one of the defining operating systems of early personal computing.
An **RCP/M**, short for **Remote CP/M**, let someone use a CP/M computer from
another location, usually by calling it over a telephone modem.

A caller could browse disks, download programs, read documentation and run
software on the remote machine. Many systems also offered a bulletin board
for messages. The person running the system—the *sysop*, or system
operator—curated the software and kept things running.

This project recreates that experience using a real CP/M 3 operating system
running on an emulated Z80 computer. The programs run inside CP/M; the
connection travels over a modern TCP network instead of a telephone line.

## A software archive you can actually explore

RCP/M comes with the **310 SIG/M and 93 CPMUG volumes**: historic user-group
collections packed with programs, source code, utilities and documentation.
They are available from inside the system, ready to browse and download.

There is more to do than look at a directory listing:

- **Explore CP/M.** Use its command line, browse named directories and discover
  the tools people used to make these computers their own.
- **Open the archives.** List software libraries and read their text members
  without downloading and unpacking everything first.
- **Play classic games.** Try Adventure, Animals and Maze Chase through the
  supplied game launchers.
- **Visit the bulletin board.** Enter the included RBBS to experience another
  side of early online computing.
- **Make it your system.** Curate the available disks and programs, manage caller
  permissions and run the machine from your own local sysop console.

Whether you remember calling these systems or have never seen a CP/M prompt,
this is a way to experience the software in its working environment.

## Get started

**[Download RCP/M 1.0](https://github.com/CPMArchives/rcpm-cpmsim/releases/tag/v1.0)**

Choose **macOS ARM64** for an Apple Silicon Mac or **Windows x64** for Windows.
Each platform ZIP contains the complete system; you do not need the separate
common archive to run it.

1. Extract the whole ZIP into a writable folder.
2. Start `Start-RCPM.command` on Mac or `Start-RCPM.cmd` on Windows.
3. When the local console says `RCP/M modem ready.`, connect with a raw TCP
   terminal client to `127.0.0.1`, port `4000`, on that computer. Press Enter
   to begin.

At the CP/M prompt, try:

```text
HELP
DIR SIGM:
DIR CPMUG:
MOUNT /L
RBBS
```

`HELP` introduces the commands and activities. `BYE` ends your call and leaves
the system ready for the next caller.

You do not need to install Python, a compiler or a separate emulator. The Mac
tools are unsigned; the included `docs/INSTALLATION.DOC` explains startup and network
setup. Start locally, then use that guide to make the system accessible from
another computer.

## Software

Add more games with the **[optional software disks](Software/README.md)**.
INFOCOM and MODERNIF are separate downloads: install the collections you want
alongside your existing volumes. The Software section includes contents,
installation instructions and test results.

## Run it your way

RCP/M supports **one caller at a time**, alongside the local sysop console.
It uses [CP/M 3](https://www.cpm.z80.de/source.html),
[Z3PLUS](https://www.gaby.de/edownf.htm) and
[BYE510](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/bye5/bye510/)
on [Udo Munk’s z80pack emulator](https://github.com/udo-munk/z80pack), with tools
for archive browsing, file transfers and system administration.

The release includes `docs/INSTALLATION.DOC` and `docs/SYSOP-GUIDE.DOC`. For technical
details, source builds, the roadmap and the project’s development history,
see the **[documentation index](docs/README.md)**.

RCP/M preserves software from many authors and user groups. Their individual
notices and terms remain applicable; see the [release notes](docs/RELEASE-NOTES-1.0.md)
and [component review](docs/distribution-review.md). The project is maintained
by **CPMArchives**.
