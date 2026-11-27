# Release candidate packaging

The release contract is **download, unpack, run**. The distribution starts one
foreground cpmsim process, leaves that terminal as the sysop console, and prints
the listening address/port after the raw TCP listener opens. No tmux, Python,
Homebrew, caller client or compiler is required at run time. Python and a compiler
are build-time tools only. The operator's existing tmux wrapper remains separate.

Host service installation, scheduled backups and monitoring belong to the
separate [optional administration add-on](hosting-addon.md). Build that add-on
with `build_admin_addon.py` against an exact standard v1.2.2 archive; it does
not rebuild or redistribute the base runtime or board media. The standard
v1.2.2 packages use `prepare_release_1_2_2.py` and retain the foreground workflow.

`build_release.py` produces a common payload and a macOS ARM64 package. The
native launcher, emulator and bundled POSIX cpmtools depend only on macOS system
libraries, with deployment target 11.0. Other host packages are not yet built or
qualified. Download quarantine/signing/notarization needs host release validation.

## Documentation release gate (1.2.3 and later)

Treat the manuals and online HELP as part of the released system, not as a
separate writing project. Before approving any standard RCP/M release:

1. Review the changes since the previous stable release against both
   [the Sysop's Guide](SYSOP-GUIDE.md) and [the User's Guide](USER-GUIDE.md).
   Update affected chapters, commands, examples, defaults, limitations and
   version references. Record an explicit no-change finding for either
   manual if the release does not affect it.
2. Review the HELP topics in `guest/help/` against the manuals and actual
   shipped behavior. Update affected topics and links; run the repository's
   HELP format and integration checks. Do not claim planned features as
   available. Test our content, not the unchanged HELPC implementation.
3. Keep ordinary sysop operation separate from optional host administration.
   Retain period terminology and the conversational handbook style.
4. Generate or refresh the distributed manual editions from the reviewed
   sources. Include both guides in every standard native and Docker package
   (through the common payload as applicable), alongside installation and
   disk-image references. Verify the packaged copies and installed HELP
   against the reviewed source revision. Never include private SYSOP.DOC.
5. Check the repository README, documentation index and website links.
   Update release notes with documentation changes or an explicit no-change
   finding, and record the source commit and packaging/HELP check results.

The release maintainer must confirm this checklist before publication.
Do not publish a new release with missing or stale manuals, or omit the
documentation review because the changes appear to be host-only. This is
a mandatory release procedure; automated enforcement should be added to
the 1.2.3 packaging and qualification workflow when those packages are built.
Existing published release assets are not retroactively replaced.

## Common payload

- Fresh A: and I: are constructed from pinned inputs, never operator disks.
- P: contains 310 SIGM and 93 CPMUG LBR files. All 403 are extracted and checked
  against the preserved SHA256 list before the archive image is packaged.
- No J: image is shipped under disks/. The native launcher creates an empty J:
  on first start. `MOUNT GAMES` / `MOUNT GUIDES` select public read-only volumes.
- GAMES user 0 holds its game-data preparation launchers; A0 has no game-specific wrappers.
- GAMES contains compiled games, required runtime data and playing instructions.
  Source-only and unqualified sets, old catalogs and MCHORIG.COM are excluded;
  the original archives remain on P:. The optional expanded GAMES download
  adds 73 qualified games and does not enlarge the base packaging inputs.
- GUIDES contains documentation only. A public development toolbox was rejected;
  compilers/interpreters/loaders remain private sysop tools or offline media.
- Both BYEDRIV variants ship under drivers/. Direct raw TCP is default on
  127.0.0.1:4000. IP232 selects the modem driver and cpmsim backend together.
- RBBS counters/users/messages start fresh. The common password record is an
  uninitialized seed. Before first guest boot, the native launcher replaces it
  with fresh local secrets and creates private SYSOP.DOC; it never ships an
  operator password or account. The state marker prevents resets on restart.
- INSTALLATION.DOC covers setup; SYSOP-GUIDE.DOC covers daily administration,
  including the private host upload inbox and review/publication workflow.
  Generated SYSOP.DOC remains a private credential file, not the general guide.
- Documentation includes raw image geometries and format/edit examples. cpmtools
  format selection is explicit; the bundled diskdefs is used via DISKDEFS.
