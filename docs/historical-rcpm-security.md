# Historical RCP/M configuration evidence

Research date: November 19, 2026. These are period operator accounts and
guides, not reconstructed complete disk images. A BBS message program could
coexist with direct CP/M access; the findings below concern that CP/M access,
not a proposal to replace it with an RBBS interface.

## Identified systems and period practice

### Technical CBBS and SYSOP CBBS: Dave Hardy, July 10, 1981

[SECURSYS.DOC](https://www.dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/rcpm/secursys.doc.txt)
gives advice based on the operator's experience with these systems. It
recommends removing dangerous resident commands, withholding debuggers,
memory-modifying programs, loaders and unrestricted transfer tools, keeping
private utilities inaccessible, and checking executable integrity. It
describes refusing COM uploads and warns about malicious programs submitted
for public use. This is security advice, not a complete configuration listing.

### The ZCPR3 BBS: David McCord, November 8, 1984

[Z3ANDBYE.DOC](https://www.dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/rcpm/z3andbye.doc.txt)
describes the author's actual ZCPR3/BYE setup. Wheel-controlled renaming and
an alias restrict TCSELECT to safe invocation. The account also warns that
carrier loss can leave queued commands which later execute when the sysop
exits BYE with the wheel restored. It prescribes clearing the multiple-command
buffer and discusses recovery from an interrupted alias. These are concrete
period transition hazards, not modern conjectures.

### Rio Grande RCP/M operator's general guide: Jon Schneider, circa 1985

[RCP/M GUIDE](https://www.dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/rcpm/rcpm-ug.prn)
identifies its author as Rio Grande's sysop but explicitly generalizes across
systems. Its example A0 has selected utilities such as BYE, CHAT, DIR, TYPE,
XMODEM and LUX. It describes disabled resident commands, command search paths,
and XMODEM uploads directed to A6 regardless of the current prompt. RP
selects a private sysop destination. Do not present its example directory
as a verified full listing of Rio Grande's installed files, or infer universal
quarantine from its private-upload option.

### Z-System practice including CP/M Plus: Jay Sage, May/June 1989

[The Computer Journal 38, The Z-System Corner, printed pages 19-20 and continuation](https://www.jaysage.org/tcj/tcj_38_OCR.pdf)
explicitly discusses NZ-COM and Z3PLUS remote-system security. It describes
wheel-aware utilities, restricted write/print options, drive/user limits and
passworded named directories. It notes that command-search areas have special
access semantics. This is later than the mid-1980s target but directly relevant
to the selected CP/M 3/Z3PLUS software. It does not establish our binary's
settings or prove protection against arbitrary guest machine code.

## Implications for this project

The sources support a selected-utility configuration at the CP/M prompt.
They do not establish that unrestricted execution of uploaded software was
an intrinsic RCP/M feature. The approved prohibition on arbitrary caller code
fits these documented approaches. A cryptographic executable allowlist or
emulator-enforced user/supervisor architecture has not been established as
the period mechanism by this research.

Before inventing new execution machinery, inspect the actual Z3PLUS secure
configuration, resident commands, approved transients and transfer settings.
Retain the shared console and the agreed I:/J:/P: layout. Keep uploads
unavailable pending sysop review as our explicit policy; the sources show
different upload arrangements, not one universal historical configuration.

Review runtime-selected utility options, alternate program-launch paths,
rename/copy permissions and archive tools against that policy. A library
member being downloadable does not make executing it on the board necessary.
Also test command-buffer and other queued-input cleanup at logoff, carrier
loss and local privilege transitions. The current build's wheel integration
is not evidence that these additional Z3PLUS/BYE behaviors are configured.

This research changes no executable code and supplies no evidence that the
current prototype already enforces the intended caller restrictions.
