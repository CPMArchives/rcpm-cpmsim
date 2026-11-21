# CP/M BBS survey: 1983–1986

Research date: November 19, 2026. Scope: message/user services for the
CP/M 3 + Z3PLUS + BYE510 shared-console system, retaining direct CP/M access.
This survey informed package selection. RBBS 3.7 is now being evaluated in a
separate [operator-started trial](rbbs-trial.md); the other candidates remain
research leads rather than qualified installations.

Archive upload timestamps are not necessarily release dates. Internal dated
documentation takes priority. Later source histories are identified as such;
later package features are not attributed automatically to 1983–1986 releases.

## Candidates

| Package | Period evidence | Character | Fit for this project |
| --- | --- | --- | --- |
| RBBS 3.x, especially Dennis Recla's 3.7 | Manual dated November 23, 1984; refers to his 3.5 earlier in 1984. Preserved 3.7 and 4.0 archives have 1985 catalog dates. | Traditional message board, callers/users, validation and configurable CP/M entry. Microsoft BASIC lineage; 3.7 supplies compiled COMs, installer, maintenance utilities and source. | Strong practical candidate. Its manual explicitly explains BYE launching RBBS and returning callers to CP/M. Check current BYE/CP/M 3 interfaces and runtime dependencies; keep compiler/interpreter and maintenance utilities private. |
| MBBS, Kim Levitt | 1983 copyright; operator guide and 4.5 release dated April 1986. A November 1986 newsletter lists an MBBS installation on CP/M 3 with BYE504. | Compact random-access message/mail storage; editing, bulletins, access flags and CP/M entry. Version 4.5 separates LOGIN and message programs. | Historically strong, but 4.5 explicitly requires MBYE 4.x and forbids BYE5xx. Do not treat the newsletter's unspecified MBBS version as proof that 4.5 works with BYE510. Main programs were distributed as object code, making adaptation less attractive than a source-based package. |
| PBBS, Russ Pencin family, later maintained by Ian Cottrell | Contemporary PCHAT source dated July 16, 1986 requires PBBS 3.0 or later and BYE5/NUBYE. Later v5 source records v1 March 1, v2 April 6 and v3 June 15, 1986. | Modular assembly-language public-board family, with signon/mail, chat and related services. | First investigation choice for preserving BYE. Obtain the complete period v3 package, including headers and support objects/source, and inspect it before claiming CP/M 3 compatibility. Do not substitute 1987–1990 versions without explicitly changing the historical target. |
| METAL, Tim Gary | David McCord's November 8, 1984 account identifies it as the message system on his actual ZCPR3/BYE board. | Message service demonstrated alongside a full Z-System installation. McCord reports no unusual TPA demand. | Excellent historical precedent for our model. A complete preserved installation/source package and its terms still need locating; present evidence does not establish modern reproducibility or feature completeness. |
| ROS, Steven Fox | v3.4 release notes dated October 19, 1985; preserved source and operations manual, archive cataloged in 1986. | Turbo Pascal/Toolbox system with messages, private mail, user validation, file areas, XMODEM and its own modem/session handling. | Capable, and the manual explicitly reports CP/M Plus operation. However v3 incorporated the roles of BYE, XMODEM and directory tools. It is an integrated host, so installing it unchanged would overlap our chosen architecture. A message-only adaptation requires investigation. |
| Citadel 2.x, CrT and David Mitchell | Internal history and installation docs dated December 1982; therefore predates the requested window. | BDS C room-based discussion system, topic rooms and personal mail, with configurable modem routines. | Attractive for a conversation-centered board, but not the simplest message application under BYE. Installation docs require CP/M 2.x, at least 300K disk, an auto-answer modem and a TPA extending to CF00h. Verify actual available memory and communications/exit integration. |
| CBBS, Ward Christensen/Randy Suess | Original system dates to 1978; original authors' retrospective describes CP/M and 8080 assembly implementation. Period CP/M publications continue to discuss CBBS during the window. | Foundational bulletin-board model with hardware-specific roots. | Historically relevant, particularly for an early-board reconstruction, but weaker than the above candidates for adding a maintained/reproducible message service to our already-working BYE machine. This survey has not recovered a complete suitable period distribution. |

