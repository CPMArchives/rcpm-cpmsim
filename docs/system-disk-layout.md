# A: boot and caller services; B: private maintenance

Decision: retain IBM 3740 geometry for A: and B:. Do not enlarge A: or
introduce a new emulator/BIOS disk geometry solely for system utilities.
The builder now creates this layout and BYE gates caller BDOS access to B:.
The running shared trial has not been modified. This is a focused B: boundary,
not completion of the approved-program execution policy.

## Historical basis

Jon Schneider's circa-1985 [RCP/M GUIDE](https://www.dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/rcpm/rcpm-ug.prn)
shows an illustrative A0 directory with BYE, CHAT, DIR, TYPE, XMODEM,
library tools and file-finding services. It describes selected public
transients and disabled resident commands. This is an example, not a
universal disk layout or a verified complete Rio Grande installation.

Dave Hardy's July 10, 1981 [SECURSYS.DOC](https://www.dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/rcpm/secursys.doc.txt)
specifically warns against publicly accessible PIP, FORMAT, debuggers,
memory-modifying programs and loaders. Our policy also withholds assemblers
and compilers: Hardy allowed some without their loaders, but our approved
caller services do not require a development environment.

David McCord's November 8, 1984 [Z3ANDBYE.DOC](https://www.dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/rcpm/z3andbye.doc.txt)
shows that even terminal-selection tools need option restrictions when they
can write arbitrary files. Classify the actual binary and its options,
not just the command name. His alias example is historical evidence, not
a proposed implementation for this system.

The following assignments are our engineering decisions based on those
sources and our current CP/M 3/Z3PLUS installation.

## Assignments from the current A: inventory

| Files | Destination | Access and reason |
| --- | --- | --- |
| CPM3.SYS, PROFILE.SUB, Z3PLUS.COM, STARTZ3P.COM, VT100DYN.COM, BYEDRIV.COM | A: boot support | Retain for boot; callers must not modify or freely invoke initialization/load utilities. Presence on A: does not authorize execution. |
| BYE.COM | A: | Caller logoff; retain required BYE startup behavior. |
| DIR.COM, TYPE.COM, HELP.COM, CLS.COM | A: | Public directory, reading, help and display services; review actual options and access to private files. |
| MOUNT.COM, UPLOAD.COM, MESSAGE.COM, YSEND.COM | A: | Approved caller-service roles; retain restrictions on destinations, mount selection and readable files. |
| GET.COM, PATH.COM, SUBMIT.COM | A: initially | Startup invokes GET CONSOLE and PATH before BYE; CP/M uses SUBMIT for PROFILE.SUB. Retain until startup is refactored; caller invocation controls remain security work. |
| BYEBYE.COM | B: | Local-only emulator shutdown. Moving it alone does not enforce local-only use. |
| SID.COM, DUMP.COM, HEXCOM.COM, SAVE.COM, GENCOM.COM | B: | Debugging, memory inspection, executable creation and RSX modification. |
| PIP.COM, ERASE.COM, RENAME.COM, SET.COM | B: | Unrestricted copying, deletion, renaming and attribute/password administration. Any future caller WORK editor/deletion service needs narrower permissions. |
| DEVICE.COM, PUT.COM, RESET.COM, SETDEF.COM | B: | Device redirection and disk/system state. |
| HIST.COM, HIST.UTL, HISTCL.COM, TRACE.UTL | B: initially | Command history/recall and tracing need a separate caller-data and execution review before public use. |
| SHOW.COM, ZSHOW.COM | B: initially | Operator diagnostics; provide selected read-only information later if useful. |
| Z3PLUS.LBR | A: boot support | The Z3PLUS installation uses its configured library during initialization. It must stay with the boot files. |
| !(C)1988 | Retain with Z3PLUS pending license review | Small copyright material; do not discard required attribution to gain space. |

The stock B: development/system-building contents are copied to a 4-MB
`offline/BUILD.dsk`, outside `volumes/`. This includes COPYSYS, GENCPM,
INITDIR, LINK, L80, M80, MAC, RMAC, PATCH, WM, BIOS/loader sources,
SPR/REL inputs, scripts and original system artifacts. Store BUILD offsite
in normal operation; introduce it to the mount collection only for maintenance
between calls, restore a public J: volume, then remove BUILD again.
No special restricted-volume mounting mechanism is introduced.

B: also gets ED and DATE from the original stock A:. Its VOLUME.TXT label
identifies SYSUTILS. B: remains a small IBM 3740 image. The builder fails
if a file cannot be copied rather than silently dropping tools.

Later public additions may include CHAT, file search, NEW listings and
library-member browsing/downloads, following the historical service roles.
Their particular programs and configurations remain future decisions.

## Enforcement before deployment

1. Deny callers B: selection and file access, including explicit B0: commands
   and private-file reads through otherwise approved utilities.
2. Allow public execution only of approved programs. Protect boot loaders,
   PATH/GET and other retained support files on A: against caller invocation;
   protect all system files against caller writes.
3. Give the operator a path including B0:; restore the restricted caller
   path and execution policy at every return to caller mode and new call.
   A path is a lookup preference, not authorization.
4. Prevent archive executables or files copied into WORK from becoming
   alternate executable sources. Disable/restrict resident commands and
   alternate loaders consistently with the approved-program policy.
5. Verify public functions, explicit B0:SID denial, private copying and
   downloading denial, local shutdown restriction, privilege transitions,
   normal logoff and carrier-loss recovery on disposable images.

The B: mechanism below covers a subset of these requirements; wheel and
named-directory settings alone do not establish every item. Image changes
are implemented in the builder and tested separately. Migrate only after
the active console is shut down.

## Implemented B: mechanism

`guest/bye5/privateb.ins` is included in both BYE builds and runs at BYE's
BDOS interceptor. With the Z3PLUS wheel clear (normal caller mode), it
rejects B: selection, disk-free/label queries for B: and FCB file operations
on B:, including overlay loading, reads, writes, copying via BDOS,
directory search, rename, deletion, attributes and password metadata.
FCB drive zero is resolved using the current BDOS drive; leaving B: current
during a local transition does not grant access. Search Next is denied after
a denied search and after a local search until a new permitted caller search.

With local/operator privileges the same disk is accessible. B: is not added
to the public command path; use explicit `B:tool` commands locally for now.
Denials return an error without modifying the private disk. A failed B:
selection also denies subsequent implicit-drive file access until a permitted
disk selection or local operation, so utilities that ignore selection errors
cannot silently operate on the prior drive instead.

This is guest policy for approved software. It does not isolate hostile
machine code, direct BIOS access, resident-memory writes, or a caller utility
that can restore privileges. The remaining startup/utility execution controls
and caller configuration must be finished before public deployment.

`prepare_shared_trial.py` refuses BYE build metadata without this adapter and
checks the direct build's installed binaries against their recorded hashes.
`check_sysutils.py` exercises caller denial and local access with both direct
TCP and tcpser/IP232 on disposable disks.

Reproduce after the standard runtime and BYE builds:

```sh
python3 check_sysutils.py --source /absolute/path/to/z80pack \
  --romwbw /absolute/path/to/RomWBW --tcpser /absolute/path/to/tcpser \
  --builds build/bye5
```

The check covers FCB read/write and metadata denial, default-drive operations
after a rejected select, explicit B:/B0: executable loads, private text and
directory access, local private execution/read/PIP, privilege restoration,
two calls per backend, native shutdown from B:, and unchanged B: disk bytes.
Its diagnostic executables are installed only on disposable test disks.