- `offline/BUILD.dsk` is reconstructed from a fresh image, retaining DRI files
  while omitting Microsoft M80/L80 and MicroPro WM, including WM.HLP. The unfiltered original
  `cpm3-2.dsk` is also omitted from the source bundle. Builders supply that
  pinned disk separately; it is not a runtime dependency. `DEVELOPMENT-MEDIA.json`
  records excluded hashes and verifies every retained development file.
  The P: archive collections are preserved unchanged.

The native launcher holds `.console.lock` across driver installation and exec into
cpmsim. It stages A: changes before replacing it. It never edits live disks. Mode
switches and backups require stopping the guest first. Optional tcpser is installed
by operators who choose modem mode; it is not a default dependency.

## Build

Use the same source inputs as the upper-area system build. Example:

```sh
MACOSX_DEPLOYMENT_TARGET=11.0 python3 build_raw_cpmtools.py /path/to/cpmtools-2.23 \
  --output build/release-tools
MACOSX_DEPLOYMENT_TARGET=11.0 python3 build_modem_runtime.py /path/to/z80pack \
  build/release-runtime/cpmsim
python3 build_release.py --source /path/to/z80pack --romwbw /path/to/RomWBW \
  --bye-reference /path/to/pristine/bye510 --cpmtools-source /path/to/cpmtools-2.23 \
  --archive /path/to/drivep-sigm-cpmug.dsk --sigm /path/to/SIGM/LBR \
  --builds build/release-bye \
  --output build/release-final
```

The archive input must have its matching `.sha256` file. Source archives are
immutable build inputs, not a currently mounted operator archive. The builder
refuses to replace an existing output. It expects the reviewed BYE, PPIP, SDZ and
ZDE build outputs documented elsewhere in the project. No network fetch occurs
while running or packaging the system when those inputs are available.

For the complete verified build order, pinned inputs and an isolated replay,
use [the source baseline](source-baseline.md) and `rebuild_release.py`. The BYE
output directory is now required explicitly when invoking `build_release.py`
directly; the historical default cache must not silently select an older driver.

Output contains the common ZIP, platform ZIP, SHA256SUMS, unpacked common payload
and unpacked platform package. MANIFEST.json in the platform package separates
common file hashes from native-host hashes. The common payload is the basis for
future platform builds; it is not itself a runnable package.

## Qualification

The [Linux x64 host path](linux-host-build.md) now has a native packager and a
transferable build kit. It consumes this exact common ZIP and builds only native
host files. Actual Linux x64 compilation and live qualification remain pending;
the Mac-side packaging checks are not Linux runtime evidence.

```sh
python3 check_release.py build/release-final/rcpm-macos-arm64-candidate.zip \
  --output build/release-final-check --tcpser /path/to/tcpser
```

Checks unpack using macOS ditto, preserve executable modes, run from a directory
with spaces and a working directory outside the checkout, and restrict PATH to
system directories. They verify file hashes, first-start initialization, caller
login, SIGM/CPMUG aliases, both public volumes, RBBS entry, duplicate-instance
refusal, orderly shutdown, real tcpser/IP232 operation, switching back to direct
TCP and credential preservation. The device-level socket suite is also retained.
No live operator instance is stopped or modified.

## Distribution and qualification status

The maintainer's release decisions are in [the component review](distribution-review.md).
Retain Z3PLUS on its later free-release/public-domain evidence, retain configured
ZDE with the original complete archive, and retain the modified BYE510 with its
original notices, documented changes and the maintainer's accepted uncertainty.
The SIG/M and CPMUG collection authorization is accepted. Noncommercial and
other component-specific conditions remain; no uniform public-domain or
open-source license is asserted for the aggregate.

The required Windows suite passed on Windows 11 ARM64 (build 26300), running
our x64 executables through Windows emulation, including restart and credential
preservation. [Windows evidence](performance/windows-runtime-2026-11-21.json)
distinguishes the transcribed screenshot from a retrieved original guest report.
Optional Windows IP232 and native x64 hardware were not tested. Linux remains
outside the qualified 1.0 host set. macOS ARM64 retains its direct/IP232 live
qualification. Final distribution checks are recorded with the frozen assets.

`finalize_release.py` refreshes documentation and source/qualification scripts
around the frozen runtime files and regenerates the common/host manifests.
It rejects changes to guest images, BYE drivers, native runtime executables or
startup launchers relative to the tested candidates. A changed ZIP hash from
updated documentation does not imply a rebuilt runtime.