Other names worth tracking: **TPBBS** (ROS's manual identifies a 1984 Turbo
Pascal conversion of RBBS by James Whorton and Eddie Curlin), **XBBS** (named
in a 1985 RCP/M list; a v2.3 archive is cataloged in 1986), **EMX**, and
**MSGSYS20** (both explicitly mentioned as alternatives in Recla's 1984 manual,
the latter as CBASIC-based). These are not yet investigated as deeply as the
main candidates. The preserved EMX 3.13 archive is dated 1988, so its features
must not be projected backward without earlier documentation. CP/M QBBS is
also distinct from Adam Hudson's DOS QuickBBS; do not mix the names or dates.

## Recommendation

The operator selected **RBBS 3.7** for the first trial. See the
[installation and measured compatibility results](rbbs-trial.md). The original
shortlist below remains useful for comparing alternatives.

Investigate **PBBS 3.0** and **RBBS 3.7** first. PBBS has explicit contemporary
BYE5 ecosystem evidence and an assembly-language lineage. RBBS 3.7 has the
clearest already-recovered period installation, source and operating material.
This is an engineering shortlist, not a measured ranking of all period boards.

Keep METAL as a worthwhile recovery lead. Treat MBBS 4.5 as a monitor/API
adaptation project, not a drop-in program. ROS and Citadel warrant choosing
their user experience deliberately rather than selecting them simply because
their archives survive.

## Consequences for the disk and security design

- I2:BBS is a proposed persistent data area, not a guarantee that every
  package will fit one DU. MBBS's manual explicitly separates message/user
  files from WRK/ARC files by drive. Package-specific requirements must be
  settled before finalizing storage. All I: user areas share its 4-MB capacity.
- BBS executables and executable overlays/support modules must be trusted and
  protected from caller replacement. Persistent messages/users need controlled
  application access; ordinary TYPE/DIR/transfers must not expose private data.
- Our current caller list contains no BBS entrypoint. A chosen package's
  loader, chaining and overlay paths require explicit review and authorization;
  merely copying its COM file to I2: will not make it runnable.
- Several packages inspect BYE low-memory conventions or invoke extended BDOS
  calls. Match the actual APIs of the selected release to our BYE510 insert.
  Generic descriptions of compatibility are insufficient.
- Measure TPA after BYE has loaded. The Z3PLUS startup TPA banner precedes that
  additional resident load, so it is not the final application-memory budget.
  Build/link memory requirements are separate from runtime requirements.
- Recheck carrier loss during writes, user-record ownership, privilege flags,
  return to CP/M, caller/system context cleanup and local operator controls.
  Compiler/interpreter access need not be public to run a compiled BASIC BBS.
- Recover and review the exact package's redistribution terms before bundling.
  MBBS's manual describes an object-code release with author requests about
  headings/commercial or restricted-access use; ROS permits noncommercial
  distribution with documentation. Archival availability alone settles neither
  terms nor package completeness.

## Primary sources and preserved distributions

1. [RBBS 3.7 manual, November 23, 1984](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/rbbs/rbbs37-1/rbbs37.doc.txt),
   [RBBS archive](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/rbbs/).
2. [MBBS 4.5 release notes, April 22, 1986](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/mbbs/mbbs45a/mbbs45.doc.txt),
   [operator manual, April 21, 1986](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/mbbs/mbbs45b/sysopman.doc.txt).
3. [BAMDUA newsletter, November 10, 1986](https://bitsavers.trailing-edge.com/pdf/morrow/bamdua/BAMDUA_Vol4No10_Nov1986.pdf),
   inside-cover system listing. It names MLOGIN 1.2 and BYE504, not MBBS 4.5.
4. [PCHAT source, July 16, 1986](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/pbbs/pchat11.mac.txt),
   [PBBS archive](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/pbbs/),
   [later PBBS 5 source with release history](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/pbbs/pbbs-50/pbbs50.mac.txt).
5. [McCord, Z3ANDBYE, November 8, 1984](https://www.dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/rcpm/z3andbye.doc.txt).
6. [ROS operations manual](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/ros/ros34/rosops.ws.txt),
   [3.4 release notes](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/ros/ros34/ros34.not.txt),
   [ROS source/distribution archive](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/ros/).
7. [Citadel's December 1982 history](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/bbs/citadel/history.doc.txt),
   [installation guide](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/bbs/citadel/install.doc.txt).
8. [Ward and Randy, The Birth of the BBS](https://www.chinet.com/html/cbbs.php).
9. [1985 RCP/M list](https://groups.google.com/g/net.micro.cpm/c/eKb_H8oBGH8),
   [additional BBS archive/catalog](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/bbs/).

Still unverified: complete period PBBS v3 sources, a complete METAL package,
exact current-runtime compatibility of any BBS, final executable/overlay sizes,
and whether one reserved data DU is sufficient for the selected package.
