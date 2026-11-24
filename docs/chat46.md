# CHAT46 for HUMONGOUS RCP/M

CHAT runs at the CP/M prompt alongside the existing resident BYE510 driver.
It is a separate transient, not an RBBS module. In RBBS, C returns to CP/M;
then CHAT pages the operator. A later RBBS integration can chain to CHAT,
but returning to the board with the same login needs separate design.

The local operator answers with Escape. Either keyboard can use Ctrl-C or
Ctrl-X to exit. Both participants share one text area and should take turns.
An unanswered page returns to CP/M. Local Ctrl-G toggles BYE's bell/availability
flag; CHAT honors it. Local Ctrl-B enables private operation rather than chat.
The original CHAT C option enters conversation directly without paging;
it is not an authentication or privilege mechanism. Escape is likewise an
ordinary shared input character, not proof that the sysop answered.

## Build

`build_chat46.py` verifies the preserved source against its existing reference
SHA-256, retains it unchanged, configures direct CP/M use, and builds with
M80/L80 in an isolated stock CP/M 3 guest. The current executable is 768 bytes.
NONE=YES, MBBS=NO, GETCALR=NO and COMMENT=NO remove MBBS assumptions. BYBELL=YES
and LMBELL=NO use BYE BDOS 78. TIMEON=NO matches our driver (CLOCK=NO and
TIMEON=NO); no low-memory clock or time-limit writes are compiled in.
The original 4 MHz and PGTIME=30 constants are retained. Paging uses CPU
delay loops; its actual elapsed time must be measured, not assumed.

## Installation and validation

`install_chat46.py` requires a stopped instance and takes its console lock.
It stages A:/I:, installs A0:CHAT.COM with the F4 caller approval attribute,
adds a welcome hint and I14:CHAT.HLP, and verifies readback. It verifies that
all other existing files and their displayed attributes are unchanged,
backs up both images, then replaces them. The resident BYE driver is unchanged;
its load policy checks the actual F4 attribute. No new resident memory is used.
Source, build identity, documentation and a receipt are retained in the instance.

`check_chat46.py` copies installation media into a new test directory, installs
CHAT there, and exercises paging, text from both keyboards, both exits, page
cancellation/timeout, bell-off behavior, PATH use from WORK, and disconnect
recovery during conversation and paging. It uses loopback TCP on a free port
and writes local/caller logs plus result.json. It never boots the original
installation. Copy from stopped media for a consistent test snapshot.

November 24, 2026: native build and the BYE-absent abort/return to CP/M passed.
Two-way tests are pending: this execution session denies localhost bind/connect.
The supplied terminal command runs those tests before allowing installation.
