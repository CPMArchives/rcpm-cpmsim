# Installed-service caller regression — 27 November 2026

All eight recorded groups passed through the installed tcpser/IP232 systemd
service in the disposable Debian 12.15 ARM64 VM. This completes this local
caller-regression gate, not production or public-VPS qualification.

## Results

| Group | Verified coverage |
| --- | --- |
| AUTH | Drive/DU read and write policy, actual F4 execution approval, overrides/inheritance, live changes, save/load, scoped RBBS access and restart persistence. |
| AUTH commands | Permission spellings, effective status, named policies, overwrite protection/backups, invalid loads and interactive cancellation. |
| Flush precautions | Failed flush preserves live policy and mounted volume; successful transitions, swaps, relog and caller MOUNT. |
| Caller boundary | Private reads, operator commands, unapproved loads, resident memory/boot commands, forged approval flags, raw BDOS operations, host-file denial, invalid FDC drives, private takeover and real RBBS cleanup. |
| Invalid startup policy | Caller access fails closed; private AUTH recovery succeeds without restarting the guest. |
| Transfers | XMODEM CRC retry/duplicate handling, YMODEM exact-length and empty-file upload, all-byte-values download, quarantine, approved-basename replacement denial, rejected paths, interrupted-upload cleanup and reconnect. |
| CHAT | Two-way text and separate panes, concurrent input, redraw/tab/editing/scrolling, cancellation, page timeout, bell toggle, WORK directory, scrolling fallback, private blanking and reconnect after carrier loss in conversation and paging. |
| Idle | One-minute limit at 4 MHz, activity reset after 30 seconds, expiry after 59.853 seconds from last activity, and successful reconnect. |

Unanswered CHAT paging took 22.43 seconds. The earlier native service test log
also records 11 passing tests, including the shutdown-signal regression.

## Fixes and corrected test assumptions

The existing uncommitted service fix prevents a final systemd termination signal
during successful stop cleanup from being misreported as a startup failure.
Evidence includes an actual failing service journal, a regression test failing
against the published helper, 11 passing tests with the fix, and successful
subsequent installed-service stops. The final installed helper hash matches the
modified checkout helper. The helper fix has not been published by this work.

The continuation corrected test code rather than CP/M program binaries:

- Flush assertions now match `Volume GUIDES mounted on J:` and the equivalent
  GAMES output.
- The private-file positive control uses LT; TYPE coverage supplies its explicit
  no-page option.
- Unblanking preserves the current DU. The test checks restored caller
  permissions in I15 before explicitly returning to A0.
- CHAT's installed-service adapter no longer sends direct-TCP login kicks
  during Hayes carrier negotiation.
- The shutdown negative test leaves the public test copy of BYEBYE unapproved.
  The draft incorrectly approved it before expecting native-code isolation.
  That deliberately altered fixture halted and systemd restarted it. This is
  retained evidence of the documented native-code trust boundary, not a bypass
  of the shipped admission policy. The corrected unapproved-load check passes.

The original auth prompt adaptation and all initial failures remain in the
evidence. The latest per-phase result files pass; retained failure files are
historical and must not be interpreted as failures of those later runs.

## Test identity and fixture scope

The installed service ran as `rcpm` with real systemd 252, private runtime
control, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes` and
`NoNewPrivileges=yes`. The VM used Apple virtualization, two CPUs and 2 GiB RAM.
The caller and internal modem endpoints were loopback-only.

Payload checks match the published kit's runtime/drivers and baseline AUTH,
CHAT, MOUNT and RBBS binaries. The installed service helper contains the recorded
shutdown fix; the unit, timer, configuration and control wrapper match the kit.
The eight groups use stopped disposable media copies and explicitly added test
fixtures. The flush group rebuilds AUTH/MOUNT and fault-injected variants only
on its own copy. The idle group adds a test-only approved timeout setter.
These modified case images are not release media.

An abandoned, privately blanked flush fixture from the interrupted run did not
complete a normal stop during preparation. Only that disposable service was
force-terminated before its case directory was preserved and a fresh baseline
copy was used. This event is not claimed as a consistent shutdown or backup.
The final idle case stopped normally: `ActiveState=inactive`, `SubState=dead`,
`Result=success`, `MainPID=0`. The VM remains available, with the test service
stopped; its disk contents are test fixtures.

## Evidence

- Archive: `build/security-vm-qualification/security-evidence-final.tar.gz`
- SHA-256: `d30eeaf2dbb6cf351f8b0efe6751c4966419eed9bbd6b1e3a418dae5440e9e52`
- Extracted evidence: `build/security-vm-qualification/final-evidence/`
- All 265 file hashes in its manifest verified after copying to the host.
- Export includes sanitized journals, initial and final logs, phase results,
  environment/payload identities, and test sources. The adapted source files
  were compared with the checkout and match.
- Tracked summary: `docs/performance/debian-caller-regression-2026-11-27.json`.

The original partial archive and recovered evidence are retained separately.

## Limits

Approved native programs remain trusted code; this is not isolation of arbitrary
Z80 programs. The blanking checks establish private-output and privilege
protection, not that every buffered remote byte is discarded on unblank:
a pending input suffix appeared at the caller-restricted prompt in an earlier
run. No private sentinel was exposed, and caller permissions remained enforced.

Transfer coverage here is the shipped XMODEM/YMODEM service path; it does not
claim separate ZMODEM/Kermit client qualification. This ARM64 run does not replace
native x64 hardware testing, a 72-hour soak, operational alert/failure testing,
separate-storage recovery or public-listener qualification. No VPS deployment,
CPMNet work, commit, push or release publication occurred.
