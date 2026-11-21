# RCP/M 1.0 source baseline

Recorded 21 November 2026. This is a local engineering baseline, not a public
release. The qualified macOS candidate remains
`build/release-1.0-stabilization/rcpm-macos-arm64-candidate.zip`; its exact hash
is recorded in [release-baseline.json](release-baseline.json). Consolidating
source does not replace that qualified archive or clear redistribution.

## What is pinned

The baseline records 321 required input files by relative name and SHA256,
nine built guest-tool outputs, and both qualified archive hashes. Existing
component reference manifests retain original download URLs and hashes.

| Input group | Required material | Recovery/source |
| --- | --- | --- |
| z80pack | Exact host source snapshot, native assembler sources and stock CP/M 3 toolchain disks | Qualified candidate `source/upstream/z80pack`; do not substitute a different upstream snapshot for this reviewed, service-capable input |
| cpmtools | cpmtools 2.23 source | Qualified candidate `source/upstream/cpmtools-2.23`; the builder applies the raw-device option fix in a private copy |
| bye | Seven pristine BYE510 reference files | Qualified candidate `source/upstream/bye510`; original URLs/hashes in `bye510-reference-sources.json` |
| romwbw | Selected Z3PLUS files, tools and notices | RomWBW commit `cb887a1a2191072dff952bfa836a8dca201b1450`; every selected file is individually pinned |
| cache | Original PPIP, SD137, LDIR, ZDE and RBBS reference material | `build/ztools` and `build/rbbs37/original`; component manifests specify original paths/URLs/hashes. Utility references are also in candidate `source/upstream/utility-references`. RBBS binary references must be obtained separately if absent; the packaged RBBS source folder alone is insufficient. |
| sigm | Seven original SIG/M libraries used to construct GAMES | SIGMV002, 010, 011, 024, 134, 228 and 256; the matching original libraries are also preserved on P0: |
| archive | Original populated P: and matching library manifest | `drivep-sigm-cpmug.dsk` plus `drivep-sigm-cpmug.sha256`; candidate `disks/drivep.dsk` and `ARCHIVE.sha256` supply those same bytes under different names |

No operator disks, users, uploads, accounts or installed passwords are build
inputs. Generated caches and disk images remain outside Git. Original notices
remain attached to reference material; this manifest asserts identity, not a
uniform license or permission to redistribute.

## Rebuild from a clean checkout

On macOS ARM64, install Python 3.9 or newer and the C compiler/make tools.
Provide the pinned material above. Create a local JSON file mapping input group
names to their directories, for example:

```json
{
  "z80pack": "/path/to/z80pack-snapshot",
  "cpmtools": "/path/to/cpmtools-2.23",
  "bye": "/path/to/bye510",
  "romwbw": "/path/to/RomWBW",
  "cache": "/path/to/reference-cache",
  "sigm": "/path/to/SIGM/LBR",
  "archive": "/path/to/archive-inputs"
}
```

The cache directory must contain `ztools/ppip18`, `ztools/sd137`,
`ztools/ldirb15`, `ztools/zde16`, and `rbbs37/original`, with the files named in
the baseline. `build/release-baseline-paths.json` is the existing local mapping;
it is deliberately ignored by Git because machine-specific paths are not the
baseline. To verify inputs or rebuild:

```sh
python3 rebuild_release.py --paths /path/to/input-paths.json --verify-only
python3 rebuild_release.py --paths /path/to/input-paths.json --output build/fresh-rebuild
```

The output must not already exist. The recipe copies sources and verified
inputs into that new directory, then builds native z80asm, raw cpmtools,
cpmsim, both configured BYE variants, PPIP, SDZ and ZDE. It compares guest-tool
hashes with the qualified baseline before packaging, and refuses to package a
mismatch. Packaging uses the explicit new BYE directory, never the historical
`build/bye5` cache. Original input directories and existing installations are
not modified. No downloads occur during this replay. Guest toolchain sessions
have modem/listeners disabled; final network qualification is a separate step.

Output includes `work/`, pinned `inputs/`, new `candidate/` packages and
`rebuild-result.json`. A repository checkout or a packaged source snapshot can
supply the project scripts. Future source snapshots include the host wrapper,
check command and reproduction fixtures as well as the build scripts.

## Verification evidence and limits

An isolated replay completed at `build/release-baseline-rebuild/`. All nine
guest-tool outputs matched exactly. The new A:, I:, P:, GAMES and GUIDES images,
and cpmsim executable, also matched the qualified candidate byte for byte.
The reports in [source-baseline-2026-11-21.json](performance/source-baseline-2026-11-21.json)
and [release-package-2026-11-21.json](performance/release-package-2026-11-21.json)
preserve rebuild and extracted-package qualification evidence without passwords.
Launcher regression checks and Python syntax checks also passed.

The full ZIP files are not promised byte-identical: source/documentation
snapshots, ZIP timestamps and native build paths/toolchain metadata can differ.
The replay does not qualify Windows/Linux, crash recovery during writes, or
download quarantine behavior. It does establish that the recorded source and
pinned inputs reproduce the tested guest media and emulator. The tested archive
is preserved; no new network test is required solely for source consolidation.
