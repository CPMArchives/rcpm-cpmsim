# RCP/M 1.2.3 — HELPC 1.5r and complete command help

This release includes HELPC 1.5r, qualified internal links and the completed
command reference. It retains the native runtimes, bundled virtual modem,
BYE drivers, RBBS 4.1 board and archive volumes from the verified 1.2.2 base.
Use a fresh directory; do not extract a new release over an existing board.

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
successful packages with links that HELPC 1.4 cannot follow. Package qualification enforces the component distribution review and the
[1.2.3 documentation/release gate](release-packaging.md#documentation-release-gate-123-and-later),
including refreshed distributed manual editions and platform package checks.
Both complete manuals are included as readable .DOC text and maintained
Markdown sources in every native package and Docker image.

## Release checks

The release workflow verifies pinned base archives and the published 1.5r
binary, checks that only the two viewers and I14 help files change on guest
media, and retains all native runtime/driver bytes. It reads all 120 packaged
help menus as a caller on macOS ARM64, Linux ARM64/x64 and Windows x64, and
checks the Windows bundle under Windows 11 ARM64 emulation. Each platform
checks direct TCP and bundled-modem reconnect/shutdown. Linux Docker images
are rebuilt with both manuals and tested in both modes with persistent data.
VALIDATION.json records the exact source commit, assets and check results.

## Earlier development verification

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
