# v1.2.2-rc2 — rebuilt service-kit verification

**PASS — 27 November 2026.** Both local prerelease kits contain the shutdown
fix and corresponding source/tests. No release was uploaded or tagged.

| Check | ARM64 | x64 |
| --- | --- | --- |
| Archive file hashes and layout | 762 verified | 762 verified |
| ELF architecture and executable modes | Pass | Pass |
| Installer preflight | Pass | Pass |
| Linux service unit tests | 11 passed | 11 passed |
| Supervisor integration checks | 10 passed | 10 passed |
| Post-test package manifest/preflight | Pass | Pass |

Both guests ran Debian 12.15 with real systemd 252 as PID 1 and Python 3.11.2.
ARM64 used Apple virtualization. x64 used QEMU TCG CPU emulation on the ARM64
Mac, with two CPUs and 2 GiB RAM; it is not native x64 hardware qualification.

The integration checker runs disposable supervisor instances and a readiness
notification socket. It covers IP232 boot, duplicate-instance refusal, console
reattachment, caller HELP, private-data/shutdown denials, caller draining,
graceful snapshot, restore with matching credentials/data, and modem failure
followed by successful restart. This is not a repeat of all real-unit systemd
reboot, timer and fault tests from rc1.

## Package identity

The two archives were rebuilt from the pinned, qualified rc1 archives. All
19 runtime/media/driver files in each kit remain byte-identical to that input;
no native binary recompilation or CP/M media change was needed. The helper,
matching source copies, tests and documentation are updated. Package manifests
and candidate receipts were regenerated. All source overlays were compared
with the current checkout, and the shared common manifest matches across both
architectures.

| Archive architecture | SHA-256 |
| --- | --- |
| arm64 | `c18d846d651af6ba4bae18ed1e6b3d80e0430ae39b049962c5f73ef97829a9fb` |
| x64 | `f62aff5be5768269859438f25f3a60030d1b1b0e6db3e6bc523d4db261805890` |

Each archive is named `rcpm-v1.2.2-rc2-linux-ARCH-service.tar.gz` under
`build/prerelease-v1.2.2-rc2/`. Exact sizes, base hashes and source hashes are
recorded in `RELEASE-PROVENANCE.json` and `CANDIDATE-VERIFICATION.json`. Provenance
identifies the checkout base revision plus exact working-tree source hashes;
it does not claim a new tag or a clean, committed release snapshot.

## Findings and evidence

The first x64 candidate unit run found a test race: `/proc/PID/stat` disappeared
while being read after successful child termination. The packaged test now
accepts FileNotFoundError/ProcessLookupError as the expected exit. Its final
11-test run passed on each architecture. This corrected a test, not production
process cleanup. The initial failure log is retained.

The production change remains the shutdown-signal fix already exercised by
the installed ARM64 eight-group caller regression. Its helper hash matches both
rebuilt kits. See [the caller report](debian-caller-regression.md).

The candidate folder contains the release notes and installation guide,
checksums, JSON provenance/verification, the caller report/summary and its
sanitized evidence archive. `VERIFICATION-EVIDENCE.tar.gz` contains the new
preflight, unit, integration and postcheck logs, environment records, archive
checks, and the initial x64 test failure. The older partial candidate archives
and logs are retained separately; their digests are not the final kit digests.

## Limits and final state

The new x64 VM is shut down after evidence export; the earlier ARM64 test VM
is retained with its installed RCP/M service stopped. No VPS, CPMNet work,
commit, push, tag creation or publication is included in this preparation.

Outstanding stable-release gates include native x64 hardware qualification,
72-hour mixed-use operation, operational failure/alert checks, off-host recovery
and public-listener qualification. Full rc2 systemd-unit lifecycle qualification
and x64 repetition of the eight-group caller regression are not claimed.
