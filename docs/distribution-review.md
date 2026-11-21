# RCP/M candidate distribution review

Reviewed 21 November 2026. This is an evidence inventory, not a completed
component clearance. Preserve original notices in the candidate.

| Component | Evidence inspected | Candidate treatment and open work |
| --- | --- | --- |
| Z3PLUS | `NOTICES/Z3PLUS-original.txt` restricts copying/distribution. [RomWBW's current catalog](https://wwarthen.github.io/RomWBW/Catalog/#z3plus) describes that notice as superseded by public-domain release. | The later release claim is a concrete research lead, not merely inference from archive availability. Locate the original grant and its scope; do not conclude the 1988 notice is necessarily the final word. |
| BYE510 | `NOTICES/BYE510-original.asm`, opening notice, permits personal copying and unmodified distribution without a fee. | Our configured sources include substantive AUTH, execution, RBBS and modem changes. No later grant covering those changes has been established in this review. |
| ZDE 1.6 | `source/upstream/utility-references/zde16/zde16.new.txt`, opening notice, restricts incomplete or modified circulation and commercial distribution. | Our `build_sysop_editor.py` uses ZDENST to change the terminal profile, keys and cursor controls. Preserve the original library and installer. Establish whether distribution of installed configurations is authorized; do not silently classify the installed binary as unmodified. |
| PPIP 1.8 | `source/upstream/utility-references/ppip18/ppip18.z80.txt` and `ppip.doc.txt` retain noncommercial restrictions. | Preserve notice and sources; assess distribution conditions separately from editor/BYE restrictions. |
| HELPC, ZLT and other Z-System tools | Pinned binaries and source references are listed in `docs/caller-tool-binaries.json` and `docs/zsystem-tool-sources.json`. | Finish component-specific notice review; version/hash identity does not establish permission. |
| CP/M 3 and offline build tools | Stock z80pack media, RomWBW inputs and offline BUILD image are included. | Record the applicable grants for these exact components, including bundled tools. RomWBW's general LEGAL.md statement is not itself a grant by every upstream author. |
| SIG/M, CPMUG and GAMES members | P: contains 403 preserved libraries, checked against ARCHIVE.sha256. GAMES contains selected extracted members and their notices. | Preserve member notices and record applicable terms. Collection completeness and checksums establish identity, not a uniform collection-wide license. |
| z80pack and Z80 core | `NOTICES/z80pack-LICENSE.txt` and `NOTICES/z80core-COPYING.txt` contain permissive grants. | Retain notices, matching source and our patches. |
| cpmtools | `NOTICES/cpmtools-COPYING.txt` and matching source snapshot accompany the candidate. | Retain applicable license text and corresponding modified source/build instructions. |

The pinned RomWBW input is commit
`cb887a1a2191072dff952bfa836a8dca201b1450`. Online catalog wording was checked
on 21 November 2026; it is distinct from the original component notices.
Searches for later BYE510 and ZDE grants did not establish one. That search
result is an evidence limit, not proof that no later grant exists.

No rights holder has been contacted. Do not replace the chosen command
environment, remove tools or omit archive collections as a release workaround
without an explicit design/scope decision. Local stabilization can proceed while
these questions remain open.
