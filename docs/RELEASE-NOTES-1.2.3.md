# RCP/M 1.2.3 — help integration

This source update merges `qualified-help-links` and the completed command
reference. It does not publish a v1.2.3 tag or replace existing release archives.

The online collection now has 120 HLP files. It covers 63 installed COM
programs and 24 resident CCP/RCP/FCP entries, with separate public, resident,
private utility and startup/backend indexes. An asterisk means SYSOP ONLY;
individual private topics repeat the access label. DU:/NAME: directory
selection syntax and arbitrary programs on optional collection volumes are
outside this inventory. NAME.COM itself has a command topic.

Qualified internal links retain the named directory, and HELPC 1.5r remembers
the DU for parent (`^`) and session-root (`.`) navigation. The reference
separates resident GET from console-input GET.COM and resident R from
whole-machine RESET.COM. Existing handbook chapters and canonical command
links remain intact. Both source manuals describe the expanded reference.

## Local build input

Historical HELPC source, libraries and proprietary tool executables remain
local and are not part of this source commit. The tested 1.5r viewer binary
is distributed separately by the [HELPC release](https://github.com/CPMArchives/HELPC/releases/tag/v1.5r),
with original notices and the recorded rights uncertainty. Original
copyright and noncommercial/distribution conditions remain applicable.

The stopped-media help installer requires the tested qualified-link viewer at
both A0:HELP.COM and I13:ZHELP.COM. If staging media still contain an older
recognized viewer, supply the tested 1.5r binary through
`RCPM_HELPC_VIEWER=/absolute/path/to/HELPC15.COM` before running the existing
assembly workflow. `caller_help.install(instance, tools, viewer=path)` also
accepts that input explicitly. The helper retains each viewer's local settings
and attributes, validates both replacements before changing staging originals,
and rejects unknown code. It never fetches historical files or copies that
input into the source tree. This helper is for fresh, stopped build media;
existing live installations use the separate guarded local updater.

Without a compatible installed viewer or the explicit local input, assembly
fails before installing qualified-link topics. This prevents apparently
successful packages with links that HELPC 1.4 cannot follow. Producing a public
binary release still requires the component distribution review and the
[1.2.3 documentation/release gate](release-packaging.md#documentation-release-gate-123-and-later),
including refreshed distributed manual editions and platform package checks.

## Verification

The tested local collection opened all 120 help files, followed 145 qualified
links and returned to their parents, and exercised nested root navigation.
Loopback caller tests verified access labels, navigation, private utility and
resident GET denial, and a working resident IF NULL example. The operator
confirmed topic text and parent/root navigation, rejected SYSUTLS:DATE, GET,
GO, JUMP, POKE and PORT from a normal caller connection, and confirmed ECHO
and HELP still work. This is evidence for those checks, not an exhaustive
security audit or a new cross-platform release qualification.

The [coverage manifest](command-help-coverage.json) maps every captured
invocation to its topic/access category. [Test evidence](command-help-tests.json)
records the viewer and caller checks. Run `python3 -m unittest test_caller_help`
for the source validation and coverage checks. Local integration also verifies
that the repository installer rejects old viewers before changing either disk,
upgrades recognized viewers only with the explicit local input, and installs
byte-verified help on disposable media.
