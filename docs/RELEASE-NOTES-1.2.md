# RCP/M 1.2

RBBS 4.1.02 replaces the single-base 3.7 board. Fresh packages provide empty
PERSONAL, GENERAL, CPM and TEST areas, with no test users or messages.
First start generates a six-character SYSOP password in private SYSOP.DOC.

Menus and help are shorter. Normal menus respond immediately to a key;
message text and numbers still use Return. Expert mode retains command lines
and semicolon sequences. The private maintenance utility is
SYSUTLS:RBUTIL41; it manages forums and users. See docs/SYSOP-GUIDE.DOC.

The welcome banner and existing software collections are retained.
BYE/AUTH still protects private board data and operator commands. New users
may register and post. End message text with a period, then S to save.

This is fresh installation media. RBBS 3.7 data is not compatible with 4.1;
back up existing installations rather than overwriting their data disks.

Validation: macOS local and direct TCP tests cover registration, posting,
forum separation, private mail, maintenance, immediate keys, expert mode,
CP/M return, logout and carrier loss. Both BYE transports were rebuilt;
RBBS 4.1 over IP232 was not live-tested. Windows x64 launcher is cross-compiled
and dependency-audited; this release has not been live-qualified on Windows.
Existing emulator and disk-tool binaries are retained from 1.1.1.

Original component notices and source are included. Component-specific terms
and the maintainer's existing distribution decisions continue to apply.
