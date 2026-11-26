# Interrupted regression: recovery checkpoint

Inspected on 27 November 2026 (Asia/Taipei). This is a recovery inventory,
not a test qualification report. No regression tests were rerun during inspection.

Subsequent authorized continuation completed all eight groups. See
[the final caller regression report](debian-caller-regression.md) for verified
results, fixes, preserved failures, evidence identity and limitations. The
inventory below remains the historical recovery checkpoint.

## Recovered evidence review

The user subsequently collected and copied `security-evidence.tar.gz` into
`build/security-vm-qualification/`. Its contents were recovered into
`build/security-vm-qualification/recovered-evidence/`; all 58 entries in the
exported SHA-256 manifest verified. The inventory below describes the earlier
inspection; this section supersedes its statements about unread guest evidence.

| Group | Evidence-backed outcome |
| --- | --- |
| auth | Completed: 13 recorded checks pass, including permission enforcement, execution approval, scoped RBBS access and restart persistence. |
| auth-cli | Completed: eight recorded checks pass. |
| flush | Attempted, incomplete: stopped at an obsolete expected MOUNT message. |
| boundary, invalid-policy, transfers, chat, idle | No result or failure evidence exported for these groups; completion is unverified. |

The initial auth failure expected `Enter your FIRST Name:` while the shipped
RBBS displayed `Enter your name:`. The adapter was corrected and a later run
recorded a pass. The initial auth-cli failure occurred during stop handling;
the journal records a successful stop acknowledgement followed by a false
startup-error exit. A later run passed after the service helper change.

The service defect is supported by both the journal and a regression test that
fails against the original published helper. All 11 native service tests pass
with the fix; the journal also shows a later successful service stop. The local
modified helper hash matches the exported installed helper identity. This is
evidence for the fix, not a claim that a corrected release has been published.

The flush test expected `Volume mounted on J:.`; actual output was
`Volume GUIDES mounted on J:`. This failure establishes a stale test expectation,
not a failed mount or a permission bypass. The suite must be updated and resumed
before claiming flush coverage. Its source contains additional copies of the
old expected message that also need review.

Environment evidence records Debian 12.15 ARM64, systemd 252, two CPUs and Apple
virtualization. Exported identity checks report matching runtime/drivers and
AUTH, CHAT, MOUNT and RBBS binaries relative to the kit, with the service helper
changed as described above. No full BYE/AUTH, transfers or CHAT qualification is
claimed from these partial results. No additional tests, commits, deployments,
or VM deletion were performed during recovery review.

## Confirmed on the host

The checkout remains at `0085ea0`. These uncommitted changes survived:

| File | Observed change |
| --- | --- |
| `check_debian_security.py` (untracked) | Disposable-systemd-VM runner for eight groups: auth, auth-cli, flush, boundary, invalid-policy, transfers, chat, idle. |
| `check_auth.py` | Allows the installed RBBS login prompt to be supplied by the adapter. |
| `check_chat46.py` | Adds an installed-service adapter and IP232 modem readiness handling. |
| `packaging/native/rcpm_service.py` | Ignores a final shutdown signal when the supervisor is already stopping, intended to avoid reporting cleanup as a startup failure. |
| `test_native_service.py` | Adds a regression case for that shutdown-signal behavior. |

The production change is present, but this inspection did not independently
verify its test outcome or establish that it is ready to publish.

`build/security-vm-qualification/` exists and was empty at inspection.
Earlier ARM64/x64 lifecycle reports are present; they do not prove that this
new caller regression completed.

## VM and evidence recovery

The following temporary host files remain:

- VM directory: `/private/tmp/rcpm-security-lima/rcpm-security/`
- SSH configuration: `/tmp/rcpm-security-lima/rcpm-security/ssh.config`
- Evidence collector: `/tmp/collect-security-evidence.py`
- Guest test results expected at `/var/lib/rcpm/security-qualification/`

The VM configuration specifies Debian ARM64, two CPUs, 2 GiB RAM and 16 GiB disk.
Lima could not determine VM status in this inspection because sandbox restrictions
blocked its boot-session query. The displayed `Broken` status is therefore not
proof of guest failure. SSH to the configured localhost endpoint was also denied
by the inspection sandbox, so guest results and current service state remain unread.

The saved collector is source code, not proof of execution. It expects all eight
phase result files to say `passed`, compares installed payload identities,
redacts the known RBBS sysop password from exported logs, and creates
`/var/tmp/security-evidence.tar.gz`. It also expects the helper to include the
shutdown fix; a successful collection would therefore describe a modified helper,
not an entirely unchanged published kit.

From a host Terminal with access to the VM, recover the evidence using:

```sh
ssh -F /tmp/rcpm-security-lima/rcpm-security/ssh.config lima-rcpm-security 'sudo python3 -' < /tmp/collect-security-evidence.py
scp -F /tmp/rcpm-security-lima/rcpm-security/ssh.config lima-rcpm-security:/var/tmp/security-evidence.tar.gz /Users/nathanael/Documents/ChatGPT/M/rcpm-cpmsim/build/security-vm-qualification/
```

Run the second command only if collection succeeds. These commands collect
existing results; they do not rerun the regression suite. If collection fails,
retain the error and preserve the VM for inspection. Do not delete or rebuild it.

## Outstanding verification

- Read each phase result and failure log, including any initial failures.
- Verify the exported hash manifest and review the sanitized evidence.
- Establish which cases used the original helper and which used the fix.
- Verify the added host regression test outcome.
- Produce the final qualification report with explicit coverage and limitations.
- No commit, publication, deployment, or VM deletion was performed by this inspection.
