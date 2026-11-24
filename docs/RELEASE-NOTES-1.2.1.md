# RCP/M 1.2.1

Adds CHAT46 for live conversation between the caller and local sysop.
Type CHAT at the CP/M prompt; the sysop answers with Escape locally.
The default 80x24 ANSI/VT100 display gives SYSOP the upper pane and CALLER
the lower pane, with independent wrapping, backspace and scrolling.
Ctrl-R redraws; Ctrl-C or Ctrl-X ends chat. CHAT /S retains plain scrolling.
Local Ctrl-B ends split chat and enters BYE's private-console mode.

CHAT is a separate 3328-byte transient and adds no resident memory.
BYE510, Z3PLUS, the emulator and host binaries are unchanged from 1.2.
HELP CHAT, the welcome display, caller command listing and sysop guide
document the new command. Configured and original source, build hashes,
validation and a stopped-installation updater are included.
RBBS integration is unchanged: leave the board with C before typing CHAT.

macOS direct-TCP checks passed: separate panes, concurrent input, wrapping,
backspace, tabs, independent scrolling, redraw, both exits, paging,
cancellation/timeout, bell control, WORK/PATH use, scrolling fallback,
private blanking and carrier-loss recovery during chat and paging.
The Windows package contains the same guest program; Windows and IP232
CHAT operation have not been live-tested. Existing 1.2 qualification limits
continue to apply.

Fresh packages contain empty RBBS forums and no test callers, messages or
operator credentials. Existing 1.2 installations can use the included
source/rcpm/Update-CHAT-Split.command on macOS while stopped; it defaults to
~/CPM/RCPM and accepts another installation directory as its first argument.
It backs up A:/I:, installs CHAT and its help, and preserves unrelated files.
Do not replace an existing installation's data disks with fresh release disks.
This release does not migrate a running Docker deployment.

The component-specific notices and prior distribution decisions are retained.
