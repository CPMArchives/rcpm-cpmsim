# RCP/M candidate distribution review

Reviewed 21 November 2026. Public redistribution of the aggregate is still
unresolved. This records component evidence and engineering choices; it does
not classify every archive member as cleared or prohibited. The tested
candidate and its notices are unchanged. No rights holder was contacted.

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
| Z3PLUS | Original 1988 notice restricts distribution. [Gaby's download page](https://www.gaby.de/edownf.htm) attributes later free-download authorization to Jay Sage. [RomWBW's catalog](https://wwarthen.github.io/RomWBW/Catalog/#z3plus) calls it public domain. | The distributor page establishes free downloads, not an explicit grant to rehost modified bundles. Obtain the originating broader grant or confirmation covering our configured library, aliases and distribution. The old notice alone is not the complete historical picture. |
| BYE510 | Original source and BYE5.DOC permit unmodified, no-fee distribution. The installation chapter instructs operators to edit inserts/options and add an application subroutine. | Configuration is expected; describing all operator edits as forbidden would be wrong. Our AUTH/BDOS, execution and lifecycle changes go beyond ordinary equates. A grant covering distribution of those derivatives has not been established. |
| ZDE 1.6 | ZDE16.NEW restricts incomplete/modified circulation and commercial distribution, while directing users to configure ZDE with ZDENSTAL 1.6. Our changes use that installer. | Ordinary configuration is intended use. The question is distribution of our preconfigured copy, not permission to configure it locally. Original ZDE16.LBR and installer are retained; no later clarification was found. |
| Microsoft M80/L80 | Both occur in offline/BUILD.dsk, the shipped stock toolchain snapshot and the build inputs. L80 embeds Microsoft's copyright; M80 identifies itself as MACRO-80 3.44. | No applicable Microsoft redistribution grant was found. CP/M permissions and inclusion in z80pack do not answer this. Removing only offline/BUILD would leave the stock B: snapshot under source/upstream. |
| MicroPro WM | offline/BUILD.dsk/0:WM.COM embeds a 1978 MicroPro copyright and occurs in the shipped stock toolchain snapshot. | No applicable MicroPro grant was established. Treat it separately from DRI components. |
| HELPC/ZLT and other utilities | Installed hashes are pinned. ZHELP embeds Greenberg's non-profit reproduction text; ZLT embeds non-profit terms for Warren and Greenberg/Falconer code. | These identify constituent routines, not necessarily the whole program's terms. Complete the exact-version inventory for SDZ, HELPC, remaining private utilities and RBBS. Missing explicit terms in a header are not proof of prohibition or public-domain status. |
| SIG/M and CPMUG | All 403 LBR files are preserved and checksum-verified. Notice discovery inspected top-level members of all 310 SIG/M and 93 CPMUG libraries. SIG/M contribution forms describe its noncommercial public-use policy. | This is meaningful provenance, but blank forms are not signed grants for every file. Member-specific terms remain authoritative. Compressed and nested material needs review; this is not completed collection clearance. |
| Original project code | No root project LICENSE/COPYING file is recorded. | Declare the intended license for original contributions if publishing as open source; third-party terms remain separate. This review does not select a license for the maintainer. |

Notice discovery saw 6,703 SIG/M and 2,552 CPMUG top-level members with no parse
errors. It left 617 SIG/M and 16 CPMUG compressed members unread and did not
recurse into nested libraries. These figures describe coverage, not the number
of licensed programs. Working inventories are in build/distribution-review/;
a compact hash-based record is tracked in
[distribution-review-2026-11-21.json](performance/distribution-review-2026-11-21.json).

## Concrete release decisions

1. Trace the originating Z3PLUS grant and clarify derivative BYE distribution
   and ZDE preconfigured-copy terms. Requests should identify exact versions,
   source patches, modified binary distribution, notice retention and proposed
   release terms. An author named in an old header is not necessarily the
   person who can grant permission today. Contact requires separate authorization.
2. Decide whether development-only Microsoft/MicroPro binaries belong in the
   public runtime package. They are not needed to run the built system. A
   proposed separation would omit them from both offline and source media and
   let builders provide their own toolchain disks. That changes packaging and
   recorded inputs; it has not been implemented.
3. Finish utility/member notice review and declare release terms consistent
   with the noncommercial grants being used. Do not describe the complete
   aggregate as unrestricted public domain.
4. If broader permissions cannot be established, operator-supplied-input
   assembly is an alternative to distributing affected bytes. It would change
   the download/unpack/run contract and needs a scope decision. This report
   does not approve a replacement shell/driver or removal of the agreed P:
   collections.

Native platform engineering can continue independently. The local candidate
remains available; no public release or rights-holder message was sent.
