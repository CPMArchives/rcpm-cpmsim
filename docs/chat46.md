# CHAT46 for HUMONGOUS RCP/M

CHAT runs at the CP/M prompt with the existing BYE510 RSX. It is a transient,
not an RBBS module. Leave RBBS with C before running CHAT. RBBS chaining and
returning with the same login remain separate integration work.

## Operation

CHAT pages the sysop, who answers with Escape on the local console. The default
conversation display requires an 80-column, 24-row ANSI/VT100 terminal at both
ends. SYSOP has eight rows in the upper pane; CALLER has eight in the lower
pane. The panes maintain independent insertion positions, wrapping and scroll
history. Both people can type without interleaving their text. Backspace/Delete
erases the preceding character on the current line; Tab adds spaces. Arrow-key
editing and terminal resizing are not supported. Ctrl-R redraws both panes.

Ctrl-C or Ctrl-X from either keyboard returns to CP/M. CHAT /S retains the
plain scrolling conversation for terminals without ANSI cursor positioning.
It still uses the plain paging banner, answer key and exit controls.

Local Ctrl-G toggles BYE's bell/paging availability. BYE's existing local
function keys remain active. Local Ctrl-B ends split chat and enters BYE's
private-console mode; subsequent private input is never stored in chat buffers.
If another BYE control prints over the display, Ctrl-R restores the panes.
CHAT C retains the historical direct-entry option. Paging still accepts Escape
as shared input; it is not an identity check or privilege mechanism.

## Implementation

build_chat46.py verifies the preserved reference SHA-256, configures the source,
and builds with native M80/L80 under CP/M 3. guest/chat-split.asm supplies the
extension; the generated CHAT.MAC includes it in full. The transient is 3328
bytes and adds no resident memory. NONE=YES, MBBS=NO, GETCALR=NO and COMMENT=NO
remove MBBS assumptions; BYBELL=YES uses BYE BDOS 78. TIMEON=NO matches the
resident driver. The original 4 MHz and PGTIME=30 constants are retained;
measured unanswered paging is about 23 seconds, not an exact 30-second clock.

Split input polls BYE's combined BIOS status path for carrier/idle handling,
then consumes at most one local and one remote byte per pass through existing
BDOS 66/67 and 61/64. Local input retains BYE's control-key processing. Local
private state is checked through BDOS 77 before input enters a pane. Screen
output continues through BYE's normal combined output and carrier checks.
The driver and emulator are unchanged. The renderer uses cursor positioning
and explicit pane buffers, with no alternate screen, scroll margins, colors,
or hidden cursor that a carrier-loss exit could leave enabled.

## Build, installation and tests

install_chat46.py locks a stopped instance, stages A:/I:, installs approved
A0:CHAT.COM plus HELP CHAT and a welcome hint, and reads back the changes.
It verifies other files and attributes are unchanged, backs up both images
and the previous validation receipt, then replaces the images. Source,
documentation, build identity and matching validation are retained.
Update-CHAT-Split.command defaults explicitly to native ~/CPM/RCPM and accepts
another installation directory as its first argument. It does not update a
Docker container. Stop with local Ctrl-C, Return, then SYSUTLS:BYEBYE first.

check_chat46.py tests disposable media over loopback TCP. It interprets the
ANSI output into screen cells to verify participant separation, backspace,
wrapping and independent scrolling, in addition to paging, local answer, both
exits, cancellation/timeout, bell-off behavior, PATH from WORK, CHAT /S,
private blanking and carrier-loss recovery during chat and paging. Test tools
and the emulator run from their existing host paths to avoid asking macOS to
approve fresh copies. All media writes go to the disposable directory.

The original scrolling version passed its live checks and was installed on
November 24, 2026. The split build's executable hash and check results are
recorded together in guest/chat46/VALIDATION.json after qualification.
