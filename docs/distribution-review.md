# RCP/M candidate distribution review

Reviewed and rechecked 21 November 2026. Component release decisions are recorded below;
remaining utility notice questions are distinct from accepted maintainer decisions. This records component evidence and engineering choices; it does
not classify every archive member as cleared or prohibited. The tested
candidate and its notices are unchanged. No rights holder was contacted.

Subsequent approved packaging change: the new runtime profile excludes M80,
L80 and WM from a freshly reconstructed offline/BUILD.dsk and omits the
unfiltered stock cpm3-2.dsk from the source bundle. The original reviewed
candidate remains preserved. The tools remain external, pinned build inputs.

## Findings supported by component evidence

| Component | Evidence | Assessment for this candidate |
| --- | --- | --- |
| DRI CP/M 3 | [Published permission correspondence, updated 9 July 2022](https://www.cpm.z80.de/license.html) records Bryan Sparks's grant covering CP/M and derivatives, including distribution and modification. | A concrete later permission statement exists for the CP/M technology. Preserve its wording/provenance with DRI notices in a public package. Do not describe this custom grant as BSD solely because a secondary project does so. It is not permission for independent Microsoft/MicroPro software on the same disk. |
| z80pack / Z80 core | Candidate NOTICES/z80pack-LICENSE.txt, z80core-COPYING.txt, matching source and patches. | Permissive grants identified; retain notices and component-specific source headers. |
| cpmtools 2.23 | Candidate NOTICES/cpmtools-COPYING.txt is GPLv3; full source snapshot and raw-device patch/build script accompany the tools. | Preserve the license, copyright/modification notices, corresponding source and build recipe. This does not turn independent guest programs into a uniformly GPL aggregate. |
| LDIR-B 1.5 | build/ztools/ldirb15/ldirb15.z80.txt, opening notice, declares the source public domain and encourages documented updates. | Positive release evidence for the source lineage was found. Retain attribution and update history with the pinned binary/reference set. |
| PPIP 1.8 | build/ztools/ppip18/ppip.doc.txt, closing notice, invites experimentation but prohibits commercial use/monetary gain without permission; the source repeats the restriction. | Supports customization with noncommercial restrictions. Preserve those terms; it is not unrestricted public domain. Do not silently treat a paid distribution as covered. |
| Maze Chase | SIGMV228.LBR/MCHASE.DOC expressly permits compiled and modified versions, subject to no sale without prior consent and unchanged DOC/HLP accompaniment. | The ANSI binary patch is contemplated by the grant. Both original text files were read back from GAMES and match the originals exactly. Retain them together and honor the non-sale condition. |
| Expanded Adventure | SIGMV011.LBR/ABSTRACT.011 records Mike Goetz releasing the expanded game to SIG/M for noncommercial distribution. | Positive historical distribution evidence exists for this version. Preserve the abstract/catalog and noncommercial scope; do not generalize to unrelated Adventure versions. |

The CP/M and Z-System download pages were retrieved through indexed primary-site
text; direct page opens timed out. The evidence record distinguishes that
retrieval from local files inspected directly.

## Questions that remain open

| Component | Established facts | Specific unresolved point |
| --- | --- | --- |
| Z3PLUS | Original 1988 notice restricts distribution. [Gaby's download page](https://www.gaby.de/edownf.htm) attributes later free-download authorization to Jay Sage. [RomWBW's catalog](https://wwarthen.github.io/RomWBW/Catalog/#z3plus) calls it public domain. | Later free release is confirmed, and RomWBW explicitly describes Z3PLUS as since placed in the public domain while distributing a configured boot image. Treat this as substantial later-release evidence; the original 1988 notice is not a sufficient basis for a blanket distribution block. The originating general grant text has not been recovered; record this provenance limit without presenting it as a demonstrated prohibition. |
| BYE510 | Original source and BYE5.DOC permit unmodified, no-fee distribution. The installation chapter instructs operators to edit inserts/options and add an application subroutine. | Free distribution of the original is expressly permitted. The manual authorizes hardware inserts and application subroutines, and an original author publicly supplied a core-code fix for sysops to add to their downloadable master library. Thus configuration and supported patching are part of the intended history. Our broader AUTH/BDOS and lifecycle changes still have no separately located general derivative-distribution grant; this is the narrow uncertainty, not a prohibition on freely distributing BYE510 itself. |
| ZDE 1.6 | ZDE16.NEW restricts incomplete/modified circulation and commercial distribution, while directing users to configure ZDE with ZDENSTAL 1.6. Our changes use that installer. | Ordinary configuration is intended use. The question is distribution of our preconfigured copy, not permission to configure it locally. Original ZDE16.LBR and installer are retained; no later clarification was found. |
| Microsoft M80/L80 | Present on the original candidate's development media; L80 embeds Microsoft's copyright and M80 identifies itself as MACRO-80 3.44. | No applicable grant was found. The approved new runtime profile excludes them from offline media and excludes the unfiltered stock source disk. They remain separately supplied build inputs. |
| MicroPro WM | The original development copy embeds a 1978 MicroPro copyright. | No applicable grant was established. The approved new runtime profile excludes this copy along with the stock source disk; it remains an external build input. |
| HELPC/ZLT and other utilities | Installed hashes are pinned. ZHELP embeds Greenberg's non-profit reproduction text; ZLT embeds non-profit terms for Warren and Greenberg/Falconer code. | These identify constituent routines, not necessarily the whole program's terms. Complete the exact-version inventory for SDZ, HELPC, remaining private utilities and RBBS. Missing explicit terms in a header are not proof of prohibition or public-domain status. |
| SIG/M and CPMUG | All 403 LBR files are preserved and checksum-verified. Notice discovery inspected top-level members of all 310 SIG/M and 93 CPMUG libraries. SIG/M contribution forms describe its noncommercial public-use policy. | Maintainer confirmed that these are user-group collections authorized for redistribution from their original release. That established collection authorization is the accepted release basis; do not require fresh grants for every member as a release gate. Preserve existing member-specific notices and conditions. Inventory coverage remains a description of inspection, not a claim of exhaustive reading. |
| Original project code | No root project LICENSE/COPYING file is recorded. | Declare the intended license for original contributions if publishing as open source; third-party terms remain separate. This review does not select a license for the maintainer. |

Notice discovery saw 6,703 SIG/M and 2,552 CPMUG top-level members with no parse
errors. It left 617 SIG/M and 16 CPMUG compressed members unread and did not
recurse into nested libraries. These figures describe coverage, not the number
of licensed programs. Working inventories are in build/distribution-review/;
a compact hash-based record is tracked in
[distribution-review-2026-11-21.json](performance/distribution-review-2026-11-21.json).

## Concrete release decisions

1. Retain the documented later Z3PLUS free-release/public-domain provenance.
   Keep BYE original/configured distribution distinct from the narrower new-core-
   derivative question, and clarify ZDE preconfigured-copy terms. Any optional
   permission request should identify exact versions,
   source patches, modified binary distribution, notice retention and proposed
   release terms. An author named in an old header is not necessarily the
   person who can grant permission today. Contact requires separate authorization.
2. The maintainer approved separating development-only Microsoft/MicroPro
   binaries from the public runtime package. The builder now reconstructs the
   offline image without them, omits the unfiltered stock source disk, and
   records retained/excluded hashes in DEVELOPMENT-MEDIA.json. Exact build
   input pins are retained. P: and its preserved archives are unchanged; this
   does not claim removal of every historical reference or descendant in P:.
3. Preserve user-group archive notices under the accepted collection authorization.
   Finish the specific utility notice questions and declare release terms consistent
   with the noncommercial grants being used. Do not describe the complete
   aggregate as unrestricted public domain.
4. If broader permissions cannot be established, operator-supplied-input
   assembly is an alternative to distributing affected bytes. It would change
   the download/unpack/run contract and needs a scope decision. This report
   does not approve a replacement shell/driver or removal of the agreed P:
   collections.

Native platform engineering can continue independently. The local candidate
remains available; no public release or rights-holder message was sent.


## Recheck: later distribution history

The maintainer requested a second check specifically because Z3PLUS and BYE510
have circulated freely for decades. The recheck found these concrete sources:

- [Gaby's authorized Z-System download page](https://www.gaby.de/edownf.htm)
  attributes free release of NZ-COM and Z3PLUS to Jay Sage. Indexed text was
  retrieved; direct opening timed out.
- [RomWBW's current distribution catalog](https://wwarthen.github.io/RomWBW/Catalog/#z3plus)
  explicitly states that Z3PLUS was subsequently placed in the public domain,
  and describes its configured CP/M 3 boot distribution. The page was opened.
- [Herb Johnson's account](https://www.retrotechnology.net/dri/howto_cpm.html)
  describes Sage's release for general use and records his August 2008 account
  of downloads through the authorized site. The page was opened.
- [Irv Hoff's BYE510 fix, 4 August 1986](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/bye5/bye510.fix)
  asks sysops to include the fix in their downloadable master BYE510 library.
  It changes core input/status routines, not merely machine equates. Opened.
- [The historical BYE archive index](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/bye5/)
  preserves the original library alongside later fixes, hardware adaptations
  and BYE520. This corroborates the distribution history; archive presence by
  itself is not a new license grant.
- [BYE5's original manual](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/bye5/bye520/bye5.doc.txt)
  was opened and compared with the local reference: no-fee unmodified
  redistribution is granted, and installation includes custom hardware code,
  clock code and an application subroutine. No blanket later grant covering
  arbitrary new core changes was found in this recheck.

Revised assessment: it was too broad to describe Z3PLUS and BYE510 as software
that cannot be freely redistributed. There is direct later-release evidence
for Z3PLUS and express original-distribution permission for BYE510. The BYE
question left open is the breadth of permission for our new core modifications.
No program or archive has been removed, no runtime bytes changed, and no rights
holder contacted as part of this review.

## Maintainer decisions following the recheck — 21 November 2026

These decisions supersede earlier requests above to resolve Z3PLUS, BYE510 and
ZDE as release gates. They do not replace original third-party notices.

- Z3PLUS: retain it, based on the documented later free-release/public-domain
  evidence. Preserve the original notices and later-release provenance.
- ZDE: retain the configured 1.6 sysop editor and complete original archive and
  notices. The configured-copy wording remains an acknowledged ambiguity, not
  an established redistribution prohibition. No replacement is requested.
- BYE510: the maintainer explicitly authorizes proceeding with distribution of
  the project's modified build and accepts responsibility for that decision.
  This is a maintainer release decision, not a newly established grant from
  BYE's authors. Preserve their notices, pristine reference sources, and the
  project modifications. The remaining permission uncertainty is documented
  and accepted for this release; it does not require a wrapper rewrite.

The modified build includes configuration/hardware adaptation, the historical
keyboard fix, elapsed-time idle polling, dynamic Z3PLUS wheel integration and
relocation fixes, AUTH file/program-load enforcement and administration,
trusted RBBS state, session/WORK cleanup, private editor-key handling, exact
welcome-file selection, carrier checking and the driver filename adjustment.
`prepare_bye5.py` and `guest/bye5/` preserve the actual transformation and
project-authored additions separately from the pristine references.

Other utility notice questions, original project-code license selection, and
platform runtime qualification are not resolved by these decisions.
