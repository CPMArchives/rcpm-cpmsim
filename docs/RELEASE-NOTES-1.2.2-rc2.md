# RCP/M v1.2.2-rc2 — native Debian service prerelease

Prepared for local testing and evaluation. This is not a stable or
production-ready public-VPS release. Existing v1.2.1 and v1.2.2-rc1 assets
are unchanged.

## Changes since rc1

- Fix a shutdown race: systemd's final termination signal during successful
  cleanup no longer reports that the service failed during startup.
- Include the regression test for that race and the installed tcpser/IP232
  caller-regression runner, corrected flush assertions and CHAT adapter.
- Make the child-exit safety test accept disappearance of its `/proc` entry
  during the read; that is successful cleanup, not a service failure.
- Record all eight passing ARM64 installed-service regression groups:
  AUTH, AUTH commands, flush precautions, caller boundaries, invalid-policy
  recovery, XMODEM/YMODEM transfers, CHAT and idle expiry/reconnect.
- Update the installation guidance to distinguish completed rc1 x64 VM
  lifecycle tests from outstanding native x64 hardware qualification.

The existing guest media, drivers, native host binaries and tcpser are retained
byte for byte from rc1. The kits are rebuilt with the corrected Python service
helper, matching corresponding source/tests and updated documentation. Embedded
legacy guest/base-version labels continue to describe the retained components;
the service-candidate metadata identifies rc2.

## Candidate files

- `rcpm-v1.2.2-rc2-linux-arm64-service.tar.gz`
- `rcpm-v1.2.2-rc2-linux-x64-service.tar.gz`
- `SHA256SUMS`, `RELEASE-PROVENANCE.json`, `CANDIDATE-VERIFICATION.json`
- `NATIVE-DEBIAN-INSTALLATION.md`, `CALLER-REGRESSION-REPORT.md`,
  `CALLER-REGRESSION.json` and `CANDIDATE-VERIFICATION.md`

These are complete, fresh-install kits. Do not unpack over an existing board.
Debian 12.15 is the tested baseline; Python 3.9+ and systemd are required.
Installation leaves services stopped/disabled and callers restricted to
loopback. No separate compiler or tcpser download is required.

## Evidence and limits

The caller regression used Debian 12.15 ARM64, real systemd 252 and the corrected
installed helper. All eight groups passed; the recovered Linux helper test log
also records 11 passing tests. The corrected helper's tested hash is recorded
in the bundled regression summary. Flush and idle cases use documented
test-only media fixtures. Approved native programs remain trusted code.

The candidate verification report separately records checks on these exact
rebuilt archive bytes. Earlier ARM64 and emulated x64 rc1 lifecycle reports
remain historical evidence for their original artifacts; they must not be
described as full rc2 lifecycle qualification. A new native x64 hardware run,
72-hour soak, operational failure/alert checks, separate-storage recovery and
public-listener qualification remain outstanding. Transfer coverage here is
XMODEM/YMODEM, not a new ZMODEM/Kermit qualification.

This preparation does not deploy a VPS, implement CPMNet, alter an existing
release or publish a tag. Candidate provenance records the checkout revision
and exact source-file hashes used by the rebuild.
