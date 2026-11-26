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

## Linux and Docker packages — 26 November 2026

Added Linux ARM64/x64 runtime archives and Docker image archives. Both Linux
architectures pass extracted-package direct-TCP qualification: boot, caller
login, all ten HELP topics, SIG/M and CPMUG browsing, GAMES/GUIDES mounts,
RBBS 4.1 entry, duplicate-instance refusal, private credential consistency and
orderly shutdown. Docker checks cover published-port login, HELP, RBBS entry,
orderly shutdown and credential preservation across container replacement.

Test host: ARM64 Docker on macOS; Debian 12 userspace for both architectures.
x64 compilation/execution uses CPU emulation, not native x64 hardware.
Optional IP232 and broader distribution compatibility were not tested.
Shared media is unchanged from the published 1.2.1 common archive.
Linux disk tools now honor package-local DISKDEFS after relocation. The
release checker now validates the current RBBS 4.1 prompt and account format.

See docker.md for loading image archives and preserving the system in a
named volume. These are downloads, not claims of published registry images.

### Simultaneous Docker instances — 26 November 2026

Both released Docker packages passed two-instance checks with callers connected
simultaneously on ports 4000 and 5000 inside an isolated Docker network. RBBS
and CP/M HELP sessions operated independently, with separate data volumes and
credentials. Stopping one instance left the other caller connected and able to
use HELP. Startup reported the correct ports and both instances shut down cleanly.
Host publication of both occupied ports was not tested in this pass; x64 used
QEMU CPU emulation on ARM64. See performance/LINUX-DOCKER-VALIDATION.json.

### Mixed ARM64/x64 Docker pair — 26 November 2026

One released ARM64 instance on port 4000 and one released x64 instance on port
5000 passed simultaneous caller checks, with independent RBBS and CP/M HELP
sessions, separate volumes and credentials, correct startup port reports and
clean shutdowns. The x64 caller stayed connected and used HELP after ARM64
shut down. Test networking was isolated; occupied host ports were not published.
x64 used QEMU emulation on ARM64. Results and archive hashes are in the
consolidated Linux/Docker validation report.
